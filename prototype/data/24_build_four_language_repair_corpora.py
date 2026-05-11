#!/usr/bin/env python3
"""Build second-wave 4L repair curricula after the first audit.

First-wave result: G2 is mostly strong and G3 improves for balanced/family, but
G1 family structure is weak and G4 session routing is 0/24 across variants.
This script adds explicit G1/G4 repair slices while keeping held-out audit
objects disjoint from training examples.
"""
from __future__ import annotations

import json
import pathlib
import random


random.seed(20260509)

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
DATA = PROJ / "prototype/data"

TRAIN_OBJECTS = [
    ("apple", "사과", "яблоко", "pomme"),
    ("cat", "고양이", "кошка", "chat"),
    ("dog", "강아지", "собака", "chien"),
    ("milk", "우유", "молоко", "lait"),
    ("water", "물", "вода", "eau"),
    ("book", "책", "книга", "livre"),
    ("cup", "컵", "чашка", "tasse"),
    ("ball", "공", "мяч", "balle"),
    ("car", "자동차", "машина", "voiture"),
    ("house", "집", "дом", "maison"),
    ("spoon", "숟가락", "ложка", "cuillère"),
    ("bed", "침대", "кровать", "lit"),
]


def load_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[write] {len(rows):,} -> {path.relative_to(PROJ)}")


def chat(system: str, user: str, assistant: dict) -> dict:
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": json.dumps(assistant, ensure_ascii=False)},
        ]
    }


def card_for(active: list[str], en: str, ko: str, ru: str, fr: str) -> dict:
    values = {"ko": ko, "ru": ru, "fr": fr, "en": en}
    return {lang: values[lang] for lang in active}


def add_g1_repair(rows: list[dict], repeat: int) -> None:
    sys = (
        "You are a four-language family tutor. Return exactly one valid JSON "
        "object with keys mode, age_band, active_languages, card, next_action, safety."
    )
    for _ in range(repeat):
        for en, ko, ru, fr in TRAIN_OBJECTS:
            baby = {
                "mode": "baby_0_2",
                "age_band": "0-2",
                "active_languages": ["ko", "ru", "en"],
                "card": card_for(["ko", "ru", "en"], en, ko, ru, fr),
                "next_action": "Parent points to the object, says each word once, then lets the baby touch or look.",
                "safety": {"child_safe": True, "no_private_data": True},
            }
            rows.append(chat(
                sys,
                f"Return JSON only. Mode: baby_0_2. Active languages: ko, ru, en. Object: {en}. Build a parent-led card for a pre-verbal baby.",
                baby,
            ))
            child = {
                "mode": "child_3_6",
                "age_band": "3-6",
                "active_languages": ["ko", "fr", "en"],
                "card": card_for(["ko", "fr", "en"], en, ko, ru, fr),
                "next_action": "Ask the child to say the word, point to the object, then choose it in the room.",
                "safety": {"child_safe": True, "no_private_data": True},
            }
            rows.append(chat(
                sys,
                f"Return JSON only. Mode: child_3_6. Active languages: ko, fr, en. Object: {en} / French: {fr}. Build a speaking prompt for a 4-year-old child.",
                child,
            ))


def add_g4_repair(rows: list[dict], repeat: int) -> None:
    sys = (
        "You are a session-routing adapter. The app supports ko/ru/fr/en, but "
        "each family session activates at most three languages. Return JSON only "
        "and never include inactive languages."
    )
    sessions = [
        ("ko, ru, en", ["ko", "ru", "en"], "fr"),
        ("ko, fr, en", ["ko", "fr", "en"], "ru"),
    ]
    for _ in range(repeat):
        for active_text, active, forbidden in sessions:
            for en, ko, ru, fr in TRAIN_OBJECTS:
                payload = {
                    "mode": "parent_bridge",
                    "age_band": "adult",
                    "active_languages": active,
                    "card": card_for(active, en, ko, ru, fr),
                    "next_action": f"Use only {active_text} for this family session. Do not include {forbidden}.",
                    "safety": {"child_safe": True, "no_private_data": True},
                }
                rows.append(chat(
                    sys,
                    f"Return JSON only. The app supports ko/ru/fr/en, but this session activates only {active_text}. Do not include {forbidden}. Object: {en}.",
                    payload,
                ))


def build(name: str, base_name: str, *, g1_repeat: int, g4_repeat: int) -> None:
    rows = load_jsonl(DATA / f"train_{base_name}.jsonl")
    add_g1_repair(rows, g1_repeat)
    add_g4_repair(rows, g4_repeat)
    random.shuffle(rows)
    write_jsonl(DATA / f"train_{name}.jsonl", rows)
    # Use the same eval file path convention for the trainer, though eval is
    # disabled in same-day sweeps.
    write_jsonl(DATA / f"eval_{name}.jsonl", load_jsonl(DATA / f"eval_{base_name}.jsonl"))


def main() -> None:
    build("4l_balanced_repair", "4l_balanced", g1_repeat=8, g4_repeat=12)
    build("4l_family_repair", "4l_family_high", g1_repeat=12, g4_repeat=12)
    build("4l_policy_repair", "4l_policy_high", g1_repeat=8, g4_repeat=16)
    build("4l_no_policy_repair", "4l_no_policy", g1_repeat=8, g4_repeat=12)


if __name__ == "__main__":
    main()
