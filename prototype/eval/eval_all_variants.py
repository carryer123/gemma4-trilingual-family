#!/usr/bin/env python3
"""Evaluate stock + every trained LoRA variant on the 30-probe FaE set.

Auto-discovers adapters under lora_out/:
  - <variant>/adapter/             — final adapter
  - <variant>/checkpoint-N/        — intermediate checkpoint (only if VARIANTS_INCLUDE_CHECKPOINTS=1)

Saves one JSONL per (variant) with side-by-side output, plus a master
ledger pointing to all of them.

Env:
  CUDA_VISIBLE_DEVICES — GPU id
  VARIANTS_INCLUDE_CHECKPOINTS=1 — also evaluate intermediate checkpoint-N dirs
  VARIANTS_FILTER=L_step_dense    — only eval variants whose name contains this substring
  ONLY_NEW=1 — skip variants whose JSONL already exists
"""
from __future__ import annotations
import os, json, time, pathlib, re
os.environ.setdefault("HF_HOME", "/PATH/REDACTED")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
import unsloth
from unsloth import FastLanguageModel

PROJ = pathlib.Path("/PATH/REDACTED")
PROBES_FILE = PROJ / "paper/data_release/family_as_evaluator_probes_v1.jsonl"
STOCK_MODEL = str(PROJ / "models/unsloth-gemma-4-E2B-it")
OUT_DIR = PROJ / "prototype/eval"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LORA_OUT = PROJ / "lora_out"
INCLUDE_CHKPT = bool(int(os.environ.get("VARIANTS_INCLUDE_CHECKPOINTS", "0")))
FILTER = os.environ.get("VARIANTS_FILTER", "")
ONLY_NEW = bool(int(os.environ.get("ONLY_NEW", "1")))


def _filter_match(name: str) -> bool:
    if not FILTER:
        return True
    parts = [p.strip() for p in FILTER.split(",") if p.strip()]
    if not parts:
        return True
    return any(p in name for p in parts)


def discover_variants():
    """Return list of (name, path, is_adapter) tuples."""
    items = [("stock", STOCK_MODEL, False)]
    for d in sorted(LORA_OUT.iterdir()):
        if not d.is_dir(): continue
        if not _filter_match(d.name): continue
        # Final adapter
        adapter = d / "adapter"
        if adapter.is_dir() and (adapter / "adapter_config.json").exists():
            items.append((d.name, str(adapter), True))
        # The Unsloth merge dir from earlier (lora_v1)
        merged = d / "gguf-q4_k_m"
        if merged.is_dir() and (merged / "model.safetensors").exists() and not adapter.is_dir():
            items.append((d.name, str(merged), False))
        # Intermediate checkpoints (opt-in; for step-axis curves)
        if INCLUDE_CHKPT:
            for ck in sorted(d.glob("checkpoint-*")):
                if not ck.is_dir(): continue
                if not (ck / "adapter_config.json").exists(): continue
                m = re.match(r"checkpoint-(\d+)", ck.name)
                step = int(m.group(1)) if m else 0
                items.append((f"{d.name}_step{step:05d}", str(ck), True))
    return items


def load_probes():
    return [json.loads(l) for l in PROBES_FILE.open() if l.strip()]


def load_variant(name, path, is_adapter):
    print(f"[load] {name} from {path}")
    t0 = time.time()
    model, tok = FastLanguageModel.from_pretrained(
        model_name=path, max_seq_length=2048,
        load_in_4bit=False, load_in_16bit=True, full_finetuning=False,
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
    variants = discover_variants()
    print(f"[discover] {len(variants)} variants found")
    for name, path, _ in variants[:8]:
        print(f"  {name}  ←  {path}")
    if len(variants) > 8:
        print(f"  ... and {len(variants)-8} more")

    probes = load_probes()
    ledger = {"variants": []}

    for name, path, is_adapter in variants:
        out_path = OUT_DIR / f"variant_{name}.jsonl"
        if ONLY_NEW and out_path.exists():
            n = sum(1 for _ in out_path.open())
            if n >= len(probes) - 1:
                print(f"[skip] {name} already evaluated ({n} rows)")
                ledger["variants"].append({"name": name, "out": str(out_path)})
                continue
        try:
            model, tok = load_variant(name, path, is_adapter)
        except Exception as e:
            print(f"[err] {name} load failed: {type(e).__name__}: {str(e)[:120]}")
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
