#!/usr/bin/env python3
"""Synthesize trilingual object-naming cards using Gemma 4 26B (locally) as teacher.

Each row: prompt = object name in any of {ko, ru, en}
          target = JSON card (3 langs + phonetics + L1 contrast + family cards)

For v1 we use a pre-curated object list (1500 items: house, food, body, animals,
nature, transport, school, emotions, actions). Output prototype/data/raw/object_cards.jsonl.

Run mode:
  - DRY_RUN=1: only emit input prompts, no model call (for offline data audit)
  - else: launch local 26B inference with MTP drafter
"""
from __future__ import annotations
import os, json, pathlib, random, time

PROJ = pathlib.Path("/PATH/REDACTED")
RAW = PROJ / "prototype/data/raw"
RAW.mkdir(parents=True, exist_ok=True)
OUT = RAW / "object_cards.jsonl"

# Domain-driven object list (house+food+body+animals+nature+transport+school+emotions+actions+...)
OBJECTS = {
    "집": ["문", "창문", "벽", "천장", "바닥", "방", "거실", "주방", "화장실", "침실",
           "침대", "의자", "책상", "소파", "냉장고", "전자레인지", "TV", "리모컨",
           "이불", "베개", "수건", "비누", "샴푸", "치약", "칫솔", "컵", "그릇",
           "수저", "젓가락", "포크", "냄비", "프라이팬", "도마", "칼", "가위"],
    "음식": ["밥", "국", "김치", "된장찌개", "라면", "빵", "우유", "물", "주스", "차",
             "사과", "바나나", "딸기", "포도", "수박", "참외", "복숭아", "배",
             "당근", "감자", "양파", "마늘", "고추", "파", "오이", "토마토",
             "고기", "닭고기", "돼지고기", "소고기", "생선", "달걀", "치즈"],
    "동물": ["강아지", "고양이", "토끼", "햄스터", "새", "물고기", "곰", "사자",
             "호랑이", "코끼리", "기린", "원숭이", "하마", "악어", "거북이",
             "개구리", "뱀", "나비", "벌", "개미", "거미"],
    "신체": ["눈", "코", "입", "귀", "머리", "얼굴", "손", "발", "팔", "다리",
             "배", "등", "어깨", "무릎", "발가락", "손가락", "이", "혀"],
    "자연": ["해", "달", "별", "구름", "비", "눈", "바람", "나무", "꽃", "잎",
             "산", "바다", "강", "호수", "돌", "모래", "흙", "풀"],
    "교통": ["자동차", "버스", "지하철", "기차", "비행기", "배", "자전거", "오토바이",
             "택시", "트럭", "유모차"],
    "감정": ["기쁘다", "슬프다", "화나다", "무섭다", "좋아하다", "사랑하다", "졸리다",
             "배고프다", "목마르다", "춥다", "덥다"],
    "행동": ["먹다", "마시다", "자다", "일어나다", "걷다", "뛰다", "앉다", "서다",
             "보다", "듣다", "말하다", "웃다", "울다", "씻다", "닦다"],
}


def build_examples():
    """Build prompt list for the synthesis stage."""
    examples = []
    for category, items in OBJECTS.items():
        for kor in items:
            for age_band in ["0-2", "2-4", "4-6", "6-8"]:
                for bridge in ["ru", "en"]:
                    examples.append({
                        "category": category,
                        "kor": kor,
                        "age_band": age_band,
                        "bridge_for_wife": bridge,
                    })
    random.shuffle(examples)
    return examples


SYSTEM_PROMPT = """You are the trilingual (KO/RU/EN) AI tutor for a multicultural family.
The household: father (KO L1) + mother (RU L1, learning KO; husband bridge = EN) + child age %%AGE_BAND%% (KO L1).
Given a Korean object/concept, produce a JSON learning card for the family.

Schema:
{
  "word": {"ko": str, "ru": str, "en": str},
  "phonetic": {
    "ko_in_cyrillic_for_ru": str,   // 한국어 발음을 키릴문자로
    "ru_in_hangul_for_ko": str,     // 러시아어 발음을 한글로
    "ko_in_latin_for_en": str,      // McCune-Reischauer or Revised Romanization
    "ru_in_latin_for_en": str
  },
  "wife_card": {
    "target": "ko",
    "explanation_in": "%%BRIDGE_FOR_WIFE%%",
    "text": str   // 와이프(RU L1)용 한국어 학습 표현, 설명은 bridge 언어로
  },
  "husband_card": {
    "target": "ru",
    "explanation_in": "ko",
    "text": str   // 본인(KO L1)용 러시아어 학습 표현
  },
  "child_card": {
    "ko_simple": str,    // 짧고 발음 명확한 한국어 한 줄
    "ru_simple": str,
    "en_simple": str,
    "audio_focus": [str, str, str]   // 발음 반복용 3종
  },
  "l1_contrast": {
    "ko_vs_ru": str,    // 음운/문법 차이 (russian-language note)
    "ko_vs_en": str,
    "ru_vs_en": str
  },
  "function_call_hints": {
    "next_word": [str, str, str],   // 같은 카테고리 추천 3개
    "common_mistake": str,          // RU L1 학습자가 흔히 틀리는 KO 발음
    "praise_phrase": {"ko": str, "ru": str, "en": str}
  }
}

Output ONLY valid JSON. No explanations outside the JSON."""


def emit_prompts(examples):
    """Emit input prompts (no model call yet — used by next stage)."""
    OUT_PROMPTS = RAW / "object_cards_prompts.jsonl"
    with OUT_PROMPTS.open("w", encoding="utf-8") as fo:
        for ex in examples:
            sys_p = (SYSTEM_PROMPT
                     .replace("%%AGE_BAND%%", ex["age_band"])
                     .replace("%%BRIDGE_FOR_WIFE%%", ex["bridge_for_wife"]))
            user_p = f"Object: {ex['kor']} (category: {ex['category']})"
            fo.write(json.dumps({
                "system": sys_p,
                "user": user_p,
                "meta": ex,
            }, ensure_ascii=False) + "\n")
    print(f"[prompts] {len(examples)} -> {OUT_PROMPTS.name}")


def main():
    examples = build_examples()
    print(f"[plan] total prompts = {len(examples)}")
    emit_prompts(examples)
    if os.environ.get("DRY_RUN"):
        print("[dry-run] skipping model inference")
        return
    print("[next] run 04_run_synth_with_26b.py to fill object_cards.jsonl with model outputs")


if __name__ == "__main__":
    main()
