#!/usr/bin/env python3
"""Summarize extended G3 JSON/schema results.

The G3-80 set is an expanded automatic schema-discipline check. It is not a
semantic quality metric; it asks whether an adapter can preserve exact JSON
objects, required keys, type constraints, and simple enum constraints under
deterministic decoding.
"""
from __future__ import annotations

import json
import pathlib

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
G3 = PROJ / "paper/figures/g3_extended_scores.json"
OUT = PROJ / "paper/figures/g3_extended_selector_table.md"


def g3_band(row: dict) -> str:
    groups = row.get("by_group", {})
    if not groups:
        return "RED"
    worst = min(v["correct"] for v in groups.values())
    total = row["g3_score"]
    # Heuristic triage bands, not calibrated statistical cutoffs.
    if total >= 72 and worst >= 18:
        return "GREEN"
    if total >= 64 and worst >= 15:
        return "AMBER"
    return "RED"


def main() -> None:
    if not G3.exists():
        raise SystemExit(f"missing {G3}; run prototype/eval/eval_g3_extended.py first")
    g3 = json.loads(G3.read_text())["variants"]
    lines = [
        "| Variant | G3-80 | Worst group | G3 band | Main failure reason |",
        "|---|---:|---:|---:|---|",
    ]
    for name in sorted(g3):
        row = g3[name]
        groups = row.get("by_group", {})
        worst = min((v["correct"], group) for group, v in groups.items()) if groups else (0, "?")
        reasons: dict[str, int] = {}
        for p in row.get("per_probe", []):
            if not p.get("schema_correct"):
                reasons[p.get("reason", "fail")] = reasons.get(p.get("reason", "fail"), 0) + 1
        reason = max(reasons.items(), key=lambda kv: kv[1])[0] if reasons else "none"
        lines.append(
            f"| `{name}` | {row['g3_score']}/{row['g3_total']} | "
            f"{worst[0]}/20 `{worst[1]}` | **{g3_band(row)}** | {reason} |"
        )
    lines.append("")
    lines.append(
        "G3-80 bands are triage heuristics: GREEN means >=72/80 and every "
        "20-probe group >=18/20; AMBER means >=64/80 and every group >=15/20; "
        "RED is below that floor. These thresholds are not calibrated precision/"
        "recall estimates."
    )
    OUT.write_text("\n".join(lines) + "\n")
    print(f"[write] {OUT}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
