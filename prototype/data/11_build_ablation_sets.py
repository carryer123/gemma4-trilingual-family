#!/usr/bin/env python3
"""Build ablation training sets for Plan B (bridge-pivot + policy-frequency).

Variants produced:
  L-direct          — KO-RU/KO-EN/RU-EN direct pairs only, no pivot
  L-pivot-only      — KO+RU+EN triples only, no direct
  L-pivot-filtered  — pivot triples after round-trip similarity filter (placeholder: keep top 70% by length-similarity heuristic)
  L-policy-X%       — translation pairs + X% transliteration fraction (X ∈ {0, 1, 3, 5, 10})
  L-multilingual    — KO+RU+EN + KO+VI+EN + KO+ZH+EN combined

Output: prototype/data/ablation/{variant}_train.jsonl
"""
from __future__ import annotations
import json, pathlib, random, sys

random.seed(20260507)

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
RAW = PROJ / "prototype/data/raw"
ABL = PROJ / "prototype/data/ablation"
ABL.mkdir(parents=True, exist_ok=True)


def jsonl(p):
    if not p.exists():
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


def length_similarity(a: str, b: str) -> float:
    """Heuristic round-trip similarity proxy: |1 - |la-lb|/max(la,lb)|."""
    la, lb = len(a), len(b)
    if max(la, lb) == 0:
        return 0.0
    return 1.0 - abs(la - lb) / max(la, lb)


def expand_pair_to_chat(pairs_file: pathlib.Path, sl: str, tl: str, sl_key: str, tl_key: str, n_max: int = 5000):
    rows = []
    data = jsonl(pairs_file)
    random.shuffle(data)
    for d in data[:n_max]:
        rows.append(to_chat_pair(sl, tl, d[sl_key], d[tl_key]))
        rows.append(to_chat_pair(tl, sl, d[tl_key], d[sl_key]))
    return rows


def expand_triple_six_dir(triples, n_max=2000):
    rows = []
    random.shuffle(triples)
    for d in triples[:n_max]:
        ko, ru, en = d.get("ko"), d.get("ru"), d.get("en")
        if not (ko and ru and en):
            continue
        for a, b in [("ko","ru"),("ru","ko"),("ko","en"),("en","ko"),("ru","en"),("en","ru")]:
            sa, sb = locals()[a], locals()[b]
            rows.append(to_chat_pair(a, b, sa, sb))
    return rows


def write_set(name: str, rows: list):
    out = ABL / f"{name}_train.jsonl"
    random.shuffle(rows)
    with out.open("w", encoding="utf-8") as fo:
        for r in rows:
            fo.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[{name}] {len(rows)} -> {out}")


def main():
    # Loads
    p_kor_rus = jsonl(RAW / "tatoeba_kor-rus.jsonl")
    p_kor_eng = jsonl(RAW / "tatoeba_kor-eng.jsonl")
    p_rus_eng = jsonl(RAW / "tatoeba_rus-eng.jsonl")
    triples = jsonl(RAW / "trilingual_ko_ru_en.jsonl")
    transliteration = jsonl(RAW / "transliteration.jsonl")
    fcs = jsonl(RAW / "function_calls.jsonl")
    obj_cards = jsonl(RAW / "object_cards.jsonl")
    scens = jsonl(RAW / "family_scenarios.jsonl")
    triples_vi = jsonl(RAW / "trilingual_ko_vi_en.jsonl")
    triples_zh = jsonl(RAW / "trilingual_ko_zh_en.jsonl")

    # ---------- L-direct: only Tatoeba direct pairs, no triples
    rows = []
    for d in p_kor_rus:
        rows += [to_chat_pair("ko","ru",d["kor"],d["rus"]), to_chat_pair("ru","ko",d["rus"],d["kor"])]
    random.shuffle(p_kor_eng); random.shuffle(p_rus_eng)
    for d in p_kor_eng[:1500]:
        rows += [to_chat_pair("ko","en",d["kor"],d["eng"]), to_chat_pair("en","ko",d["eng"],d["kor"])]
    for d in p_rus_eng[:1500]:
        rows += [to_chat_pair("ru","en",d["rus"],d["eng"]), to_chat_pair("en","ru",d["eng"],d["rus"])]
    rows += fcs
    rows += transliteration
    write_set("L_direct", rows)

    # ---------- L-pivot-only: only triples, no direct Tatoeba
    rows = expand_triple_six_dir(triples, n_max=2000)
    rows += fcs
    rows += transliteration
    write_set("L_pivot_only", rows)

    # ---------- L-pivot-filtered: triples passing length-similarity heuristic >= 0.7
    filtered = [t for t in triples if length_similarity(t["ko"], t["ru"]) >= 0.7]
    print(f"[pivot-filtered] {len(filtered)}/{len(triples)} triples kept ({100*len(filtered)/max(1,len(triples)):.0f}%)")
    rows = expand_triple_six_dir(filtered, n_max=2000)
    rows += fcs
    rows += transliteration
    write_set("L_pivot_filtered", rows)

    # ---------- L-policy-X%: translation pairs + X% transliteration fraction
    base_rows = []
    random.shuffle(p_kor_rus); random.shuffle(p_kor_eng); random.shuffle(p_rus_eng)
    for d in p_kor_rus:
        base_rows += [to_chat_pair("ko","ru",d["kor"],d["rus"]), to_chat_pair("ru","ko",d["rus"],d["kor"])]
    for d in p_kor_eng[:1500]:
        base_rows += [to_chat_pair("ko","en",d["kor"],d["eng"]), to_chat_pair("en","ko",d["eng"],d["kor"])]
    for d in p_rus_eng[:1500]:
        base_rows += [to_chat_pair("ru","en",d["rus"],d["eng"]), to_chat_pair("en","ru",d["eng"],d["rus"])]
    base_rows += expand_triple_six_dir(triples, n_max=1500)  # smaller pivot to keep runs comparable
    base_count = len(base_rows)

    for pct in [0, 1, 3, 5, 10]:
        n_translit = int(base_count * pct / 100) if pct > 0 else 0
        translit_subset = transliteration[:n_translit] if n_translit > 0 else []
        rows = list(base_rows)
        rows += translit_subset
        rows += fcs   # function calls always included (small, not tested as variable)
        write_set(f"L_policy_{pct:02d}", rows)

    # ---------- L-multilingual: all 3 trilingual sets combined
    rows = expand_triple_six_dir(triples, n_max=1500)
    rows += expand_triple_six_dir([{"ko":t["ko"],"ru":t["vi"],"en":t["en"]} for t in triples_vi], n_max=800)  # treat VI as ru-slot
    rows += expand_triple_six_dir([{"ko":t["ko"],"ru":t["zh"],"en":t["en"]} for t in triples_zh], n_max=800)
    rows += fcs
    rows += transliteration
    if obj_cards:
        from_cards = [{"messages":[
            {"role":"system","content":"You are the trilingual KO/RU/EN family AI tutor."},
            {"role":"user","content":f"Object: {c['meta']['kor']} (category: {c['meta']['category']})"},
            {"role":"assistant","content": json.dumps(c['card'], ensure_ascii=False)}
        ]} for c in obj_cards[:1000]]
        rows += from_cards
    if scens:
        from_scens = [{"messages":[
            {"role":"system","content":"You are the trilingual KO/RU/EN family AI tutor. Generate JSON dialogs for daily co-learning."},
            {"role":"user","content": f"Scenario: {s['meta']['scenario']}\nAge: {s['meta']['age_band']}\n"},
            {"role":"assistant","content": json.dumps(s['scenario'], ensure_ascii=False)}
        ]} for s in scens[:800]]
        rows += from_scens
    write_set("L_multilingual", rows)


if __name__ == "__main__":
    main()
