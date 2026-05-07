#!/usr/bin/env python3
"""Compare LoRA-v1 (merged safetensors) vs stock unsloth/gemma-4-E2B-it on the
20-probe baseline. Outputs side-by-side JSONL + summary.

Run:
  cd /scratch/hpc198a01/젬마4해커톤
  source venv/bin/activate
  CUDA_VISIBLE_DEVICES=0 ./venv/bin/python prototype/eval/lora_v1_vs_stock.py
"""
from __future__ import annotations
import os, json, time, pathlib
os.environ.setdefault("HF_HOME", "/scratch/hpc198a01/젬마4해커톤/hf_cache")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
import unsloth  # apply patches early
from unsloth import FastLanguageModel

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
PROBES_FILE = PROJ / "paper/data_release/family_as_evaluator_probes_v1.jsonl"
STOCK_MODEL = str(PROJ / "models/unsloth-gemma-4-E2B-it")
LORA_MERGED = str(PROJ / "lora_out/lora_v1/gguf-q4_k_m")  # merged safetensors dir

OUT_DIR = PROJ / "prototype/eval"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "lora_v1_vs_stock.jsonl"
SUMMARY = OUT_DIR / "lora_v1_vs_stock_summary.json"


def load_probes():
    with PROBES_FILE.open() as f:
        return [json.loads(l) for l in f if l.strip()]


def load_model(path):
    print(f"[load] {path}")
    t0 = time.time()
    model, tok = FastLanguageModel.from_pretrained(
        model_name=path,
        max_seq_length=2048,
        load_in_4bit=False,
        load_in_16bit=True,
        full_finetuning=False,
    )
    FastLanguageModel.for_inference(model)
    print(f"[load] done in {time.time()-t0:.1f}s")
    return model, tok


def gen(model, tok, prompt: str, max_new: int = 512) -> tuple[str, float, int]:
    messages = [{"role": "user", "content": prompt}]
    text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    # Gemma 4 has a multimodal processor wrapping; reach through to text tokenizer
    text_tok = getattr(tok, "tokenizer", tok)
    enc = text_tok(text, return_tensors="pt", add_special_tokens=False)
    input_ids = enc.input_ids.to(model.device)
    attn = enc.attention_mask.to(model.device) if enc.get("attention_mask") is not None else None
    t0 = time.time()
    with torch.inference_mode():
        out = model.generate(
            input_ids=input_ids, attention_mask=attn,
            max_new_tokens=max_new, do_sample=False,
            pad_token_id=text_tok.eos_token_id,
        )
    dt = time.time() - t0
    n_new = out.shape[1] - input_ids.shape[1]
    txt = text_tok.decode(out[0][input_ids.shape[1]:], skip_special_tokens=True).strip()
    return txt, dt, n_new


def main():
    probes = load_probes()
    print(f"[probes] {len(probes)} loaded")

    # Pass 1: stock
    stock_results = []
    model, tok = load_model(STOCK_MODEL)
    for i, p in enumerate(probes):
        txt, dt, n = gen(model, tok, p["prompt"])
        stock_results.append({"id": p["id"], "category": p["category"],
                              "prompt": p["prompt"], "rubric": p.get("rubric", ""),
                              "stock_response": txt, "stock_dt": round(dt, 2),
                              "stock_tps": round(n / max(dt, 1e-3), 2)})
        print(f"  [stock {i+1}/{len(probes)}] {p['id']} {n/dt:.1f} tok/s")
    del model, tok
    torch.cuda.empty_cache()

    # Pass 2: LoRA-v1 (merged)
    model, tok = load_model(LORA_MERGED)
    for i, p in enumerate(probes):
        txt, dt, n = gen(model, tok, p["prompt"])
        stock_results[i]["lora_response"] = txt
        stock_results[i]["lora_dt"] = round(dt, 2)
        stock_results[i]["lora_tps"] = round(n / max(dt, 1e-3), 2)
        print(f"  [lora  {i+1}/{len(probes)}] {p['id']} {n/dt:.1f} tok/s")
    del model, tok
    torch.cuda.empty_cache()

    # Save
    with OUT.open("w", encoding="utf-8") as fo:
        for r in stock_results:
            fo.write(json.dumps(r, ensure_ascii=False) + "\n")

    summary = {
        "n": len(stock_results),
        "stock_mean_tps": round(sum(r["stock_tps"] for r in stock_results) / len(stock_results), 2),
        "lora_mean_tps": round(sum(r["lora_tps"] for r in stock_results) / len(stock_results), 2),
        "stock_empty_count": sum(1 for r in stock_results if not r["stock_response"].strip()),
        "lora_empty_count": sum(1 for r in stock_results if not r["lora_response"].strip()),
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\n[summary]"); print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nside-by-side at {OUT}")


if __name__ == "__main__":
    main()
