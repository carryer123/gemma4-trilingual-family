#!/usr/bin/env python3
"""Build a combined promotion-decision audit trace.

This table is the selector experiment the paper can honestly support: it does
not estimate population precision/recall, but it shows what scalar selectors
would promote and what behavioral audit state/action each candidate receives.
"""
from __future__ import annotations

import json
import pathlib

PROJ = pathlib.Path("/PATH/REDACTED")
G2 = PROJ / "paper/figures/g2_extended_scores.json"
G3 = PROJ / "paper/figures/g3_extended_scores.json"
LEGACY = PROJ / "paper/figures/all_variants_scores.json"
OUT = PROJ / "paper/figures/selector_audit_trace.md"


def g2_band(row: dict | None) -> str:
    if not row:
        return "NA"
    dirs = row.get("by_direction", {})
    if not dirs:
        return "RED"
    worst = min(v["correct"] for v in dirs.values())
    total = row["g2_score"]
    if total >= 50 and worst >= 12:
        return "GREEN"
    if total >= 48 and worst >= 10:
        return "AMBER"
    return "RED"


def g3_band(row: dict | None, legacy_g3: int | None) -> str:
    if row:
        groups = row.get("by_group", {})
        worst = min((v["correct"] for v in groups.values()), default=0)
        total = row["g3_score"]
        if total >= 72 and worst >= 18:
            return "GREEN"
        if total >= 64 and worst >= 15:
            return "AMBER"
        return "RED"
    if legacy_g3 is None:
        return "NA"
    if legacy_g3 >= 8:
        return "GREEN"
    if legacy_g3 >= 7:
        return "AMBER"
    return "RED"


def action(g2: str, g3: str) -> str:
    if g2 == "GREEN" and g3 == "GREEN":
        return "GREEN: eligible, log audit artifacts"
    if g2 == "RED" or g3 == "RED":
        return "RED: block promotion; retrain/repair then rerun full failed gate"
    if g2 == "AMBER" or g3 == "AMBER":
        return "AMBER: inspect raw outputs; targeted repair or scoped waiver; rerun failed gate"
    return "NA: not scored in expanded audit"


def fmt_score(row: dict | None, key: str, total_key: str) -> str:
    if not row:
        return "not run"
    return f"{row[key]}/{row[total_key]}"


def main() -> None:
    g2 = json.loads(G2.read_text())["variants"] if G2.exists() else {}
    g3 = json.loads(G3.read_text())["variants"] if G3.exists() else {}
    legacy = json.loads(LEGACY.read_text()) if LEGACY.exists() else {}
    names = sorted(set(g2) | set(g3))
    priority = ["stock", "lora_v1", "lora_v2", "L_v1_recreate", "v1ra_r64_a128"]
    names = [n for n in priority if n in names] + [n for n in names if n not in priority]

    lines = [
        "| Adapter | Scalar selector status | G2-52 | G2 state | G3 source | G3 state | Pipeline action |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for name in names:
        g2row = g2.get(name)
        g3row = g3.get(name)
        old = legacy.get(name, {})
        legacy_g3 = old.get("json_parse_ok")
        g2state = g2_band(g2row)
        g3state = g3_band(g3row, legacy_g3 if isinstance(legacy_g3, int) else None)
        if name == "lora_v1":
            scalar = "loss/BLEU-attractive historical candidate"
        elif name == "stock":
            scalar = "baseline"
        else:
            scalar = "controlled comparison candidate"
        g3src = fmt_score(g3row, "g3_score", "g3_total") if g3row else (
            f"legacy {legacy_g3}/14" if isinstance(legacy_g3, int) else "not run"
        )
        lines.append(
            f"| `{name}` | {scalar} | {fmt_score(g2row, 'g2_score', 'g2_total')} | "
            f"**{g2state}** | {g3src} | **{g3state}** | {action(g2state, g3state)} |"
        )
    lines.append("")
    lines.append(
        "This is a promotion-decision audit trace, not a selector benchmark: it "
        "does not estimate false-positive or false-negative rates."
    )
    OUT.write_text("\n".join(lines) + "\n")
    print(f"[write] {OUT}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
