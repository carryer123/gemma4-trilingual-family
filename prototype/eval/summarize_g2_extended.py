#!/usr/bin/env python3
"""Summarize extended G2 results for the paper selector table.

The 52-probe G2 set is intentionally stricter than the historical 4-probe
smoke test. We therefore report a three-band decision instead of pretending a
single hard cutoff cleanly separates good from bad adapters:

* GREEN: total >= 50/52 and every direction >= 12/13
* AMBER: total >= 48/52 and every direction >= 10/13
* RED: anything below the amber floor
"""
from __future__ import annotations

import json
import pathlib

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
G2 = PROJ / "paper/figures/g2_extended_scores.json"
LEGACY = PROJ / "paper/figures/all_variants_scores.json"
OUT = PROJ / "paper/figures/g2_extended_selector_table.md"


def g2_band(row: dict) -> str:
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


def strict_promote(row: dict, g3: object) -> bool:
    return g2_band(row) == "GREEN" and isinstance(g3, int) and g3 >= 8


def main() -> None:
    g2 = json.loads(G2.read_text())["variants"]
    legacy = json.loads(LEGACY.read_text()) if LEGACY.exists() else {}

    lines = [
        "| Variant | G2-52 | Worst direction | G2 band | Legacy G3 | Strict promote? |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for name in sorted(g2):
        row = g2[name]
        dirs = row.get("by_direction", {})
        worst = min((v["correct"], d) for d, v in dirs.items()) if dirs else (0, "?")
        old = legacy.get(name, {})
        g3 = old.get("json_parse_ok", "?")
        g3_total = old.get("json_parse_total", 14)
        band = g2_band(row)
        gate = "PASS" if strict_promote(row, g3) else "REJECT"
        lines.append(
            f"| `{name}` | {row['g2_score']}/{row['g2_total']} | "
            f"{worst[0]}/13 `{worst[1]}` | **{band}** | {g3}/{g3_total} | **{gate}** |"
        )

    OUT.write_text("\n".join(lines) + "\n")
    print(f"[write] {OUT}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
