#!/usr/bin/env python3
"""Summarize the same-day four-language curriculum mixes.

The output is intentionally simple and paper-table friendly. It records row
counts, approximate token/character volume, and coarse slice proportions for
the four curriculum variants.
"""
from __future__ import annotations

import json
import pathlib
from collections import Counter


PROJ = pathlib.Path("/PATH/REDACTED")
DATA = PROJ / "prototype/data"
OUT_MD = PROJ / "docs/FOUR_LANGUAGE_DATA_STATS_20260509.md"
OUT_JSON = PROJ / "paper/figures/four_language_data_stats.json"

VARIANTS = [
    "4l_balanced",
    "4l_policy_high",
    "4l_family_high",
    "4l_no_policy",
    "4l_balanced_repair",
    "4l_policy_repair",
    "4l_family_repair",
    "4l_no_policy_repair",
    "4l_policy_family_repair",
]


def load_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def text_of(row: dict) -> str:
    return "\n".join(str(m.get("content", "")) for m in row.get("messages", []))


def classify(row: dict) -> str:
    txt = text_of(row).lower()
    if "session-routing adapter" in txt or "never include inactive languages" in txt:
        return "session_policy"
    if "parent-led card for a pre-verbal baby" in txt or "speaking prompt for a 4-year-old child" in txt:
        return "g1_repair"
    if "script-state tutor" in txt or "phonetic rendering" in txt or "romanization" in txt:
        return "script_policy"
    if "valid json object with keys" in txt:
        return "schema_policy"
    if "family learning card" in txt or "family tutor" in txt or "family_card" in txt:
        return "family_card"
    if "translate " in txt:
        return "translation"
    return "other"


def summarize_split(path: pathlib.Path) -> dict:
    rows = load_jsonl(path)
    counts = Counter(classify(r) for r in rows)
    chars = sum(len(text_of(r)) for r in rows)
    return {
        "rows": len(rows),
        "chars": chars,
        "approx_tokens": round(chars / 4),
        "slices": dict(counts),
    }


def main() -> None:
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    data = {}
    for v in VARIANTS:
        train_file = DATA / f"train_{v}.jsonl"
        eval_file = DATA / f"eval_{v}.jsonl"
        if not train_file.exists() or not eval_file.exists():
            continue
        train = summarize_split(train_file)
        eval_ = summarize_split(eval_file)
        data[v] = {"train": train, "eval": eval_}

    OUT_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Four-Language Curriculum Mix Statistics",
        "",
        "All four LoRA variants share the same base model and training hyperparameters. "
        "The repair and main-boost variants also keep the same hyperparameters; only the data curriculum changes. "
        "Counts below are coarse message-level slices "
        "used to document the ablation; token counts are character/4 approximations.",
        "",
        "| Variant | Train rows | Approx train tokens | Translation | Family | G1 repair | Script policy | Schema policy | G4 session | Eval rows |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for v in VARIANTS:
        train_file = DATA / f"train_{v}.jsonl"
        eval_file = DATA / f"eval_{v}.jsonl"
        if not train_file.exists() or not eval_file.exists():
            continue
        tr = data[v]["train"]
        ev = data[v]["eval"]
        s = tr["slices"]
        lines.append(
            f"| `{v}` | {tr['rows']:,} | {tr['approx_tokens']:,} | "
            f"{s.get('translation', 0):,} | {s.get('family_card', 0):,} | "
            f"{s.get('g1_repair', 0):,} | {s.get('script_policy', 0):,} | "
            f"{s.get('schema_policy', 0):,} | {s.get('session_policy', 0):,} | {ev['rows']:,} |"
        )
    lines.extend([
        "",
        "Pre-registered readout:",
        "",
        "- H1: `4l_policy_high` should improve G2/G3 over `4l_no_policy`.",
        "- H2: `4l_family_high` should improve G1 over `4l_balanced`.",
        "- H3: scalar loss ranking need not match state-gated promotion ranking.",
        "- H4: prompt/base behavior may remain competitive on surface language but is not automatically promotable without G1-G4 gates.",
    ])
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[write] {OUT_MD}")
    print(f"[write] {OUT_JSON}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
