#!/usr/bin/env python3
"""Build KO/RU/FR/EN training corpora and state-gated mix variants.

This is the fast four-language experiment for the hackathon/paper:

* `train_4l_balanced.jsonl`:
  broad KO/RU/FR/EN translation + family-card + schema + script-state data.
* `train_4l_policy_high.jsonl`:
  same base, with a larger G2/G3 policy slice.
* `train_4l_family_high.jsonl`:
  same base, with more family-card/age-band examples.
* `train_4l_no_policy.jsonl`:
  ablation removing explicit script-state and schema policy examples.

The point is not just "more languages"; it is a state-gated data curriculum:
we intentionally vary policy slices, then select adapters with G2/G3/family
gates instead of loss alone.
"""
from __future__ import annotations

import json
import pathlib
import random
from collections import defaultdict


random.seed(20260509)

PROJ = pathlib.Path("/PATH/REDACTED")
RAW = PROJ / "prototype/data/raw"
DATA = PROJ / "prototype/data"


LANG_NAMES = {"ko": "Korean", "ru": "Russian", "fr": "French", "en": "English"}
PAIR_FILES = {
    ("ko", "ru"): ("tatoeba_kor-rus.jsonl", "kor", "rus"),
    ("ko", "en"): ("tatoeba_kor-eng.jsonl", "kor", "eng"),
    ("ru", "en"): ("tatoeba_rus-eng.jsonl", "rus", "eng"),
    ("ko", "fr"): ("tatoeba_kor-fra.jsonl", "kor", "fra"),
    ("fr", "en"): ("tatoeba_fra-eng.jsonl", "fra", "eng"),
    ("ru", "fr"): ("tatoeba_rus-fra.jsonl", "rus", "fra"),
}

OBJECT_FR = {
    "bus": "bus",
    "bear": "ours",
    "kitchen": "cuisine",
    "cat": "chat",
    "dog": "chien",
    "apple": "pomme",
    "banana": "banane",
    "milk": "lait",
    "water": "eau",
    "book": "livre",
    "cup": "tasse",
    "spoon": "cuillère",
    "ball": "balle",
    "car": "voiture",
    "train": "train",
    "house": "maison",
    "door": "porte",
    "window": "fenêtre",
    "bed": "lit",
    "chair": "chaise",
    "table": "table",
    "shoes": "chaussures",
    "hat": "chapeau",
    "flower": "fleur",
}

FR_PHRASES = [
    ("bonjour", "봉주르", "hello"),
    ("merci", "메르시", "thank you"),
    ("papa", "파파", "dad"),
    ("maman", "마망", "mom"),
    ("pomme", "폼", "apple"),
    ("chat", "샤", "cat"),
    ("chien", "시앵", "dog"),
    ("fromage", "프로마주", "cheese"),
    ("lait", "레", "milk"),
    ("eau", "오", "water"),
    ("livre", "리브르", "book"),
    ("maison", "메종", "house"),
    ("voiture", "부아튀르", "car"),
    ("dodo", "도도", "sleep"),
    ("bisou", "비주", "kiss"),
    ("encore", "앙코르", "again"),
]

KO_ROMAN = [
    ("안녕하세요", "annyeonghaseyo"),
    ("우리 아기", "uri agi"),
    ("사과", "sagwa"),
    ("고양이", "goyangi"),
    ("물 주세요", "mul juseyo"),
    ("책 읽자", "chaek ikja"),
    ("잘했어요", "jalhaesseoyo"),
    ("엄마 아빠", "eomma appa"),
]


def load_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        print(f"[warn] missing {path.name}")
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[write] {len(rows):,} rows -> {path.relative_to(PROJ)}")


def chat(system: str, user: str, assistant: str) -> dict:
    return {"messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant},
    ]}


def trans_pair(src: str, tgt: str, src_text: str, tgt_text: str) -> dict:
    return chat(
        f"Translate {LANG_NAMES[src]} to {LANG_NAMES[tgt]}. Output only the translation.",
        src_text,
        tgt_text,
    )


def add_bidirectional_pairs(rows: list[dict], pair: tuple[str, str], limit: int) -> None:
    file_name, a_key, b_key = PAIR_FILES[pair]
    data = load_jsonl(RAW / file_name)
    random.shuffle(data)
    a, b = pair
    for d in data[:limit]:
        rows.append(trans_pair(a, b, d[a_key], d[b_key]))
        rows.append(trans_pair(b, a, d[b_key], d[a_key]))


def build_by_en(file_name: str, lang_key: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for d in load_jsonl(RAW / file_name):
        en = d.get("eng", "").strip().lower()
        txt = d.get(lang_key, "").strip()
        if en and txt:
            out[en].append(txt)
    return out


def add_pivot_triples(rows: list[dict], limit: int) -> None:
    ko_by_en = build_by_en("tatoeba_kor-eng.jsonl", "kor")
    ru_by_en = build_by_en("tatoeba_rus-eng.jsonl", "rus")
    fr_by_en = build_by_en("tatoeba_fra-eng.jsonl", "fra")
    keys = list(set(ko_by_en) & set(ru_by_en) & set(fr_by_en))
    random.shuffle(keys)
    for en in keys[:limit]:
        sample = {
            "ko": random.choice(ko_by_en[en][:3]),
            "ru": random.choice(ru_by_en[en][:3]),
            "fr": random.choice(fr_by_en[en][:3]),
            "en": en,
        }
        for src in ["ko", "ru", "fr", "en"]:
            for tgt in ["ko", "ru", "fr", "en"]:
                if src != tgt:
                    rows.append(trans_pair(src, tgt, sample[src], sample[tgt]))


def add_family_cards(rows: list[dict], repeat: int = 1) -> None:
    cards = load_jsonl(RAW / "object_cards.jsonl")
    random.shuffle(cards)
    for c in cards[:900]:
        card = c.get("card", {})
        word = card.get("word", {})
        en = str(word.get("en", "")).strip().lower()
        fr = OBJECT_FR.get(en)
        if not fr:
            continue
        word4 = {"ko": word.get("ko", ""), "ru": word.get("ru", ""), "fr": fr, "en": word.get("en", "")}
        assistant = {
            "mode": "family_card",
            "active_languages": ["ko", "ru", "fr", "en"],
            "word": word4,
            "baby_0_2": {
                "prompt": {"ko": f"{word4['ko']}!", "ru": f"{word4['ru']}!", "fr": f"{word4['fr']}!", "en": f"{word4['en']}!"},
                "parent_mission": "Point, say the word once, then let the child touch or look.",
            },
            "child_3_6": {
                "say_it": word4,
                "choice_prompt": f"Can you find {word4['en']}?",
            },
            "parent_bridge": {
                "mother_fr_or_ru": f"In English: this family word is '{word4['en']}'.",
                "father_ko": f"Korean: {word4['ko']}",
            },
        }
        user = f"Build a KO/RU/FR/EN family learning card for object: {word4['en']}"
        for _ in range(repeat):
            rows.append(chat(
                "You are a four-language family tutor for multilingual households. Return valid JSON only.",
                user,
                json.dumps(assistant, ensure_ascii=False),
            ))


def add_script_policy(rows: list[dict], repeat: int = 1) -> None:
    sys = (
        "You are a script-state tutor. When asked for phonetic script transfer, "
        "output only the requested script. Do not translate."
    )
    examples = []
    for ko, latin in KO_ROMAN:
        examples.append((f"Output ONLY Latin romanization of this Korean phrase: {ko}", latin))
    for fr, hangul, _gloss in FR_PHRASES:
        examples.append((f"Output ONLY Hangul phonetic rendering of this French word or phrase: {fr}", hangul))
    for fr, _hangul, _gloss in FR_PHRASES:
        examples.append((f"Output ONLY the French phrase in Latin script, no English translation: {fr}", fr))
    base = load_jsonl(RAW / "transliteration_v2.jsonl") or load_jsonl(RAW / "transliteration.jsonl")
    for _ in range(repeat):
        for user, answer in examples:
            rows.append(chat(sys, user, answer))
        rows.extend(base[:300])


def add_schema_policy(rows: list[dict], repeat: int = 1) -> None:
    modes = [
        ("baby_0_2", ["ko", "ru", "en"], "0-2"),
        ("child_3_6", ["ko", "fr", "en"], "3-6"),
        ("parent_bridge", ["ko", "ru", "fr", "en"], "adult"),
    ]
    for _ in range(repeat):
        for mode, langs, age in modes:
            for i in range(40):
                obj = random.choice(list(OBJECT_FR.items()))
                en, fr = obj
                payload = {
                    "mode": mode,
                    "age_band": age,
                    "active_languages": langs,
                    "card": {
                        "en": en,
                        "fr": fr,
                        "ko": "사물",
                        "ru": "предмет",
                    },
                    "next_action": "speak" if mode == "child_3_6" else "show",
                    "safety": {"child_safe": True, "no_private_data": True},
                }
                rows.append(chat(
                    "Return one valid JSON object with keys mode, age_band, active_languages, card, next_action, safety.",
                    f"Make a {mode} card for a multilingual family. Object: {en}",
                    json.dumps(payload, ensure_ascii=False),
                ))


def split_and_write(name: str, rows: list[dict]) -> None:
    random.shuffle(rows)
    n_eval = max(80, len(rows) // 20)
    write_jsonl(DATA / f"eval_{name}.jsonl", rows[:n_eval])
    write_jsonl(DATA / f"train_{name}.jsonl", rows[n_eval:])


def build_variant(name: str, *, pair_limit: int, quad_limit: int, policy_repeat: int, family_repeat: int) -> None:
    rows: list[dict] = []
    for pair in PAIR_FILES:
        add_bidirectional_pairs(rows, pair, pair_limit)
    add_pivot_triples(rows, quad_limit)
    add_family_cards(rows, repeat=family_repeat)
    if policy_repeat > 0:
        add_script_policy(rows, repeat=policy_repeat)
        add_schema_policy(rows, repeat=policy_repeat)
    split_and_write(name, rows)


def main() -> None:
    build_variant("4l_balanced", pair_limit=1800, quad_limit=800, policy_repeat=1, family_repeat=1)
    build_variant("4l_policy_high", pair_limit=1400, quad_limit=700, policy_repeat=3, family_repeat=1)
    build_variant("4l_family_high", pair_limit=1200, quad_limit=500, policy_repeat=1, family_repeat=3)
    build_variant("4l_no_policy", pair_limit=1800, quad_limit=800, policy_repeat=0, family_repeat=1)


if __name__ == "__main__":
    main()
