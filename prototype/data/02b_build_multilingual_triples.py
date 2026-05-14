#!/usr/bin/env python3
"""Build multilingual trilingual triples beyond KO+RU+EN.

For each (target_lang, l2_lang) pair (with EN as bridge), index all KO and L2
sentences sharing an English midpoint, emit (KO, L2, EN) triple.

Output:
  prototype/data/raw/trilingual_ko_vie_en.jsonl
  prototype/data/raw/trilingual_ko_cmn_en.jsonl

Same algorithm as 02_build_trilingual_triples.py but parameterized.
"""
from __future__ import annotations
import json, pathlib, collections

PROJ = pathlib.Path("/PATH/REDACTED")
RAW = PROJ / "prototype/data/raw"

PAIRS = [
    # (l2_lang, l2_short, kor_l2_jsonl, l2_eng_jsonl, output_name)
    ("vie", "vi", "tatoeba_kor-vie.jsonl", "tatoeba_vie-eng.jsonl", "trilingual_ko_vi_en"),
    ("cmn", "zh", "tatoeba_kor-cmn.jsonl", "tatoeba_cmn-eng.jsonl", "trilingual_ko_zh_en"),
]


def load_jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def main():
    ko_en = load_jsonl(RAW / "tatoeba_kor-eng.jsonl")
    print(f"[ko-en] {len(ko_en)} pairs")

    ko_by_en = collections.defaultdict(list)
    for d in ko_en:
        ko_by_en[d["eng"].strip().lower()].append(d["kor"])

    for l2_long, l2_short, _direct_file, l2_en_file, out_name in PAIRS:
        l2_en = load_jsonl(RAW / l2_en_file)
        print(f"[{l2_long}-en] {len(l2_en)} pairs")

        l2_by_en = collections.defaultdict(list)
        for d in l2_en:
            l2_by_en[d["eng"].strip().lower()].append(d[l2_long])

        out_path = RAW / f"{out_name}.jsonl"
        n = 0
        with out_path.open("w", encoding="utf-8") as fo:
            for en_key in set(ko_by_en) & set(l2_by_en):
                for kor in ko_by_en[en_key][:3]:
                    for x in l2_by_en[en_key][:3]:
                        fo.write(json.dumps({"ko": kor, l2_short: x, "en": en_key}, ensure_ascii=False) + "\n")
                        n += 1
        print(f"[triple] {l2_long}: {n} -> {out_name}.jsonl")


if __name__ == "__main__":
    main()
