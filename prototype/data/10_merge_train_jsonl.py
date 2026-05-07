#!/usr/bin/env python3
"""Merge curated sources → final train.jsonl in the format Unsloth/TRL expects.

Sources:
  raw/tatoeba_kor-rus.jsonl      — 2.5K
  raw/tatoeba_kor-eng.jsonl      — 1.5K
  raw/tatoeba_rus-eng.jsonl      — 1.5K
  raw/trilingual_ko_ru_en.jsonl  — 2K (post-pivot)
  raw/object_cards.jsonl         — 1.5K (after 04_run_synth)
  raw/family_scenarios.jsonl     — 1.5K (after 04_run_synth on prompts file)
  raw/function_calls.jsonl       — 500
  + stub categories (l1_aware, age_tone, safety_refusal, regression) for v1

Output:
  prototype/data/train_v1.jsonl     — main training file
  prototype/data/eval_v1.jsonl      — held-out 5%
"""
from __future__ import annotations
import json, pathlib, random, sys

random.seed(20260506)

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
RAW = PROJ / "prototype/data/raw"
DATA = PROJ / "prototype/data"
TRAIN_OUT = DATA / "train_v1.jsonl"
EVAL_OUT = DATA / "eval_v1.jsonl"


def jsonl(p: pathlib.Path):
    if not p.exists():
        print(f"[warn] missing: {p.name}", file=sys.stderr)
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def to_chat_pair(src_lang, tgt_lang, src_text, tgt_text):
    return {
        "messages": [
            {"role": "system", "content": f"Translate {src_lang.upper()} to {tgt_lang.upper()}."},
            {"role": "user", "content": src_text},
            {"role": "assistant", "content": tgt_text},
        ]
    }


def to_chat_card(card_meta, card):
    sys = (
        "You are the trilingual KO/RU/EN family AI tutor. "
        f"Family: father (KO L1), mother (RU L1, bridge={card_meta['bridge_for_wife']}), "
        f"child age {card_meta['age_band']}. "
        "When given a Korean object, output the trilingual JSON learning card."
    )
    return {
        "messages": [
            {"role": "system", "content": sys},
            {"role": "user", "content": f"Object: {card_meta['kor']} (category: {card_meta['category']})"},
            {"role": "assistant", "content": json.dumps(card, ensure_ascii=False)},
        ]
    }


def to_chat_scenario(meta, scen):
    sys = "You are the trilingual KO/RU/EN family AI tutor. Generate JSON dialogs for daily co-learning."
    return {
        "messages": [
            {"role": "system", "content": sys},
            {"role": "user", "content": (
                f"Scenario: {meta['scenario']}\nAge: {meta['age_band']}\n"
                f"Mother KO level: {meta['parent_ko_level']}\nBridge: {meta['wife_bridge']}\n"
            )},
            {"role": "assistant", "content": json.dumps(scen, ensure_ascii=False)},
        ]
    }


def main():
    rows = []

    # Translation pairs (subsample to target counts)
    ko_ru = jsonl(RAW / "tatoeba_kor-rus.jsonl")
    random.shuffle(ko_ru)
    for d in ko_ru[:2500]:
        rows.append(to_chat_pair("ko", "ru", d["kor"], d["rus"]))
        rows.append(to_chat_pair("ru", "ko", d["rus"], d["kor"]))

    ko_en = jsonl(RAW / "tatoeba_kor-eng.jsonl")
    random.shuffle(ko_en)
    for d in ko_en[:1500]:
        rows.append(to_chat_pair("ko", "en", d["kor"], d["eng"]))
        rows.append(to_chat_pair("en", "ko", d["eng"], d["kor"]))

    ru_en = jsonl(RAW / "tatoeba_rus-eng.jsonl")
    random.shuffle(ru_en)
    for d in ru_en[:1500]:
        rows.append(to_chat_pair("ru", "en", d["rus"], d["eng"]))
        rows.append(to_chat_pair("en", "ru", d["eng"], d["rus"]))

    triples = jsonl(RAW / "trilingual_ko_ru_en.jsonl")
    random.shuffle(triples)
    for d in triples[:2000]:
        # 6 directional pairs from each triple
        for a, b in [("ko","ru"),("ru","ko"),("ko","en"),("en","ko"),("ru","en"),("en","ru")]:
            rows.append(to_chat_pair(a, b, d[a], d[b]))

    # Object cards (after model fills them — for v1 may be empty)
    cards = jsonl(RAW / "object_cards.jsonl")
    for c in cards:
        rows.append(to_chat_card(c["meta"], c["card"]))

    # Family scenarios (after model fill)
    scens = jsonl(RAW / "family_scenarios.jsonl")
    for s in scens:
        rows.append(to_chat_scenario(s["meta"], s["scenario"]))

    # Function calls
    fcs = jsonl(RAW / "function_calls.jsonl")
    rows.extend(fcs)

    # Transliteration (added v2 — fix for hidden script-direction failure)
    translits = jsonl(RAW / "transliteration.jsonl")
    rows.extend(translits)

    # Shuffle final
    random.shuffle(rows)

    # 95/5 split
    n_eval = max(50, len(rows) // 20)
    eval_rows = rows[:n_eval]
    train_rows = rows[n_eval:]

    with TRAIN_OUT.open("w", encoding="utf-8") as fo:
        for r in train_rows:
            fo.write(json.dumps(r, ensure_ascii=False) + "\n")
    with EVAL_OUT.open("w", encoding="utf-8") as fo:
        for r in eval_rows:
            fo.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[merge] train={len(train_rows)} eval={len(eval_rows)}")
    print(f"  -> {TRAIN_OUT}")
    print(f"  -> {EVAL_OUT}")


if __name__ == "__main__":
    main()
