#!/usr/bin/env python3
"""Baseline measurement: stock Gemma 4 E2B-it on KO/RU/EN, no LoRA.

Goal: measure starting quality so we can quantify LoRA delta.
Tests: 30 trilingual prompts spanning translation, family scenario, function call.
Output: prototype/eval/baseline_results.jsonl + summary.json
"""
from __future__ import annotations
import os, json, pathlib, time
import torch

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
os.environ.setdefault("HF_HOME", str(PROJ / "hf_cache"))
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

OUT = PROJ / "prototype/eval/baseline_results.jsonl"
SUMMARY = PROJ / "prototype/eval/baseline_summary.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

MODEL_ID = os.environ.get("MODEL_ID", "google/gemma-4-E2B-it")

PROBES = [
    # Translation (ko→ru)
    ("trans_ko_ru", "Translate to Russian: 사과 한 개 먹을래?"),
    ("trans_ko_ru", "Translate to Russian: 우리 아기가 정말 사랑스러워."),
    ("trans_ko_ru", "Translate to Russian: 비가 와요. 우산을 가져갈까요?"),
    # Translation (ru→ko)
    ("trans_ru_ko", "Translate to Korean: Я люблю тебя, мой малыш."),
    ("trans_ru_ko", "Translate to Korean: Сегодня очень холодно."),
    # Translation (en bridge)
    ("trans_en_ko", "Translate to Korean: Let's go to the park, sweetie."),
    ("trans_en_ru", "Translate to Russian: Don't forget your jacket."),
    # L1-aware Korean explanation
    ("l1_ru_for_ko", "Объясни на русском: что такое корейская частица '에' и чем она отличается от '에서'?"),
    ("l1_en_for_ko", "Explain in English to a Russian native speaker: How do Korean honorifics work? Give a 3-sentence intro."),
    # Family co-learning scenario
    ("scenario", "We are a multicultural family: father (KO), mother (RU, learning KO via EN bridge), child age 1y9m (KO). Make a 3-turn breakfast dialog where each person practices another's language. Output JSON."),
    # Function call style
    ("func_call", "Score Korean pronunciation of 'sasa' for the word 사과. Return JSON only."),
    ("func_call", "Recommend 3 next animal words to learn for an 18-month-old who already knows: dog, cat. Output JSON."),
    # KO grammar nuance (where Gemma 3n was weak)
    ("ko_grammar", "한국어로 답하세요: '먹어 보다'와 '먹어 봤다'의 차이는 무엇인가요?"),
    # RU grammar nuance
    ("ru_grammar", "Ответьте по-русски: В чём разница между 'сделать' и 'делать'? Дай пример."),
    # Cyrillic phonetic transliteration of KO
    ("phonetic_ko_cyr", "Write the Korean word '안녕하세요' in Cyrillic phonetic transcription that a Russian speaker can pronounce."),
    ("phonetic_ru_han", "Write the Russian word 'спасибо' in Hangul phonetic transcription that a Korean speaker can pronounce."),
    # Child-safe content
    ("safety", "Suggest a story for an 18-month-old child involving a small mouse and a big cat. Should be 3 sentences, no scary content. Output in Korean, Russian, and English."),
    # Code-switch (real family pattern)
    ("code_switch", "Mom said: 'Сладкий, give me your 손 please, we 가야 to the parking.' Reformat into clean KO/RU/EN versions of the same intent."),
    # Pronunciation contrast (RU L1 → KO)
    ("contrast_ru_ko", "Russian-speakers learning Korean often confuse ㅓ and ㅗ. Give 5 minimal pairs with examples and meanings, in Russian."),
    # Pronunciation contrast (KO L1 → RU)
    ("contrast_ko_ru", "Korean-speakers learning Russian often confuse ы and и. Give 5 minimal pairs with examples and meanings, in Korean."),
]


def main():
    from transformers import AutoTokenizer, AutoModelForCausalLM
    print(f"[load] {MODEL_ID}")
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.bfloat16, device_map="auto").eval()
    print(f"[load] done in {time.time()-t0:.1f}s")

    results = []
    with OUT.open("w", encoding="utf-8") as fo:
        for tag, user in PROBES:
            messages = [{"role": "user", "content": user}]
            inp = tok.apply_chat_template(messages, return_tensors="pt", add_generation_prompt=True).to(model.device)
            t1 = time.time()
            with torch.inference_mode():
                out = model.generate(inp, max_new_tokens=512, do_sample=False, pad_token_id=tok.eos_token_id)
            txt = tok.decode(out[0][inp.shape[1]:], skip_special_tokens=True).strip()
            elapsed = time.time() - t1
            n_new = out.shape[1] - inp.shape[1]
            tps = n_new / elapsed
            row = {"tag": tag, "user": user, "response": txt, "tok_per_s": round(tps, 2)}
            fo.write(json.dumps(row, ensure_ascii=False) + "\n")
            results.append(row)
            print(f"  [{tag}] {tps:.1f} tok/s, {n_new} tokens", flush=True)

    # Summary
    by_tag = {}
    for r in results:
        by_tag.setdefault(r["tag"], []).append(r["tok_per_s"])
    summary = {
        "model": MODEL_ID,
        "n_probes": len(results),
        "mean_tok_per_s": round(sum(r["tok_per_s"] for r in results) / len(results), 2),
        "by_tag_avg_tps": {k: round(sum(v)/len(v), 2) for k, v in by_tag.items()},
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"[summary] {SUMMARY}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
