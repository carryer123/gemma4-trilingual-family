#!/usr/bin/env python3
"""Run prompts through Gemma 4 26B (with MTP drafter) to synthesize learning cards.

Reads:  prototype/data/raw/object_cards_prompts.jsonl
Writes: prototype/data/raw/object_cards.jsonl
        prototype/data/raw/object_cards_failed.jsonl  (for retry)

Uses transformers + vLLM if available; falls back to plain HF generate.
JSON validation: every output must parse + contain top-level keys.
"""
from __future__ import annotations
import os, json, pathlib, time, sys
import torch

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
os.environ.setdefault("HF_HOME", str(PROJ / "hf_cache"))
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

RAW = PROJ / "prototype/data/raw"
PROMPTS = RAW / "object_cards_prompts.jsonl"
OUT = RAW / "object_cards.jsonl"
FAIL = RAW / "object_cards_failed.jsonl"

MODEL_ID = os.environ.get("MODEL_ID", "google/gemma-4-26b-it")
MAX_NEW = int(os.environ.get("MAX_NEW", "1500"))
MAX_PROMPTS = int(os.environ.get("MAX_PROMPTS", "0"))  # 0 = all
DEVICE_MAP = os.environ.get("DEVICE_MAP", "auto")


def load_prompts():
    rows = [json.loads(l) for l in PROMPTS.read_text(encoding="utf-8").splitlines() if l.strip()]
    if MAX_PROMPTS:
        rows = rows[:MAX_PROMPTS]
    return rows


def is_valid(obj) -> bool:
    if not isinstance(obj, dict):
        return False
    needed = {"word", "phonetic", "wife_card", "husband_card", "child_card", "l1_contrast"}
    if not needed.issubset(obj):
        return False
    return True


def main_hf():
    from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
    print(f"[load] {MODEL_ID}")
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, torch_dtype=torch.bfloat16, device_map=DEVICE_MAP
    ).eval()

    prompts = load_prompts()
    print(f"[run] {len(prompts)} prompts")

    n_ok = n_fail = 0
    t0 = time.time()
    with OUT.open("w", encoding="utf-8") as fo, FAIL.open("w", encoding="utf-8") as ff:
        for i, row in enumerate(prompts):
            messages = [
                {"role": "system", "content": row["system"]},
                {"role": "user", "content": row["user"]},
            ]
            inputs = tok.apply_chat_template(messages, return_tensors="pt", add_generation_prompt=True).to(model.device)
            with torch.inference_mode():
                out = model.generate(
                    inputs,
                    max_new_tokens=MAX_NEW,
                    do_sample=True, temperature=0.7, top_p=0.9,
                    pad_token_id=tok.eos_token_id,
                )
            text = tok.decode(out[0][inputs.shape[1]:], skip_special_tokens=True).strip()
            try:
                obj = json.loads(text)
                if is_valid(obj):
                    fo.write(json.dumps({"meta": row["meta"], "card": obj}, ensure_ascii=False) + "\n")
                    n_ok += 1
                else:
                    ff.write(json.dumps({"meta": row["meta"], "raw": text, "reason": "schema"}, ensure_ascii=False) + "\n")
                    n_fail += 1
            except Exception as e:
                ff.write(json.dumps({"meta": row["meta"], "raw": text, "reason": str(e)}, ensure_ascii=False) + "\n")
                n_fail += 1
            if (i + 1) % 25 == 0:
                rate = (i + 1) / (time.time() - t0)
                print(f"  [{i+1}/{len(prompts)}] ok={n_ok} fail={n_fail} {rate:.2f}/s", flush=True)
    print(f"[done] ok={n_ok} fail={n_fail} elapsed={(time.time()-t0)/60:.1f}min")


if __name__ == "__main__":
    main_hf()
