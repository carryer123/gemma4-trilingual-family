#!/usr/bin/env python3
"""Write a before/after report for first-wave and repair-wave 4L audits."""
from __future__ import annotations

import json
import pathlib


PROJ = pathlib.Path("/PATH/REDACTED")
FIRST = PROJ / "paper/figures/audit4l_summary.json"
REPAIR = PROJ / "paper/figures/audit4l_repair_summary.json"
LOSS = PROJ / "paper/figures/common_4l_loss.json"
OUT = PROJ / "docs/FOUR_LANGUAGE_AUDIT_RESULTS_20260509.md"


def load(path: pathlib.Path) -> dict[str, dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {row["variant"]: row for row in rows}


def pct(x: float) -> str:
    return f"{100*x:.1f}%"


def first_name(repair_name: str) -> str:
    explicit = {
        "4l_family_repair_s1500": "4l_family_high_s1500",
        "4l_policy_repair_s1500": "4l_policy_high_s1500",
    }
    if repair_name in explicit:
        return explicit[repair_name]
    return repair_name.replace("_repair_s1500", "_s1500")


def delta(new: float, old: float) -> str:
    d = 100 * (new - old)
    sign = "+" if d >= 0 else ""
    return f"{sign}{d:.1f} pp"


def main() -> None:
    first = load(FIRST)
    repair = load(REPAIR)
    loss = {}
    if LOSS.exists():
        loss = json.loads(LOSS.read_text(encoding="utf-8")).get("variants", {})
    lines = [
        "# Four-Language State-Gated Audit Results (2026-05-09)",
        "",
        "This report compares the first-wave four-language LoRA curriculum "
        "with the second-wave repair curriculum. The repair wave adds explicit "
        "G1 family-card schema examples and G4 session-routing examples while "
        "keeping audit objects held out from training.",
        "",
        "Common loss is computed on `prototype/data/eval_4l_common.jsonl` "
        "(1200-example cap in the current run). The common eval is intentionally "
        "translation-heavy; deployment behavior is measured by G1-G4.",
        "",
        "## First-Wave Audit",
        "",
        "| Variant | Common loss | G1 Family | G2 Script | G3 Schema | G4 Session | Action |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]

    for name, row in sorted(first.items()):
        l = loss.get(name, {}).get("loss")
        ltxt = f"{l:.4f}" if isinstance(l, (int, float)) else "-"
        lines.append(
            f"| `{name}` | {ltxt} | {pct(row['G1'])} | {pct(row['G2'])} | "
            f"{pct(row['G3'])} | {pct(row['G4'])} | **{row['action']}** |"
        )

    lines.extend([
        "",
        "## Repair-Wave Audit",
        "",
        "| Variant | Common loss | G1 Family | G2 Script | G3 Schema | G4 Session | Action |",
        "|---|---:|---:|---:|---:|---:|---|",
    ])

    for name, row in sorted(repair.items()):
        l = loss.get(name, {}).get("loss")
        ltxt = f"{l:.4f}" if isinstance(l, (int, float)) else "-"
        lines.append(
            f"| `{name}` | {ltxt} | {pct(row['G1'])} | {pct(row['G2'])} | "
            f"{pct(row['G3'])} | {pct(row['G4'])} | **{row['action']}** |"
        )

    lines.extend([
        "",
        "## Before/After Delta",
        "",
        "| Pair | dG1 | dG2 | dG3 | dG4 | First Action | Repair Action |",
        "|---|---:|---:|---:|---:|---|---|",
    ])

    for name, row in sorted(repair.items()):
        old_name = first_name(name)
        old = first.get(old_name)
        if old is None:
            continue
        lines.append(
            f"| `{old_name}` -> `{name}` | {delta(row['G1'], old['G1'])} | "
            f"{delta(row['G2'], old['G2'])} | {delta(row['G3'], old['G3'])} | "
            f"{delta(row['G4'], old['G4'])} | **{old['action']}** | "
            f"**{row['action']}** |"
        )

    lines.extend([
        "",
        "## Scalar-Loss Ranking",
        "",
        "| Rank | Variant | Common loss | G1 | G2 | G3 | G4 | Action |",
        "|---:|---|---:|---:|---:|---:|---:|---|",
    ])
    all_rows = {**first, **repair}
    ranked = sorted(
        [(name, res) for name, res in loss.items() if name in all_rows],
        key=lambda item: item[1].get("loss", 999),
    )
    for i, (name, res) in enumerate(ranked, 1):
        row = all_rows[name]
        lines.append(
            f"| {i} | `{name}` | {res.get('loss', 0):.4f} | "
            f"{pct(row['G1'])} | {pct(row['G2'])} | {pct(row['G3'])} | "
            f"{pct(row['G4'])} | **{row['action']}** |"
        )

    lines.extend([
        "",
        "## Interpretation Template",
        "",
        "- First-wave loss rankings are nearly tied for balanced/policy/family, "
        "but their state gates differ sharply. This supports the scalar-state "
        "disagreement claim.",
        "- The repair wave fixes specific gates but not the whole interface: "
        "`4l_policy_repair_s1500` repairs G3 (0% -> 100%) but not G4, while "
        "`4l_family_repair_s1500` repairs G4 (0% -> 83.3%) but loses G1.",
        "- No adapter is GREEN. The honest deployment conclusion is to keep "
        "LoRA for language coverage but enforce session routing and JSON shape "
        "with a template/constrained-decoding layer before promotion.",
        "",
    ])
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[write] {OUT}")


if __name__ == "__main__":
    main()
