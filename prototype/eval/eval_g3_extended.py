#!/usr/bin/env python3
"""Evaluate the extended 80-probe G3 JSON/schema set on selected adapters.

This script is prepared for the next empirical hardening pass. It mirrors the
G2 extended evaluator but scores JSON/schema correctness.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import time

os.environ.setdefault("HF_HOME", "/scratch/hpc198a01/젬마4해커톤/hf_cache")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
import unsloth
from unsloth import FastLanguageModel

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
sys.path.insert(0, str(PROJ / "tools/fae_protocol"))
from score_schema_auto import score_one  # noqa: E402

PROBES_FILE = PROJ / "tools/fae_protocol/probes_v3_schema.jsonl"
OUT_FILE = pathlib.Path(os.environ.get(
    "G3EXT_OUT_FILE",
    str(PROJ / "paper/figures/g3_extended_scores.json")))
LORA_OUT = PROJ / "lora_out"
STOCK = PROJ / "models/unsloth-gemma-4-E2B-it"
MAX_NEW = 160
MAX_SEQ = 2048
FILTER = os.environ.get("VARIANTS_FILTER", "")


def log(msg: str) -> None:
    print(msg, flush=True)


def discover():
    wanted = {p.strip() for p in FILTER.split(",") if p.strip()}
    items = []
    if not wanted or "stock" in wanted:
        items.append(("stock", str(STOCK), False))
    for d in sorted(LORA_OUT.iterdir()):
        if not d.is_dir() or (wanted and d.name not in wanted):
            continue
        ad = d / "adapter"
        ck = d / "checkpoint-4500"
        if ad.is_dir() and (ad / "adapter_config.json").exists():
            items.append((d.name, str(ad), True))
        elif ck.is_dir() and (ck / "adapter_config.json").exists():
            items.append((d.name, str(ck), True))
    return items


def load_probes():
    return [json.loads(l) for l in PROBES_FILE.read_text().splitlines() if l.strip()]


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
    model, tok = FastLanguageModel.from_pretrained(
        model_name=model_path,
        max_seq_length=MAX_SEQ,
        load_in_4bit=False,
        load_in_16bit=True,
        full_finetuning=False,
    )
    FastLanguageModel.for_inference(model)
    log(f"[load] {name} done in {time.time() - t0:.1f}s")

    by_group = {}
    rows = []
    correct = 0
    for i, p in enumerate(probes, 1):
        out = gen_one(model, tok, p["prompt"])
        s = score_one(out, p)
        group = p.get("group", "?")
        by_group.setdefault(group, {"correct": 0, "total": 0})
        by_group[group]["total"] += 1
        if s["schema_correct"]:
            by_group[group]["correct"] += 1
            correct += 1
        rows.append({
            "id": p["id"],
            "group": group,
            "output": out,
            "schema_correct": s["schema_correct"],
            "json_parse_ok": s["json_parse_ok"],
            "reason": s["reason"],
            "missing_keys": s["missing_keys"],
            "type_errors": s["type_errors"],
            "enum_errors": s["enum_errors"],
            "extra_keys": s["extra_keys"],
        })
        log(f"[probe] {name} {i:02d}/{len(probes)} {p['id']} "
            f"{'PASS' if s['schema_correct'] else 'FAIL'} reason={s['reason']}")

    del model, tok
    torch.cuda.empty_cache()
    n = len(probes)
    return {
        "name": name,
        "g3_score": correct,
        "g3_total": n,
        "g3_pass_rate": correct / n if n else 0.0,
        "by_group": {g: {"correct": v["correct"], "total": v["total"],
                         "pass_rate": v["correct"] / v["total"] if v["total"] else 0.0}
                     for g, v in by_group.items()},
        "per_probe": rows,
    }


def main() -> None:
    probes = load_probes()
    log(f"[probes] {len(probes)} G3 probes loaded")
    existing = json.loads(OUT_FILE.read_text()) if OUT_FILE.exists() else {"variants": {}}
    for name, path, is_adapter in discover():
        if name in existing["variants"]:
            log(f"[skip] {name}")
            continue
        try:
            existing["variants"][name] = score_variant(name, path, is_adapter, probes)
        except Exception as exc:
            log(f"[fail] {name}: {exc}")
            continue
        OUT_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
    log(f"[write] {OUT_FILE}")


if __name__ == "__main__":
    main()
