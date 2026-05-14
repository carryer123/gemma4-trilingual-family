#!/usr/bin/env python3
"""Download Tatoeba sentence pairs for KO-RU, KO-EN, RU-EN.

Tatoeba dump: https://downloads.tatoeba.org/exports/sentences.csv (CC-BY)
                                              /links.csv

Output: prototype/data/raw/tatoeba_{kor-rus,kor-eng,rus-eng}.jsonl
"""
from __future__ import annotations
import os, csv, json, urllib.request, gzip, io, pathlib, time

PROJ = pathlib.Path("/PATH/REDACTED")
RAW = PROJ / "prototype/data/raw"
RAW.mkdir(parents=True, exist_ok=True)

URL_SENT = "https://downloads.tatoeba.org/exports/sentences.csv"  # ~200MB
URL_LINK = "https://downloads.tatoeba.org/exports/links.csv"      # ~1GB

PAIRS = [
    ("kor", "rus"), ("kor", "eng"), ("rus", "eng"),
    # multilingual generalization (added 2026-05-07 for Plan B):
    ("kor", "vie"), ("vie", "eng"),
    ("kor", "cmn"), ("cmn", "eng"),
]


def download(url: str, dest: pathlib.Path) -> None:
    if dest.exists() and dest.stat().st_size > 1024:
        print(f"[skip] {dest.name} already exists ({dest.stat().st_size:,} bytes)")
        return
    print(f"[download] {url}")
    t0 = time.time()
    urllib.request.urlretrieve(url, dest)
    print(f"   -> {dest.name} {dest.stat().st_size/1e6:.1f} MB in {time.time()-t0:.1f}s")


def load_sentences(path: pathlib.Path, langs: set[str]) -> dict[int, tuple[str, str]]:
    """Return {sent_id: (lang, text)} for sentences in the language set."""
    out: dict[int, tuple[str, str]] = {}
    with open(path, encoding="utf-8") as f:
        rdr = csv.reader(f, delimiter="\t")
        for row in rdr:
            if len(row) < 3:
                continue
            sid, lang, text = row[0], row[1], row[2]
            if lang in langs:
                try:
                    out[int(sid)] = (lang, text)
                except ValueError:
                    continue
    print(f"[sentences] loaded {len(out)} sentences in {sorted(langs)}")
    return out


def emit_pairs(sent_path: pathlib.Path, link_path: pathlib.Path,
               lang_a: str, lang_b: str, out_path: pathlib.Path) -> int:
    """Stream links.csv, emit (a_text, b_text) JSONL where direction matches."""
    sents = load_sentences(sent_path, {lang_a, lang_b})
    n = 0
    seen = set()
    with open(link_path, encoding="utf-8") as f, out_path.open("w", encoding="utf-8") as fo:
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
            elif la == lang_b and lb == lang_a:
                key = (t, s)
                ta, tb = tb, ta  # swap
            else:
                continue
            if key in seen:
                continue
            seen.add(key)
            fo.write(json.dumps({lang_a: ta, lang_b: tb}, ensure_ascii=False) + "\n")
            n += 1
    print(f"[pairs] {lang_a}-{lang_b}: {n} -> {out_path.name}")
    return n


def main():
    sent_csv = RAW / "tatoeba_sentences.csv"
    link_csv = RAW / "tatoeba_links.csv"
    download(URL_SENT, sent_csv)
    download(URL_LINK, link_csv)
    for la, lb in PAIRS:
        out = RAW / f"tatoeba_{la}-{lb}.jsonl"
        emit_pairs(sent_csv, link_csv, la, lb, out)


if __name__ == "__main__":
    main()
