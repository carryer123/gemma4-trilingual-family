#!/usr/bin/env python3
"""Evaluate stock + every trained LoRA variant on the 30-probe FaE set.

Saves one JSONL per (variant) with side-by-side output, plus a master
summary JSON pointing to all of them.
"""
from __future__ import annotations
import os, json, time, pathlib
os.environ.setdefault("HF_HOME", "/scratch/hpc198a01/젬마4해커톤/hf_cache")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
# Unsloth's FastLanguageModel.from_pretrained accepts an adapter dir directly
# and reads adapter_config.json:base_model_name_or_path to load base + adapter.
# Plain PEFT can't load these adapters because they target Gemma4ClippableLinear
# (a custom layer type PEFT doesn't recognize).
import unsloth
from unsloth import FastLanguageModel

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
PROBES_FILE = PROJ / "paper/data_release/family_as_evaluator_probes_v1.jsonl"
STOCK_MODEL = str(PROJ / "models/unsloth-gemma-4-E2B-it")

OUT_DIR = PROJ / "prototype/eval"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# (variant_name, model_path_or_adapter_dir, is_adapter)
VARIANTS = [
    ("stock",            STOCK_MODEL,                                    False),
    ("lora_v1",          str(PROJ / "lora_out/lora_v1/gguf-q4_k_m"),     False),  # merged
    ("lora_v2",          str(PROJ / "lora_out/lora_v2/adapter"),          True),
    ("L_direct",         str(PROJ / "lora_out/L_direct/adapter"),         True),
    ("L_pivot_only",     str(PROJ / "lora_out/L_pivot_only/adapter"),     True),
    ("L_pivot_filtered", str(PROJ / "lora_out/L_pivot_filtered/adapter"), True),
    ("L_multilingual",   str(PROJ / "lora_out/L_multilingual/adapter"),   True),
    ("L_policy_00",      str(PROJ / "lora_out/L_policy_00/adapter"),      True),
    ("L_policy_01",      str(PROJ / "lora_out/L_policy_01/adapter"),      True),
    ("L_policy_03",      str(PROJ / "lora_out/L_policy_03/adapter"),      True),
    ("L_policy_05",      str(PROJ / "lora_out/L_policy_05/adapter"),      True),
    ("L_policy_10",      str(PROJ / "lora_out/L_policy_10/adapter"),      True),
    # Training-duration ablation (PF-2): how regression emerges with steps
    ("lora_v1_step4000", str(PROJ / "lora_out/lora_v1/checkpoint-4000"),  True),
    ("lora_v2_step4500", str(PROJ / "lora_out/lora_v2/checkpoint-4500"),  True),
    ("lora_v2_step5000", str(PROJ / "lora_out/lora_v2/checkpoint-5000"),  True),
]


def load_probes():
    return [json.loads(l) for l in PROBES_FILE.open() if l.strip()]


def load_variant(name, path, is_adapter):
    print(f"[load] {name} from {path} (adapter={is_adapter})")
    t0 = time.time()
    # FastLanguageModel.from_pretrained handles both: a base model dir, OR an
    # adapter dir (auto-loads base from adapter_config.json then attaches LoRA).
    model, tok = FastLanguageModel.from_pretrained(
        model_name=path,
        max_seq_length=2048,
        load_in_4bit=False,
        load_in_16bit=True,
        full_finetuning=False,
    )
    FastLanguageModel.for_inference(model)
    print(f"[load] {name} done in {time.time()-t0:.1f}s")
    return model, tok


def gen(model, tok, prompt, max_new=512):
    messages = [{"role": "user", "content": prompt}]
    text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
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
    print(f"[probes] {len(probes)}")
    ledger = {"variants": []}

    for name, path, is_adapter in VARIANTS:
        out_path = OUT_DIR / f"variant_{name}.jsonl"
        if out_path.exists():
            print(f"[skip] {name} already evaluated → {out_path}")
            ledger["variants"].append({"name": name, "out": str(out_path)})
            continue
        try:
            model, tok = load_variant(name, path, is_adapter)
        except Exception as e:
            print(f"[err] {name} load failed: {e}")
            continue
        rows = []
        for i, p in enumerate(probes):
            try:
                txt, dt, n = gen(model, tok, p["prompt"])
                rows.append({"id": p["id"], "category": p["category"],
                             "prompt": p["prompt"], "response": txt,
                             "elapsed_s": round(dt, 2),
                             "tps": round(n / max(dt, 1e-3), 2)})
                print(f"  [{name} {i+1}/{len(probes)}] {p['id']} {n/dt:.1f} tok/s")
            except Exception as e:
                rows.append({"id": p["id"], "category": p["category"], "prompt": p["prompt"],
                             "response": "", "error": str(e)})
        with out_path.open("w", encoding="utf-8") as fo:
            for r in rows:
                fo.write(json.dumps(r, ensure_ascii=False) + "\n")
        ledger["variants"].append({"name": name, "out": str(out_path)})
        del model, tok
        torch.cuda.empty_cache()

    (OUT_DIR / "all_variants_ledger.json").write_text(json.dumps(ledger, ensure_ascii=False, indent=2))
    print(f"[done] {len(ledger['variants'])} variants -> {OUT_DIR / 'all_variants_ledger.json'}")


if __name__ == "__main__":
    main()
