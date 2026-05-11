#!/usr/bin/env python3
"""Extract French pair files from the local Tatoeba dumps.

The existing pipeline already keeps `sentences.csv` and `links.csv` under
`prototype/data/raw/`.  This script adds the French edges needed for the
four-language KO/RU/FR/EN experiment:

  * tatoeba_kor-fra.jsonl
  * tatoeba_fra-eng.jsonl
  * tatoeba_rus-fra.jsonl

No network access is required when the dumps already exist.
"""
from __future__ import annotations

import csv
import json
import pathlib


PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
RAW = PROJ / "prototype/data/raw"
SENT_CSV = RAW / "tatoeba_sentences.csv"
LINK_CSV = RAW / "tatoeba_links.csv"

PAIRS = [("kor", "fra"), ("fra", "eng"), ("rus", "fra")]


def load_sentences(path: pathlib.Path, langs: set[str]) -> dict[int, tuple[str, str]]:
    out: dict[int, tuple[str, str]] = {}
    with path.open(encoding="utf-8") as f:
        rdr = csv.reader(f, delimiter="\t")
        for row in rdr:
            if len(row) < 3:
                continue
            sid, lang, text = row[0], row[1], row[2]
            if lang not in langs:
                continue
            try:
                out[int(sid)] = (lang, text)
            except ValueError:
                continue
    print(f"[sentences] {len(out):,} rows for {sorted(langs)}")
    return out


def emit_pair(lang_a: str, lang_b: str) -> int:
    out_path = RAW / f"tatoeba_{lang_a}-{lang_b}.jsonl"
    if out_path.exists() and out_path.stat().st_size > 1024:
        print(f"[skip] {out_path.name} exists ({out_path.stat().st_size:,} bytes)")
        return sum(1 for _ in out_path.open(encoding="utf-8"))

    sents = load_sentences(SENT_CSV, {lang_a, lang_b})
    seen: set[tuple[int, int]] = set()
    n = 0
    with LINK_CSV.open(encoding="utf-8") as f, out_path.open("w", encoding="utf-8") as fo:
        rdr = csv.reader(f, delimiter="\t")
        for row in rdr:
            if len(row) < 2:
                continue
            try:
                s, t = int(row[0]), int(row[1])
            except ValueError:
                continue
            if s not in sents or t not in sents:
                continue
            la, ta = sents[s]
            lb, tb = sents[t]
            if la == lang_a and lb == lang_b:
                key = (s, t)
                a_text, b_text = ta, tb
            elif la == lang_b and lb == lang_a:
                key = (t, s)
                a_text, b_text = tb, ta
            else:
                continue
            if key in seen:
                continue
            seen.add(key)
            fo.write(json.dumps({lang_a: a_text, lang_b: b_text}, ensure_ascii=False) + "\n")
            n += 1
    print(f"[pair] {lang_a}-{lang_b}: {n:,} -> {out_path.name}")
    return n


def main() -> None:
    assert SENT_CSV.exists(), f"missing {SENT_CSV}"
    assert LINK_CSV.exists(), f"missing {LINK_CSV}"
    for a, b in PAIRS:
        emit_pair(a, b)


if __name__ == "__main__":
    main()
