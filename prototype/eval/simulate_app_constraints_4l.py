#!/usr/bin/env python3
"""Estimate app-layer constrained promotion from 4L audit scores.

This is not a model benchmark. It answers a product/deployment question:
what if JSON shape and session routing are enforced by the app instead of
being delegated to free-form generation?

Assumptions:
* G2 remains model-dependent.
* G1 age-policy remains model-dependent when available.
* G1 structure, G3 schema, and G4 session routing are enforced by templates.
"""
from __future__ import annotations

import json
import pathlib


PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
INPUTS = [
    PROJ / "paper/figures/audit4l_repair_scores.json",
    PROJ / "paper/figures/audit4l_main_boost_scores.json",
]
OUT_MD = PROJ / "paper/figures/app_constraints_4l_summary.md"
OUT_JSON = PROJ / "paper/figures/app_constraints_4l_summary.json"


def pct(x: float) -> str:
    return f"{100*x:.1f}%"


def action(g1_age: float, g2: float, g3: float, g4: float) -> str:
    if g2 >= 0.85 and g3 >= 0.90 and g4 >= 0.90 and g1_age >= 0.80:
        return "GREEN"
    if g2 < 0.60 or g1_age < 0.60:
        return "RED"
    return "AMBER"


def main() -> None:
    rows = []
    for path in INPUTS:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for name, res in sorted(data.get("variants", {}).items()):
            gates = res.get("by_gate", {})
            sub = res.get("by_subgate", {})
            g2 = gates.get("G2", {}).get("pass_rate", 0.0)
            g1_age = sub.get("G1_age_policy", {}).get(
                "pass_rate",
                gates.get("G1", {}).get("pass_rate", 0.0),
            )
            row = {
                "variant": name,
                "source": path.name,
                "model_G2": g2,
                "model_G1_age_policy": g1_age,
                "app_G1_structural": 1.0,
                "app_G3_schema": 1.0,
                "app_G4_session": 1.0,
            }
            row["app_constrained_action"] = action(g1_age, g2, 1.0, 1.0)
            rows.append(row)

    OUT_JSON.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "| Variant | Source | Model G2 | Model G1 age-policy | App G1 struct | App G3 | App G4 | App-constrained action |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        lines.append(
            f"| `{r['variant']}` | `{r['source']}` | {pct(r['model_G2'])} | "
            f"{pct(r['model_G1_age_policy'])} | {pct(r['app_G1_structural'])} | "
            f"{pct(r['app_G3_schema'])} | {pct(r['app_G4_session'])} | "
            f"**{r['app_constrained_action']}** |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[write] {OUT_MD}")
    print(f"[write] {OUT_JSON}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
