#!/usr/bin/env python3
"""Generate family co-learning dialog scenarios — trilingual KO+RU+EN.

Each scenario = one daily-life situation (식탁, 산책, 병원, 마트, 공원 ...) ×
                연령 (0-2/2-4/4-6/6-8) × 부모 KO 수준 (초/중/고) × 브릿지 (RU/EN).

Output: prototype/data/raw/family_scenarios_prompts.jsonl  (model-fillable)
"""
from __future__ import annotations
import json, pathlib, random

PROJ = pathlib.Path("/PATH/REDACTED")
RAW = PROJ / "prototype/data/raw"
RAW.mkdir(parents=True, exist_ok=True)
OUT = RAW / "family_scenarios_prompts.jsonl"

SCENARIOS = [
    "식탁 아침 식사", "식탁 저녁 식사", "식탁 간식 시간",
    "거실 책 읽기", "거실 블록놀이", "거실 그림 그리기",
    "공원 산책", "공원 미끄럼틀", "공원 그네",
    "마트 장보기 야채 코너", "마트 장보기 빵 코너", "마트 계산대",
    "버스 타기", "지하철 타기", "택시 타기",
    "병원 소아과 대기실", "병원 진료실", "약국",
    "유치원 등원", "유치원 하원", "유치원 친구 인사",
    "도서관 그림책 고르기", "도서관 조용히 하기",
    "잠자리 양치질", "잠자리 책 읽어주기", "잠자리 자장가",
    "목욕 시간 비누칠", "목욕 시간 머리감기",
    "옷 갈아입히기 추운 날", "옷 갈아입히기 더운 날",
    "전화 통화 할머니와", "전화 통화 외할머니와",
    "생일 파티 케이크", "명절 한복 입기", "명절 차례 인사",
    "비 오는 날 우산", "눈 오는 날 눈사람", "더운 날 아이스크림",
    "동물원 사자 보기", "동물원 코끼리 먹이주기",
    "놀이터 친구 사귀기", "놀이터 차례 양보하기",
    "감기 걸렸을 때 약 먹기", "다쳤을 때 반창고",
    "기분 안 좋을 때 위로", "기쁠 때 칭찬", "혼날 때 사과",
    "심부름 가게 다녀오기", "함께 청소하기",
]

SYSTEM_PROMPT = """You are the trilingual (KO/RU/EN) family AI tutor.
Household: 아버지 (KO L1) + 어머니 (RU L1, learning KO; speaks EN with husband) + child age %%AGE_BAND%% (KO L1).

Generate a realistic daily-life scenario dialog that makes ALL THREE family members
practice their target language at the same time. Include:
- A short narrative setup (what's happening)
- 5-8 turns of conversation, each turn labeled with speaker (father/mother/child)
- For each turn, give: original utterance + recommended translation prompts for OTHER family members
- A "co-learning moment" that exploits the situation
- A "what each person learned" summary

OUTPUT FORMAT (strict JSON):
{
  "scenario": str,
  "age_band": "0-2|2-4|4-6|6-8",
  "parent_ko_level": "초|중|고",
  "wife_bridge": "ru|en",
  "narrative": str,
  "dialog": [
    {
      "speaker": "father|mother|child",
      "utterance": {"primary_lang": "ko|ru|en", "text": str},
      "learning_for_others": {
        "father_target_ru": str,    // father practices Russian via this turn
        "mother_target_ko": str,    // mother practices Korean
        "child_targets": {"ko": str, "ru": str, "en": str}
      }
    }
  ],
  "co_learning_moment": str,   // 가족이 동시에 배운 한 순간
  "learned_summary": {
    "father_learned_ru": [str, ...],
    "mother_learned_ko": [str, ...],
    "child_learned": {"ko": [str], "ru": [str], "en": [str]}
  }
}

Output ONLY JSON. No prose."""


def emit():
    examples = []
    for s in SCENARIOS:
        for age in ["0-2", "2-4", "4-6", "6-8"]:
            for level in ["초", "중", "고"]:
                for bridge in ["ru", "en"]:
                    examples.append({
                        "scenario": s,
                        "age_band": age,
                        "parent_ko_level": level,
                        "wife_bridge": bridge,
                    })
    random.shuffle(examples)
    examples = examples[:1500]   # ~1.5K target
    with OUT.open("w", encoding="utf-8") as fo:
        for ex in examples:
            sys_p = SYSTEM_PROMPT.replace("%%AGE_BAND%%", ex["age_band"])
            user_p = (
                f"Scenario: {ex['scenario']}\n"
                f"Age: {ex['age_band']}\n"
                f"Mother's Korean level: {ex['parent_ko_level']}\n"
                f"Mother's bridge language: {ex['wife_bridge']}\n"
                "Generate the JSON dialog now."
            )
            fo.write(json.dumps({"system": sys_p, "user": user_p, "meta": ex}, ensure_ascii=False) + "\n")
    print(f"[prompts] {len(examples)} -> {OUT.name}")


if __name__ == "__main__":
    emit()
