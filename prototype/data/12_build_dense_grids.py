#!/usr/bin/env python3
"""Build dense ablation sets:
  Track A — single 0% policy data, train 5000 steps, save every 250
  Track B — finer policy fraction grid {0, 0.5, 1, 2, 3, 5, 8, 10}%
"""
import json, pathlib, random
random.seed(20260507)

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
RAW = PROJ / "prototype/data/raw"
ABL = PROJ / "prototype/data/ablation"
ABL.mkdir(parents=True, exist_ok=True)


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


def write_set(name, rows):
    out = ABL / f"{name}_train.jsonl"
    random.shuffle(rows)
    with out.open("w", encoding="utf-8") as fo:
        for r in rows:
            fo.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[{name}] {len(rows)} -> {out.name}")


def main():
    # Loads
    p_kor_rus = jsonl(RAW / "tatoeba_kor-rus.jsonl")
    p_kor_eng = jsonl(RAW / "tatoeba_kor-eng.jsonl")
    p_rus_eng = jsonl(RAW / "tatoeba_rus-eng.jsonl")
    triples = jsonl(RAW / "trilingual_ko_ru_en.jsonl")
    translit_full = jsonl(RAW / "transliteration_v2.jsonl")  # 1765
    fcs = jsonl(RAW / "function_calls.jsonl")

    # base = same Tatoeba + triples mix as L_policy_*; deterministic
    random.shuffle(p_kor_rus); random.shuffle(p_kor_eng); random.shuffle(p_rus_eng)
    base = []
    for d in p_kor_rus:
        base += [to_chat_pair("ko","ru",d["kor"],d["rus"]), to_chat_pair("ru","ko",d["rus"],d["kor"])]
    for d in p_kor_eng[:1500]:
        base += [to_chat_pair("ko","en",d["kor"],d["eng"]), to_chat_pair("en","ko",d["eng"],d["kor"])]
    for d in p_rus_eng[:1500]:
        base += [to_chat_pair("ru","en",d["rus"],d["eng"]), to_chat_pair("en","ru",d["eng"],d["rus"])]
    base += expand_triples(triples, n_max=1500)
    base_count = len(base)
    print(f"[base] {base_count} examples")

    # Track A: dense step grid input — same data as L_policy_00 (0% translit)
    # We train ONE LoRA with save_steps=250 to extract step-axis curve.
    track_a = list(base) + fcs
    write_set("L_step_dense_p0", track_a)

    # Also a 1.5% variant for a parallel step curve (with translit data to compare)
    n_translit_15 = int(base_count * 0.015)
    track_a_15 = list(base) + translit_full[:n_translit_15] + fcs
    write_set("L_step_dense_p1_5", track_a_15)

    # Track B: finer policy fraction grid
    # transliteration_v2.jsonl has 1765 examples = up to ~9% on a base of ~16K
    pct_grid = [0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 10.0]
    for pct in pct_grid:
        n_translit = min(int(base_count * pct / 100), len(translit_full))
        rows = list(base) + translit_full[:n_translit] + fcs
        actual_pct = 100 * n_translit / max(1, base_count)
        name = f"L_pf_{pct:04.1f}".replace(".", "p")
        write_set(name, rows)
        print(f"  -> requested {pct}%, actual {actual_pct:.2f}% ({n_translit} translit / {base_count} base)")


if __name__ == "__main__":
    main()
