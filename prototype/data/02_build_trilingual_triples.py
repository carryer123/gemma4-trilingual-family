#!/usr/bin/env python3
"""Triangulate KO-EN and RU-EN Tatoeba pairs to build (KO, RU, EN) triples.

Why: direct KO-RU pairs are scarce; pivoting through EN explodes the count.
Quality: only emit triple if KO->EN->RU back-translation distance is small.
For v1 we just emit all triples that share an EN sentence (high recall).

Output: prototype/data/raw/trilingual_ko_ru_en.jsonl
"""
from __future__ import annotations
import json, pathlib, collections

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
RAW = PROJ / "prototype/data/raw"
OUT = RAW / "trilingual_ko_ru_en.jsonl"


def load_jsonl(p: pathlib.Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def main():
    ko_en = load_jsonl(RAW / "tatoeba_kor-eng.jsonl")
    ru_en = load_jsonl(RAW / "tatoeba_rus-eng.jsonl")
    print(f"[load] ko-en: {len(ko_en)}, ru-en: {len(ru_en)}")

    # index by EN
    ko_by_en: dict[str, list[str]] = collections.defaultdict(list)
    for d in ko_en:
        ko_by_en[d["eng"].strip().lower()].append(d["kor"])
    ru_by_en: dict[str, list[str]] = collections.defaultdict(list)
    for d in ru_en:
        ru_by_en[d["eng"].strip().lower()].append(d["rus"])

    n = 0
    with OUT.open("w", encoding="utf-8") as fo:
        for en_key in set(ko_by_en) & set(ru_by_en):
            for kor in ko_by_en[en_key][:3]:
                for rus in ru_by_en[en_key][:3]:
                    # try to recover original-cased EN from one of the dicts
                    fo.write(json.dumps({"ko": kor, "ru": rus, "en": en_key}, ensure_ascii=False) + "\n")
                    n += 1
    print(f"[triples] {n} -> {OUT.name}")


if __name__ == "__main__":
    main()
