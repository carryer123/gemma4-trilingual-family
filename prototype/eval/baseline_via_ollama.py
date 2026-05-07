#!/usr/bin/env python3
"""Baseline trilingual probe via Ollama API (no HF gate, no token).

Calls http://127.0.0.1:11434/api/generate with model=gemma4:e2b on the same
20 trilingual probes as baseline_e2b_trilingual.py.

Output: prototype/eval/baseline_ollama_results.jsonl + summary.json
"""
from __future__ import annotations
import os, json, pathlib, time, urllib.request

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
OUT = PROJ / "prototype/eval/baseline_ollama_results.jsonl"
SUMMARY = PROJ / "prototype/eval/baseline_ollama_summary.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

MODEL = os.environ.get("OLLAMA_MODEL", "gemma4:e2b")
HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

PROBES = [
    ("trans_ko_ru", "Translate to Russian only (no extra text): 사과 한 개 먹을래?"),
    ("trans_ko_ru", "Translate to Russian only: 우리 아기가 정말 사랑스러워."),
    ("trans_ko_ru", "Translate to Russian only: 비가 와요. 우산을 가져갈까요?"),
    ("trans_ru_ko", "Translate to Korean only: Я люблю тебя, мой малыш."),
    ("trans_ru_ko", "Translate to Korean only: Сегодня очень холодно."),
    ("trans_en_ko", "Translate to Korean only: Let's go to the park, sweetie."),
    ("trans_en_ru", "Translate to Russian only: Don't forget your jacket."),
    ("l1_ru_for_ko", "Объясни на русском кратко: что такое корейская частица '에' и чем она отличается от '에서'?"),
    ("l1_en_for_ko", "Explain in English to a Russian native speaker (3 short sentences): How do Korean honorifics work?"),
    ("scenario", "We are a multicultural family: father (KO L1), mother (RU L1, learning KO via EN bridge), child age 1y9m (KO L1). Give a 3-turn breakfast dialog where each person practices another's language. Output strict JSON with keys: turns[], each turn has speaker and text fields."),
    ("func_call", "Output JSON only: score the Korean pronunciation of '안녕' for the word '안녕하세요'. Schema: {\"score\": int 0-100, \"mistakes\": [str]}."),
    ("func_call", "Output JSON only: recommend 3 next animal words for an 18-month-old who knows: dog, cat. Schema: {\"next\":[str,str,str], \"why\": str}."),
    ("ko_grammar", "한국어로 답하세요(2문장): '먹어 보다'와 '먹어 봤다'의 차이는 무엇인가요?"),
    ("ru_grammar", "Ответьте по-русски (2 предложения): В чём разница между 'сделать' и 'делать'? Дай пример."),
    ("phonetic_ko_cyr", "Write the Korean word '안녕하세요' in Cyrillic phonetic transcription a Russian speaker can pronounce. Output ONLY the cyrillic transcription, nothing else."),
    ("phonetic_ru_han", "Write the Russian word 'спасибо' in Hangul phonetic transcription a Korean speaker can pronounce. Output ONLY hangul, nothing else."),
    ("safety", "Suggest a 3-sentence safe story for an 18-month-old child involving a small mouse and a big cat. No scary content. Output in Korean only."),
    ("code_switch", "Mom said: 'Сладкий, give me your 손 please, we 가야 to the park.' Reformat into clean KO/RU/EN versions of the same intent. Output JSON: {\"ko\": str, \"ru\": str, \"en\": str}."),
    ("contrast_ru_ko", "Russian-speakers learning Korean often confuse ㅓ and ㅗ. Give 5 minimal pairs with Korean and English meaning. Output JSON: {\"pairs\":[{\"a\":\"\",\"b\":\"\",\"meaning\":\"\"}]}."),
    ("contrast_ko_ru", "Korean-speakers learning Russian often confuse ы and и. Give 5 minimal pairs with Russian and Korean meaning. Output JSON: {\"pairs\":[{\"a\":\"\",\"b\":\"\",\"meaning\":\"\"}]}."),
]


def call_ollama(prompt: str) -> tuple[str, float, dict]:
    body = {"model": MODEL, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.3, "num_predict": 512}}
    req = urllib.request.Request(
        f"{HOST}/api/generate",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as resp:
        out = json.loads(resp.read())
    dt = time.time() - t0
    return out.get("response", ""), dt, out


def main():
    print(f"[probe] {MODEL} on {HOST}, n={len(PROBES)}")
    results = []
    with OUT.open("w", encoding="utf-8") as fo:
        for tag, prompt in PROBES:
            try:
                txt, dt, raw = call_ollama(prompt)
                eval_count = raw.get("eval_count", 0)
                tps = eval_count / max(dt, 0.001)
                row = {"tag": tag, "prompt": prompt, "response": txt.strip(),
                       "elapsed_s": round(dt, 2), "tok": eval_count, "tps": round(tps, 2)}
            except Exception as e:
                row = {"tag": tag, "prompt": prompt, "error": str(e)}
            fo.write(json.dumps(row, ensure_ascii=False) + "\n")
            results.append(row)
            print(f"  [{tag}] {row.get('tps','-')} tok/s | {row.get('response','ERROR')[:80]}")

    by_tag = {}
    for r in results:
        if "tps" in r:
            by_tag.setdefault(r["tag"], []).append(r["tps"])
    summary = {
        "model": MODEL,
        "n": len(results),
        "n_ok": sum(1 for r in results if "tps" in r),
        "mean_tps": round(sum(r.get("tps", 0) for r in results) / max(1, sum(1 for r in results if "tps" in r)), 2),
        "by_tag_avg": {k: round(sum(v)/len(v), 2) for k, v in by_tag.items()},
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\n[summary]")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
