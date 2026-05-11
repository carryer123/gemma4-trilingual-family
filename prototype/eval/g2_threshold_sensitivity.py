#!/usr/bin/env python3
"""Report G2-52 threshold sensitivity for the promotion audit.

The G2-52 gate is a Unicode-block script-state check, not a calibrated
transliteration-quality metric. This report makes the cutoff sensitivity
explicit so the paper does not rely on a single post-hoc threshold.
"""
from __future__ import annotations

import json
import pathlib

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
G2 = PROJ / "paper/figures/g2_extended_scores.json"
LEGACY = PROJ / "paper/figures/all_variants_scores.json"
OUT = PROJ / "paper/figures/g2_threshold_sensitivity.md"

RULES = [
    ("Relaxed G2", 48, 10),
    ("Current green G2", 50, 12),
    ("Perfect G2", 52, 13),
]


def passes_g2(row: dict, total_cutoff: int, direction_cutoff: int) -> bool:
    dirs = row.get("by_direction", {})
    if not dirs:
        return False
    worst = min(v["correct"] for v in dirs.values())
    return row["g2_score"] >= total_cutoff and worst >= direction_cutoff


def g3_score(legacy: dict, name: str) -> int | None:
    value = legacy.get(name, {}).get("json_parse_ok")
    return value if isinstance(value, int) else None


def names(items: list[str]) -> str:
    return ", ".join(f"`{x}`" for x in items) if items else "-"


def main() -> None:
    g2 = json.loads(G2.read_text())["variants"]
    legacy = json.loads(LEGACY.read_text()) if LEGACY.exists() else {}

    lines: list[str] = [
        "| Rule | G2 criterion | G2-pass variants | G2+G3 strict-pass variants | Always-rejected examples |",
        "|---|---|---:|---:|---|",
    ]

    per_rule_pass: dict[str, set[str]] = {}
    for label, total_cutoff, direction_cutoff in RULES:
        g2_pass = sorted(
            name
            for name, row in g2.items()
            if passes_g2(row, total_cutoff, direction_cutoff)
        )
        g2_g3_pass = sorted(
            name
            for name in g2_pass
            if (score := g3_score(legacy, name)) is not None and score >= 8
        )
        per_rule_pass[label] = set(g2_pass)
        always_fail_examples = sorted(
            name
            for name, row in g2.items()
            if not passes_g2(row, total_cutoff, direction_cutoff)
            and name in {"lora_v1", "v1ra_r64_a128", "L_v1_recreate", "lora_v2"}
        )
        lines.append(
            f"| {label} | total ≥{total_cutoff}/52 and every direction ≥{direction_cutoff}/13 "
            f"| {len(g2_pass)}/16 | {len(g2_g3_pass)}/16 | {names(always_fail_examples)} |"
        )

    lines.extend(
        [
            "",
            "| Variant | 48/52 + dir≥10 | 50/52 + dir≥12 | 52/52 + dir=13 | G3 | Interpretation |",
            "|---|---:|---:|---:|---:|---|",
        ]
    )

    focus = [
        "stock",
        "lora_v1",
        "lora_v2",
        "L_v1_recreate",
        "v1ra_r64_a128",
        "v1ra_r16_a64",
        "v1seed_42",
        "v1seed_2026",
    ]
    interp = {
        "stock": "stable positive control",
        "lora_v1": "rejected under every G2 cutoff",
        "lora_v2": "G2-clean but blocked by G3",
        "L_v1_recreate": "threshold-sensitive G2 boundary case",
        "v1ra_r64_a128": "rejected under every G2 cutoff",
        "v1ra_r16_a64": "relaxed-only G2 boundary case",
        "v1seed_42": "passes current G2 and G3",
        "v1seed_2026": "passes perfect G2 and G3",
    }
    for name in focus:
        row = g2[name]
        marks = []
        for _, total_cutoff, direction_cutoff in RULES:
            marks.append("PASS" if passes_g2(row, total_cutoff, direction_cutoff) else "FAIL")
        g3 = g3_score(legacy, name)
        lines.append(
            f"| `{name}` | {marks[0]} | {marks[1]} | {marks[2]} | "
            f"{g3 if g3 is not None else '?'}/14 | {interp[name]} |"
        )

    lines.extend(
        [
            "",
            "The sensitivity check supports two claims only: `lora_v1` is not an artifact of the current 50/52 cutoff, and several controls are threshold-sensitive or blocked by the independent G3 gate. It does not calibrate G2 precision/recall.",
        ]
    )

    OUT.write_text("\n".join(lines) + "\n")
    print(f"[write] {OUT}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
