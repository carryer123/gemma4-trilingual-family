#!/usr/bin/env python3
"""Generate the extended G3 JSON/schema probe set.

This creates 80 deterministic structured-output prompts. The set is a
hardening target for the next experiment cycle; the current paper does not
claim results on it until adapters are rerun.
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).with_name("probes_v3_schema.jsonl")


def probe(pid: str, group: str, prompt: str, required: list[str],
          types: dict[str, str], enums: dict[str, list[str]] | None = None,
          no_extra: bool = True) -> dict:
    return {
        "id": pid,
        "category": "schema",
        "gate": "G3",
        "group": group,
        "prompt": prompt,
        "required_keys": required,
        "types": types,
        "enums": enums or {},
        "no_extra_keys": no_extra,
    }


def main() -> None:
    rows = []

    topics = [
        "apple", "bus", "rain", "school", "grandmother",
        "rice", "doctor", "library", "train", "winter",
        "cat", "market", "homework", "milk", "friend",
        "park", "song", "clock", "shoe", "window",
    ]
    for i, topic in enumerate(topics, 1):
        rows.append(probe(
            f"g3_obj_{i:02d}",
            "object_card",
            "Return ONLY JSON for a bilingual object card. "
            f"Topic: {topic}. Schema: "
            '{"ko": string, "ru": string, "en": string, "age_band": one of ["0-2","3-5","6-8"], "safe": boolean}.',
            ["ko", "ru", "en", "age_band", "safe"],
            {"ko": "str", "ru": "str", "en": "str", "age_band": "str", "safe": "bool"},
            {"age_band": ["0-2", "3-5", "6-8"]},
        ))

    intents = [
        "translate", "transliterate", "explain_grammar", "make_quiz", "safety_refusal",
        "object_card", "age_rewrite", "story_prompt", "pronunciation_hint", "function_call",
        "summarize", "compare_words", "detect_language", "repair_json", "choose_register",
        "make_flashcard", "give_example", "correct_sentence", "extract_vocab", "parent_note",
    ]
    for i, intent in enumerate(intents, 1):
        rows.append(probe(
            f"g3_route_{i:02d}",
            "router",
            "Return ONLY JSON for an intent router. "
            f"Utterance intent is {intent}. Schema: "
            '{"intent": enum, "language": one of ["ko","ru","en"], "confidence": number, "needs_parent": boolean}.',
            ["intent", "language", "confidence", "needs_parent"],
            {"intent": "str", "language": "str", "confidence": "number", "needs_parent": "bool"},
            {"intent": intents, "language": ["ko", "ru", "en"]},
        ))

    ages = ["0-2", "3-5", "6-8", "9-12"] * 5
    registers = ["baby", "simple", "school", "parent"] * 5
    for i, (age, register) in enumerate(zip(ages, registers), 1):
        rows.append(probe(
            f"g3_age_{i:02d}",
            "age_register",
            "Return ONLY JSON for an age/register rewrite. "
            f"Target age={age}, register={register}. Schema: "
            '{"text": string, "age_band": enum, "register": enum, "contains_warning": boolean}.',
            ["text", "age_band", "register", "contains_warning"],
            {"text": "str", "age_band": "str", "register": "str", "contains_warning": "bool"},
            {"age_band": ["0-2", "3-5", "6-8", "9-12"], "register": ["baby", "simple", "school", "parent"]},
        ))

    tools = [
        "lookup_word", "save_card", "play_audio", "schedule_review", "flag_safety",
        "translate_pair", "make_quiz", "log_progress", "request_parent", "open_camera",
        "describe_image", "repeat_slowly", "switch_language", "show_trace", "delete_card",
        "export_vocab", "start_timer", "stop_timer", "grade_answer", "suggest_story",
    ]
    for i, tool in enumerate(tools, 1):
        rows.append(probe(
            f"g3_tool_{i:02d}",
            "tool_call",
            "Return ONLY JSON for a tool call. "
            f"Tool={tool}. Schema: "
            '{"tool": enum, "arguments": object, "confirm": boolean}. '
            "The arguments object must contain at least one key.",
            ["tool", "arguments", "confirm"],
            {"tool": "str", "arguments": "dict", "confirm": "bool"},
            {"tool": tools},
            no_extra=False,
        ))

    assert len(rows) == 80, len(rows)
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(f"[write] {OUT} rows={len(rows)}")


if __name__ == "__main__":
    main()
