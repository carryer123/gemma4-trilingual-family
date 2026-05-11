#!/usr/bin/env python3
"""Generate the v4 four-language audit probe set.

The probe set is intentionally operational, not a broad benchmark:

* G1 family-card behavior for Baby 0-2 and Child 3-6 modes.
* G2 script-state compliance for KO/RU/FR/EN family use.
* G3 JSON/schema discipline for app cards.
* G4 session-routing constraint: the app supports four demo languages, but a
  family session activates at most three.
"""
from __future__ import annotations

import json
import pathlib


PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
OUT = PROJ / "tools/fae_protocol/probes_v4_4l_audit.jsonl"

# Audit objects are intentionally disjoint from the training family-card object
# list in `21_build_four_language_corpus.py`. This keeps G1/G3/G4 from being a
# template memorization check.
OBJECTS = [
    ("umbrella", "우산", "зонт", "parapluie"),
    ("toothbrush", "칫솔", "зубная щётка", "brosse à dents"),
    ("blanket", "담요", "одеяло", "couverture"),
    ("rabbit", "토끼", "кролик", "lapin"),
    ("orange", "오렌지", "апельсин", "orange"),
    ("pencil", "연필", "карандаш", "crayon"),
    ("socks", "양말", "носки", "chaussettes"),
    ("soap", "비누", "мыло", "savon"),
    ("plate", "접시", "тарелка", "assiette"),
    ("towel", "수건", "полотенце", "serviette"),
    ("banana", "바나나", "банан", "banane"),
    ("hat", "모자", "шапка", "chapeau"),
]

G2 = {
    "ko_to_lat": [
        ("안녕하세요", "latin", ["annyeong", "annyong"]),
        ("우리 아기", "latin", ["uri", "agi"]),
        ("사과", "latin", ["sagwa", "sa gwa"]),
        ("고양이", "latin", ["goyang", "koyang"]),
        ("물 주세요", "latin", ["mul", "juse"]),
        ("책 읽자", "latin", ["chaek", "jaek", "ikja"]),
        ("잘했어요", "latin", ["jal", "haess", "haet"]),
        ("엄마 아빠", "latin", ["eomma", "umma", "appa"]),
    ],
    "ko_to_cyr": [
        ("안녕하세요", "cyrillic", []), ("우리 아기", "cyrillic", []), ("김치찌개", "cyrillic", []), ("학교 갈래?", "cyrillic", []),
        ("서울특별시", "cyrillic", []), ("엄마 아빠", "cyrillic", []), ("잘 자요", "cyrillic", []), ("사랑해", "cyrillic", []),
    ],
    "ru_to_han": [
        ("спасибо", "hangul", ["스파", "스빠"]),
        ("молоко", "hangul", ["몰로", "말라", "밀로"]),
        ("кошка", "hangul", ["코시", "코슈", "카시"]),
        ("медведь", "hangul", ["메드", "메드베", "메드볘"]),
        ("доброе утро", "hangul", ["도브", "우트", "우뜨"]),
        ("мама", "hangul", ["마마"]),
        ("папа", "hangul", ["파파", "빠빠"]),
        ("давай кушать", "hangul", ["다바", "쿠샤", "쿠샤트"]),
    ],
    "fr_to_han": [
        ("bonjour", "hangul", ["봉", "본주", "봉주"]),
        ("merci", "hangul", ["메르", "메시"]),
        ("maman", "hangul", ["마망", "마만"]),
        ("papa", "hangul", ["파파", "빠빠"]),
        ("pomme", "hangul", ["폼", "뽐"]),
        ("chat", "hangul", ["샤", "차"]),
        ("chien", "hangul", ["시앵", "시엔", "샹"]),
        ("fromage", "hangul", ["프로", "프로마", "프호"]),
    ],
    "fr_to_lat": [
        ("bonjour", "latin", ["bonjour"]),
        ("merci", "latin", ["merci"]),
        ("je veux de l'eau", "latin", ["veux", "eau"]),
        ("encore une fois", "latin", ["encore", "fois"]),
        ("bonne nuit", "latin", ["bonne", "nuit"]),
        ("où est le livre?", "latin", ["livre"]),
        ("c'est une pomme", "latin", ["pomme"]),
        ("très bien", "latin", ["très", "tres", "bien"]),
    ],
}


def emit(rows: list[dict], row: dict) -> None:
    rows.append(row)


def schema_probe(pid: str, group: str, prompt: str, mode: str, active: list[str], age: str) -> dict:
    return {
        "id": pid,
        "gate": "G3",
        "group": group,
        "prompt": prompt,
        "required_keys": ["mode", "age_band", "active_languages", "card", "next_action", "safety"],
        "types": {
            "mode": "str",
            "age_band": "str",
            "active_languages": "list",
            "card": "dict",
            "next_action": "str",
            "safety": "dict",
        },
        "enums": {"mode": ["baby_0_2", "child_3_6", "parent_bridge"]},
        "no_extra_keys": True,
        "expect_mode": mode,
        "expect_active_languages": active,
        "expect_age_band": age,
    }


def main() -> None:
    rows: list[dict] = []

    # G1: family-card behavior. Same schema as G3, but scored as family task.
    n = 0
    for en, ko, ru, _fr in OBJECTS:
        n += 1
        emit(rows, schema_probe(
            f"g1_baby_a_{n:02d}", "family_baby_ko_ru_en",
            f"Return JSON only. Mode: baby_0_2. Active languages: ko, ru, en. "
            f"Object: {en}. Build a parent-led card for a pre-verbal baby.",
            "baby_0_2", ["ko", "ru", "en"], "0-2") | {"gate": "G1"})
    n = 0
    for en, _ko, _ru, fr in OBJECTS:
        n += 1
        emit(rows, schema_probe(
            f"g1_child_b_{n:02d}", "family_child_ko_fr_en",
            f"Return JSON only. Mode: child_3_6. Active languages: ko, fr, en. "
            f"Object: {en} / French: {fr}. Build a speaking prompt for a 4-year-old child.",
            "child_3_6", ["ko", "fr", "en"], "3-6") | {"gate": "G1"})

    # G2: script-state compliance.
    for direction, items in G2.items():
        for i, (text, script, sanity) in enumerate(items, 1):
            if direction == "ko_to_lat":
                prompt = f"Output ONLY Latin romanization of this Korean phrase. No translation, no commentary: {text}"
            elif direction == "ko_to_cyr":
                prompt = f"Output ONLY Cyrillic phonetic rendering of this Korean phrase. No translation, no commentary: {text}"
            elif direction == "ru_to_han":
                prompt = f"Output ONLY Hangul phonetic rendering of this Russian word or phrase. No translation, no commentary: {text}"
            elif direction == "fr_to_han":
                prompt = f"Output ONLY Hangul phonetic rendering of this French word or phrase. No translation, no commentary: {text}"
            else:
                prompt = f"Output ONLY the French text in Latin script. Do not translate to English: {text}"
            emit(rows, {
                "id": f"g2_{direction}_{i:02d}",
                "gate": "G2",
                "group": direction,
                "direction": direction,
                "prompt": prompt,
                "expect_script": script,
                "expect_any_substring": sanity,
            })

    # G3: app schema discipline.
    for i, (en, _ko, _ru, _fr) in enumerate(OBJECTS, 1):
        emit(rows, schema_probe(
            f"g3_schema_baby_{i:02d}", "schema_baby_0_2",
            f"Return one valid JSON object with keys mode, age_band, active_languages, card, next_action, safety. "
            f"Mode baby_0_2, active languages ko/ru/en, object {en}. No markdown.",
            "baby_0_2", ["ko", "ru", "en"], "0-2"))
        emit(rows, schema_probe(
            f"g3_schema_child_{i:02d}", "schema_child_3_6",
            f"Return one valid JSON object with keys mode, age_band, active_languages, card, next_action, safety. "
            f"Mode child_3_6, active languages ko/fr/en, object {en}. No markdown.",
            "child_3_6", ["ko", "fr", "en"], "3-6"))

    # G4: session-routing. Four demo languages exist, but session should use only the requested three.
    sessions = [
        ("family_a_ko_ru_en", ["ko", "ru", "en"], "fr"),
        ("family_b_ko_fr_en", ["ko", "fr", "en"], "ru"),
    ]
    for session, active, forbidden in sessions:
        for i, (en, _ko, _ru, _fr) in enumerate(OBJECTS, 1):
            emit(rows, schema_probe(
                f"g4_{session}_{i:02d}", session,
                f"Return JSON only. The app supports ko/ru/fr/en, but this session activates only {', '.join(active)}. "
                f"Do not include {forbidden}. Object: {en}.",
                "parent_bridge", active, "adult") | {"gate": "G4", "forbidden_language": forbidden})

    with OUT.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[write] {len(rows)} probes -> {OUT}")


if __name__ == "__main__":
    main()
