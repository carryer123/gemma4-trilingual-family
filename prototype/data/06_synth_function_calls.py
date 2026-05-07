#!/usr/bin/env python3
"""Generate function-call training labels for our app-specific tools.

Tools (matched to docs/아키텍처_결정_20260506.md):
  - score_pronunciation(audio_lang, target_lang, audio_id) -> {score, mistakes[]}
  - recommend_next_word(category, age_band, learned_set) -> {next_words[3], why}
  - explain_in_l1(target_concept, l1, bridge) -> {explanation}
  - switch_age_mode(new_age) -> {ack}
  - flag_unsafe_input(reason) -> {ack}
  - daily_mission(date, age_band) -> {mission, expected_duration_min}

Output: prototype/data/raw/function_calls.jsonl
Format follows transformers chat template + tools list.
"""
from __future__ import annotations
import json, pathlib, random

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
RAW = PROJ / "prototype/data/raw"
OUT = RAW / "function_calls.jsonl"

TOOLS = [
    {
        "name": "score_pronunciation",
        "description": "Score the user's pronunciation of a target word. Returns a 0-100 score and per-phoneme issues.",
        "parameters": {
            "type": "object",
            "properties": {
                "audio_lang": {"type": "string", "enum": ["ko", "ru", "en"]},
                "target_lang": {"type": "string", "enum": ["ko", "ru", "en"]},
                "target_text": {"type": "string"},
                "audio_id": {"type": "string"}
            },
            "required": ["audio_lang", "target_lang", "target_text", "audio_id"]
        }
    },
    {
        "name": "recommend_next_word",
        "description": "Given the learner's category, age, and already-learned set, propose 3 next-word candidates.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "age_band": {"type": "string", "enum": ["0-2", "2-4", "4-6", "6-8"]},
                "learned_set": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["category", "age_band"]
        }
    },
    {
        "name": "explain_in_l1",
        "description": "Explain a Korean grammar/phonology concept in the wife's bridge language (RU or EN).",
        "parameters": {
            "type": "object",
            "properties": {
                "target_concept": {"type": "string"},
                "l1": {"type": "string", "enum": ["ru", "en"]},
                "bridge": {"type": "string", "enum": ["ru", "en"]},
                "target_lang": {"type": "string", "enum": ["ko", "ru", "en"]}
            },
            "required": ["target_concept", "l1", "target_lang"]
        }
    },
    {
        "name": "switch_age_mode",
        "description": "Switch the UI's age-band mode for the child user.",
        "parameters": {
            "type": "object",
            "properties": {
                "new_age": {"type": "string", "enum": ["0-2", "2-4", "4-6", "6-8"]}
            },
            "required": ["new_age"]
        }
    },
    {
        "name": "flag_unsafe_input",
        "description": "Flag any user input/content as unsafe (child-inappropriate, harmful, etc.).",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {"type": "string"},
                "severity": {"type": "string", "enum": ["low", "medium", "high"]}
            },
            "required": ["reason"]
        }
    },
    {
        "name": "daily_mission",
        "description": "Suggest today's family co-learning mission.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string"},
                "age_band": {"type": "string"},
                "household_langs": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["date", "age_band"]
        }
    }
]


# Hand-curated seed prompts → expected function calls
SEEDS = [
    ("아내가 '안녕하세요' 발음한 거 점수 좀 매겨줘. audio_id=sess_001",
     "score_pronunciation",
     {"audio_lang": "ko", "target_lang": "ko", "target_text": "안녕하세요", "audio_id": "sess_001"}),

    ("우리 아기 동물 단어 5개 배웠어 — 강아지 고양이 토끼 곰 새. 다음 추천해줘. 1살 9개월.",
     "recommend_next_word",
     {"category": "동물", "age_band": "0-2", "learned_set": ["강아지", "고양이", "토끼", "곰", "새"]}),

    ("Korean particle '에' vs '에서' 의 차이를 영어로 설명해줘. 와이프가 영어 brigde 야.",
     "explain_in_l1",
     {"target_concept": "particle 에 vs 에서", "l1": "ru", "bridge": "en", "target_lang": "ko"}),

    ("아기가 좀 더 컸어, 이제 4살. 모드 바꿔줘.",
     "switch_age_mode",
     {"new_age": "4-6"}),

    ("이 단어 어린이 앱에 부적절해 보이는데 체크 좀.",
     "flag_unsafe_input",
     {"reason": "potentially inappropriate vocabulary for under-8 audience", "severity": "medium"}),

    ("오늘의 가족 미션 추천해줘. 날짜 2026-05-08, 아기 1세 9개월, 우리집 한국어/러시아어/영어.",
     "daily_mission",
     {"date": "2026-05-08", "age_band": "0-2", "household_langs": ["ko", "ru", "en"]}),
]


def make_chat(user, tool_name, tool_args):
    """One training example with proper tool-calling chat structure."""
    return {
        "messages": [
            {"role": "system", "content": (
                "You are a trilingual KO/RU/EN family-learning assistant. "
                "When the user request maps to a tool, respond with a tool call. "
                "Otherwise respond in the user's language."
            )},
            {"role": "user", "content": user},
            {"role": "assistant", "tool_calls": [
                {"type": "function", "function": {"name": tool_name, "arguments": json.dumps(tool_args, ensure_ascii=False)}}
            ]}
        ],
        "tools": TOOLS
    }


def expand_seeds(seeds, target_n=500):
    """Expand seeds via paraphrase variants (manual for v1)."""
    bag = []
    for user, name, args in seeds:
        for _ in range(target_n // len(seeds)):
            bag.append(make_chat(user, name, args))
    random.shuffle(bag)
    return bag


def main():
    rows = expand_seeds(SEEDS, target_n=500)
    with OUT.open("w", encoding="utf-8") as fo:
        for r in rows:
            fo.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[function_calls] {len(rows)} -> {OUT.name}")
    print("[note] v1 uses fixed paraphrases; v2 should use 26B paraphrase generation")


if __name__ == "__main__":
    main()
