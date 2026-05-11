#!/usr/bin/env python3
"""Automatic JSON/schema scorer for the extended G3 probe set."""
from __future__ import annotations

import json
import re
from typing import Any


def extract_json(text: str) -> tuple[Any | None, str]:
    text = text.strip()
    if not text:
        return None, "empty"
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S | re.I)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text), "ok"
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1]), "ok_extracted"
        except Exception as exc:
            return None, f"json_parse_error:{type(exc).__name__}"
    return None, "no_json_object"


def type_ok(value: Any, expected: str) -> bool:
    if expected == "str":
        return isinstance(value, str)
    if expected == "bool":
        return isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "dict":
        return isinstance(value, dict)
    if expected == "list":
        return isinstance(value, list)
    return True


def score_one(output: str, probe: dict) -> dict:
    obj, parse_reason = extract_json(output)
    if not isinstance(obj, dict):
        return {
            "schema_correct": False,
            "json_parse_ok": False,
            "reason": parse_reason,
            "missing_keys": probe.get("required_keys", []),
            "type_errors": [],
            "enum_errors": [],
            "extra_keys": [],
        }

    required = probe.get("required_keys", [])
    types = probe.get("types", {})
    enums = probe.get("enums", {})
    missing = [k for k in required if k not in obj]
    type_errors = [k for k, typ in types.items() if k in obj and not type_ok(obj[k], typ)]
    enum_errors = [k for k, vals in enums.items() if k in obj and obj[k] not in vals]
    extra = []
    if probe.get("no_extra_keys", True):
        allowed = set(required)
        extra = sorted(k for k in obj if k not in allowed)
    ok = not missing and not type_errors and not enum_errors and not extra
    return {
        "schema_correct": bool(ok),
        "json_parse_ok": True,
        "reason": "ok" if ok else "schema_violation",
        "missing_keys": missing,
        "type_errors": type_errors,
        "enum_errors": enum_errors,
        "extra_keys": extra,
    }


if __name__ == "__main__":
    demo = {
        "required_keys": ["tool", "arguments", "confirm"],
        "types": {"tool": "str", "arguments": "dict", "confirm": "bool"},
        "enums": {"tool": ["lookup_word"]},
        "no_extra_keys": False,
    }
    cases = [
        ('{"tool":"lookup_word","arguments":{"q":"cat"},"confirm":false}', True),
        ('{"tool":"lookup_word","arguments":[],"confirm":false}', False),
        ('not json', False),
    ]
    for text, want in cases:
        got = score_one(text, demo)["schema_correct"]
        mark = "✓" if got == want else "✗"
        print(f"{mark} schema_correct={got} text={text!r}")
