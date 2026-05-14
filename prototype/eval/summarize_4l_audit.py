#!/usr/bin/env python3
"""Summarize four-language audit scores into Markdown/JSON tables."""
from __future__ import annotations

import json
import os
import pathlib


PROJ = pathlib.Path("/PATH/REDACTED")
IN = pathlib.Path(os.environ.get(
    "AUDIT4L_IN_FILE",
    str(PROJ / "paper/figures/audit4l_scores.json"),
))
OUT_MD = pathlib.Path(os.environ.get(
    "AUDIT4L_SUMMARY_MD",
    str(PROJ / "paper/figures/audit4l_summary.md"),
))
OUT_JSON = pathlib.Path(os.environ.get(
    "AUDIT4L_SUMMARY_JSON",
    str(PROJ / "paper/figures/audit4l_summary.json"),
))


def pct(x: float) -> str:
    return f"{100*x:.1f}%"


def main() -> None:
    data = json.loads(IN.read_text(encoding="utf-8"))
    rows = []
    for name, res in sorted(data.get("variants", {}).items()):
        gates = res.get("by_gate", {})
        row = {
            "variant": name,
            "G1": gates.get("G1", {}).get("pass_rate", 0.0),
            "G2": gates.get("G2", {}).get("pass_rate", 0.0),
            "G3": gates.get("G3", {}).get("pass_rate", 0.0),
            "G4": gates.get("G4", {}).get("pass_rate", 0.0),
            "G1_structural": res.get("by_subgate", {}).get("G1_structural", {}).get("pass_rate", None),
            "G1_age_policy": res.get("by_subgate", {}).get("G1_age_policy", {}).get("pass_rate", None),
            "action": res.get("action", "?"),
        }
        rows.append(row)

    OUT_JSON.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "| Variant | G1 Family | G1 Struct | G1 Age | G2 Script | G3 Schema | G4 Session | Action |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        g1s = "-" if r["G1_structural"] is None else pct(r["G1_structural"])
        g1a = "-" if r["G1_age_policy"] is None else pct(r["G1_age_policy"])
        lines.append(
            f"| `{r['variant']}` | {pct(r['G1'])} | {g1s} | {g1a} | {pct(r['G2'])} | "
            f"{pct(r['G3'])} | {pct(r['G4'])} | **{r['action']}** |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[write] {OUT_MD}")
    print(f"[write] {OUT_JSON}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
