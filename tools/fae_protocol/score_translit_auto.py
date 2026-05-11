#!/usr/bin/env python3
"""Automatic transliteration script-correctness scorer.

For a given probe with `expect_script` ∈ {hangul, cyrillic, latin} and a
generated text, return:
* `target_ratio` = (chars in target script) / (total alphabetic chars)
* `script_correct` = bool: target_ratio ≥ 0.85 AND no other script > 0.10

Scoring is purely Unicode-block based; no semantic transliteration accuracy
is checked. This is the "G2 script-correct" gate as used in §4.2.

Usage:
    from score_translit_auto import score_one
    res = score_one(text, expect_script="cyrillic")
"""
from __future__ import annotations
import re
import json
import pathlib

# Unicode-block ranges
HANGUL_RANGES = [
    (0xAC00, 0xD7AF),   # syllables
    (0x1100, 0x11FF),   # Jamo
    (0x3130, 0x318F),   # compatibility Jamo
    (0xA960, 0xA97F),   # Jamo extended-A
    (0xD7B0, 0xD7FF),   # Jamo extended-B
]
CYRILLIC_RANGES = [
    (0x0400, 0x04FF),
    (0x0500, 0x052F),   # Cyrillic supplement
    (0x2DE0, 0x2DFF),   # Cyrillic ext-A
    (0xA640, 0xA69F),   # Cyrillic ext-B
]
LATIN_RANGES = [
    (0x0041, 0x005A),   # A-Z
    (0x0061, 0x007A),   # a-z
    (0x00C0, 0x024F),   # Latin-1 supp + ext-A/B
    (0x1E00, 0x1EFF),   # Latin extended additional
]


def _in_ranges(cp: int, ranges) -> bool:
    for lo, hi in ranges:
        if lo <= cp <= hi:
            return True
    return False


def script_of(ch: str) -> str | None:
    cp = ord(ch)
    if _in_ranges(cp, HANGUL_RANGES):
        return "hangul"
    if _in_ranges(cp, CYRILLIC_RANGES):
        return "cyrillic"
    if _in_ranges(cp, LATIN_RANGES):
        return "latin"
    return None


def script_counts(text: str) -> dict:
    counts = {"hangul": 0, "cyrillic": 0, "latin": 0, "other": 0}
    for ch in text:
        s = script_of(ch)
        if s:
            counts[s] += 1
        # else: punctuation, digits, whitespace, CJK ideographs, etc — ignore
    return counts


def score_one(text: str, expect_script: str,
              target_threshold: float = 0.85,
              other_threshold: float = 0.10) -> dict:
    """Return a scoring dict. `script_correct` is bool."""
    counts = script_counts(text)
    total = counts["hangul"] + counts["cyrillic"] + counts["latin"]
    if total == 0:
        return {
            "script_correct": False,
            "reason": "no_alphabetic_chars",
            "target_ratio": 0.0,
            "counts": counts,
        }
    target = counts.get(expect_script, 0)
    target_ratio = target / total
    other_ratios = {k: counts[k] / total for k in counts if k in {"hangul", "cyrillic", "latin"} and k != expect_script}
    other_max = max(other_ratios.values()) if other_ratios else 0.0
    correct = (target_ratio >= target_threshold) and (other_max <= other_threshold)
    return {
        "script_correct": bool(correct),
        "target_ratio": target_ratio,
        "other_max_ratio": other_max,
        "counts": counts,
        "expect_script": expect_script,
    }


def score_probe_run(probes_path: str, generations_path: str) -> dict:
    """Score a generation run. Return aggregate + per-probe scores."""
    probes = {}
    with open(probes_path) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            p = json.loads(line)
            probes[p["id"]] = p
    gens = {}
    with open(generations_path) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            g = json.loads(line)
            gens[g["id"]] = g

    results = []
    correct = 0
    n = 0
    by_direction = {}
    for pid, probe in probes.items():
        if probe.get("category") != "phonetic":
            continue
        n += 1
        text = gens.get(pid, {}).get("output", "")
        s = score_one(text, probe["expect_script"])
        s["id"] = pid
        s["direction"] = probe.get("direction", "?")
        results.append(s)
        if s["script_correct"]:
            correct += 1
        d = probe.get("direction", "?")
        by_direction.setdefault(d, [0, 0])
        by_direction[d][1] += 1
        if s["script_correct"]:
            by_direction[d][0] += 1

    return {
        "g2_score": correct,
        "g2_total": n,
        "g2_pass_rate": correct / n if n else 0.0,
        "by_direction": {d: {"correct": c, "total": t, "pass_rate": c / t if t else 0.0}
                         for d, (c, t) in by_direction.items()},
        "per_probe": results,
    }


# Self-test
if __name__ == "__main__":
    cases = [
        ("Аннёнхасеё", "cyrillic", True),
        ("안녕하세요", "cyrillic", False),
        ("annyeonghaseyo", "latin", True),
        ("안녕하세요, 우리 아기.", "cyrillic", False),  # source-script echo
        ("Спасибо, моя дорогая", "hangul", False),  # cyrillic instead of hangul
        ("스파시바", "hangul", True),
        ("hello WORLD 123", "latin", True),
        ("", "latin", False),
    ]
    for text, expect, want in cases:
        s = score_one(text, expect)
        ok = "✓" if s["script_correct"] == want else "✗"
        print(f"  {ok} expect={expect:9s} script_correct={s['script_correct']!s:5s}  text={text!r}")
