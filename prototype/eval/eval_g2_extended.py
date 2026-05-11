#!/usr/bin/env python3
"""Evaluate the extended 52-probe G2 transliteration set on a list of variants.

Variants are the 16 paper-critical adapters: stock, lora_v1, lora_v2,
L_v1_recreate, 5 seeds, 7 (r,α) configs. The 52 probes cover four
directions (ko->cyr, ru->han, ko->lat, ru->lat) with 13 prompts each.

Output: paper/figures/g2_extended_scores.json
        per-variant per-direction breakdown + bootstrap CI

Env:
  CUDA_VISIBLE_DEVICES — which GPU
  VARIANTS_FILTER — comma-separated exact variant names
"""
from __future__ import annotations
import os
import sys
import json
import pathlib
import time

os.environ.setdefault("HF_HOME", "/scratch/hpc198a01/젬마4해커톤/hf_cache")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
import unsloth
from unsloth import FastLanguageModel

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
sys.path.insert(0, str(PROJ / "tools/fae_protocol"))
from score_translit_auto import score_one  # noqa: E402

PROBES_FILE = PROJ / "tools/fae_protocol/probes_v2_translit.jsonl"
OUT_FILE = pathlib.Path(os.environ.get(
    "G2EXT_OUT_FILE",
    str(PROJ / "paper/figures/g2_extended_scores.json")))
LORA_OUT = PROJ / "lora_out"
STOCK = PROJ / "models/unsloth-gemma-4-E2B-it"
MAX_NEW = 80
MAX_SEQ = 2048

FILTER = os.environ.get("VARIANTS_FILTER", "")


def log(msg: str) -> None:
    print(msg, flush=True)


def discover():
    """List of (name, path, is_adapter)."""
    pf = [p.strip() for p in FILTER.split(",") if p.strip()]
    wanted = set(pf)
    items = []
    if not wanted or "stock" in wanted:
        items.append(("stock", str(STOCK), False))
    for d in sorted(LORA_OUT.iterdir()):
        if not d.is_dir(): continue
        if wanted and d.name not in wanted: continue
        ad = d / "adapter"
        if ad.is_dir() and (ad / "adapter_config.json").exists():
            items.append((d.name, str(ad), True))
        else:
            ck = d / "checkpoint-4500"
            if ck.is_dir() and (ck / "adapter_config.json").exists():
                items.append((d.name, str(ck), True))
    return items


def load_probes():
    return [json.loads(l) for l in PROBES_FILE.open() if l.strip()]


def gen_one(model, tok, prompt: str) -> str:
    msgs = [{"role": "user", "content": prompt}]
    text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    text_tok = getattr(tok, "tokenizer", tok)
    enc = text_tok(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=MAX_NEW, do_sample=False,
                             temperature=None, top_p=None, top_k=None)
    new_ids = out[0][enc["input_ids"].shape[1]:]
    return text_tok.decode(new_ids, skip_special_tokens=True).strip()


def score_variant(name: str, model_path: str, is_adapter: bool, probes: list) -> dict:
    log(f"[load] {name} from {model_path}")
    t0 = time.time()
    if is_adapter:
        model, tok = FastLanguageModel.from_pretrained(
            model_name=model_path, max_seq_length=MAX_SEQ,
            load_in_4bit=False, load_in_16bit=True, full_finetuning=False,
        )
    else:
        model, tok = FastLanguageModel.from_pretrained(
            model_name=model_path, max_seq_length=MAX_SEQ,
            load_in_4bit=False, load_in_16bit=True, full_finetuning=False,
        )
    FastLanguageModel.for_inference(model)
    log(f"[load] {name} done in {time.time()-t0:.1f}s")

    by_dir = {}
    correct_total = 0
    rows = []
    for i, p in enumerate(probes, 1):
        out = gen_one(model, tok, p["prompt"])
        s = score_one(out, p["expect_script"])
        d = p["direction"]
        by_dir.setdefault(d, {"correct": 0, "total": 0})
        by_dir[d]["total"] += 1
        if s["script_correct"]:
            by_dir[d]["correct"] += 1
            correct_total += 1
        rows.append({
            "id": p["id"],
            "direction": d,
            "expect_script": p["expect_script"],
            "output": out,
            "output_preview": out[:140],
            "script_correct": s["script_correct"],
            "target_ratio": s["target_ratio"],
        })
        log(f"[probe] {name} {i:02d}/{len(probes)} {p['id']} "
            f"{'PASS' if s['script_correct'] else 'FAIL'} "
            f"out={out[:60]!r}")

    n = len(probes)
    summary = {
        "name": name,
        "g2_score": correct_total,
        "g2_total": n,
        "g2_pass_rate": correct_total / n if n else 0.0,
        "by_direction": {d: {"correct": v["correct"], "total": v["total"],
                             "pass_rate": v["correct"] / v["total"]}
                         for d, v in by_dir.items()},
        "per_probe": rows,
    }

    # Cleanup model to free VRAM
    del model, tok
    torch.cuda.empty_cache()
    return summary


def main():
    probes = load_probes()
    log(f"[probes] {len(probes)} G2 probes loaded")
    variants = discover()
    log(f"[variants] {len(variants)} variants to evaluate")
    for v in variants:
        log(f"  - {v[0]}")

    # Load existing JSON if any (for incremental runs)
    if OUT_FILE.exists():
        existing = json.loads(OUT_FILE.read_text())
    else:
        existing = {"variants": {}}

    for name, path, is_adapter in variants:
        if name in existing["variants"]:
            log(f"[skip] {name} (already scored: {existing['variants'][name]['g2_score']}/52)")
            continue
        try:
            res = score_variant(name, path, is_adapter, probes)
        except Exception as e:
            log(f"[fail] {name}: {e}")
            continue
        existing["variants"][name] = res
        OUT_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
        log(f"[score] {name} -> G2 {res['g2_score']}/{res['g2_total']} = {res['g2_pass_rate']:.1%}")

    log("\n=== Summary ===")
    for n, r in existing["variants"].items():
        log(f"  {n:30s} G2={r['g2_score']:>2}/{r['g2_total']}  ({r['g2_pass_rate']:.1%})")


if __name__ == "__main__":
    main()
