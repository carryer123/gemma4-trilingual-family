#!/usr/bin/env python3
"""Component-isolation ablation for lora_v1's G2 cliff.

If lora_v1's mix triggers G2 collapse at long training but L_step_dense_p0 mix
does not, the difference is: object_cards (1294) and/or scenarios (1006).
We train three leave-one-out variants:

  V1_no_cards     = lora_v1 mix MINUS object_cards
  V1_no_scenarios = lora_v1 mix MINUS family_scenarios
  V1_no_triples   = lora_v1 mix MINUS English-pivot triples

Each at 5000 steps, save_steps=250, 0% translit. Whichever loses the cliff
isolates the trigger component.
"""
import json, pathlib, random
random.seed(20260506)

PROJ = pathlib.Path("/PATH/REDACTED")
RAW = PROJ / "prototype/data/raw"
ABL = PROJ / "prototype/data/ablation"


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

    # base = Tatoeba 6-direction + function calls (always included, no transliteration)
    base = []
    random.shuffle(p_kor_rus); random.shuffle(p_kor_eng); random.shuffle(p_rus_eng)
    for d in p_kor_rus:
        base += [to_chat_pair("ko","ru",d["kor"],d["rus"]), to_chat_pair("ru","ko",d["rus"],d["kor"])]
    for d in p_kor_eng[:1500]:
        base += [to_chat_pair("ko","en",d["kor"],d["eng"]), to_chat_pair("en","ko",d["eng"],d["kor"])]
    for d in p_rus_eng[:1500]:
        base += [to_chat_pair("ru","en",d["rus"],d["eng"]), to_chat_pair("en","ru",d["eng"],d["rus"])]

    triples_rows = expand_triples(triples, n_max=2000)
    cards_rows = [{"messages":[
        {"role":"system","content":"You are the trilingual KO/RU/EN family AI tutor."},
        {"role":"user","content":f"Object: {c['meta']['kor']} (category: {c['meta']['category']})"},
        {"role":"assistant","content": json.dumps(c['card'], ensure_ascii=False)}
    ]} for c in obj_cards[:1294]]
    scens_rows = [{"messages":[
        {"role":"system","content":"You are the trilingual KO/RU/EN family AI tutor. Generate JSON dialogs for daily co-learning."},
        {"role":"user","content": f"Scenario: {s['meta']['scenario']}\nAge: {s['meta']['age_band']}\n"},
        {"role":"assistant","content": json.dumps(s['scenario'], ensure_ascii=False)}
    ]} for s in scens[:1006]]

    def write_set(name, rows):
        out = ABL / f"{name}_train.jsonl"
        random.shuffle(rows)
        with out.open("w", encoding="utf-8") as fo:
            for r in rows: fo.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"[{name}] {len(rows)} -> {out.name}")

    # leave-one-out
    write_set("V1_no_cards",     base + triples_rows                + scens_rows + fcs)
    write_set("V1_no_scenarios", base + triples_rows + cards_rows                + fcs)
    write_set("V1_no_triples",   base                + cards_rows   + scens_rows + fcs)


if __name__ == "__main__":
    main()
