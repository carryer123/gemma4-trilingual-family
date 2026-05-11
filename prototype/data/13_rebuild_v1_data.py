#!/usr/bin/env python3
"""Rebuild the EXACT data mix lora_v1 was trained on (v2 minus transliteration).

The original train_v1.jsonl was overwritten by 10_merge_train_jsonl.py when we
added transliteration. To investigate whether lora_v1's transliteration
regression is data-specific, we reconstruct the v1 mix and retrain with a
dense step grid (save_steps=250).

train_v1_recreated = Tatoeba 6-direction + triples + object_cards + scenarios + function_calls
  (NO transliteration, ~18K)
"""
import json, pathlib, random
random.seed(20260506)  # match lora_v1's seed

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
RAW = PROJ / "prototype/data/raw"
ABL = PROJ / "prototype/data/ablation"
OUT = ABL / "L_v1_recreate_train.jsonl"


def jsonl(p):
    if not p.exists(): return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def to_chat_pair(sl, tl, s, t):
    return {"messages": [
        {"role": "system", "content": f"Translate {sl.upper()} to {tl.upper()}."},
        {"role": "user", "content": s},
        {"role": "assistant", "content": t},
    ]}


def expand_triples(triples, n_max):
    rows = []
    random.shuffle(triples)
    for d in triples[:n_max]:
        ko, ru, en = d.get("ko"), d.get("ru"), d.get("en")
        if not (ko and ru and en): continue
        for a, b in [("ko","ru"),("ru","ko"),("ko","en"),("en","ko"),("ru","en"),("en","ru")]:
            sa, sb = locals()[a], locals()[b]
            rows.append(to_chat_pair(a, b, sa, sb))
    return rows


def main():
    p_kor_rus = jsonl(RAW / "tatoeba_kor-rus.jsonl")
    p_kor_eng = jsonl(RAW / "tatoeba_kor-eng.jsonl")
    p_rus_eng = jsonl(RAW / "tatoeba_rus-eng.jsonl")
    triples = jsonl(RAW / "trilingual_ko_ru_en.jsonl")
    fcs = jsonl(RAW / "function_calls.jsonl")
    obj_cards = jsonl(RAW / "object_cards.jsonl")
    scens = jsonl(RAW / "family_scenarios.jsonl")

    rows = []
    random.shuffle(p_kor_rus); random.shuffle(p_kor_eng); random.shuffle(p_rus_eng)
    for d in p_kor_rus:
        rows += [to_chat_pair("ko","ru",d["kor"],d["rus"]), to_chat_pair("ru","ko",d["rus"],d["kor"])]
    for d in p_kor_eng[:1500]:
        rows += [to_chat_pair("ko","en",d["kor"],d["eng"]), to_chat_pair("en","ko",d["eng"],d["kor"])]
    for d in p_rus_eng[:1500]:
        rows += [to_chat_pair("ru","en",d["rus"],d["eng"]), to_chat_pair("en","ru",d["eng"],d["rus"])]
    rows += expand_triples(triples, n_max=2000)

    # object cards as chat
    for c in obj_cards[:1294]:
        rows.append({"messages":[
            {"role":"system","content":"You are the trilingual KO/RU/EN family AI tutor."},
            {"role":"user","content":f"Object: {c['meta']['kor']} (category: {c['meta']['category']})"},
            {"role":"assistant","content": json.dumps(c['card'], ensure_ascii=False)}
        ]})
    # scenarios as chat
    for s in scens[:1006]:
        rows.append({"messages":[
            {"role":"system","content":"You are the trilingual KO/RU/EN family AI tutor. Generate JSON dialogs for daily co-learning."},
            {"role":"user","content": f"Scenario: {s['meta']['scenario']}\nAge: {s['meta']['age_band']}\n"},
            {"role":"assistant","content": json.dumps(s['scenario'], ensure_ascii=False)}
        ]})
    # function calls
    rows += fcs

    random.shuffle(rows)
    with OUT.open("w", encoding="utf-8") as fo:
        for r in rows:
            fo.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[v1_recreate] {len(rows)} examples -> {OUT.name}")


if __name__ == "__main__":
    main()
