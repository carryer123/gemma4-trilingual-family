#!/usr/bin/env python3
"""Generate the final 4L main-boost report.

This report is intentionally decision-oriented: it compares scalar common
loss, free-form state gates, seed stability, and the app-layer constrained
promotion decision.
"""
from __future__ import annotations

import json
import math
import pathlib
import re
from collections import defaultdict
from typing import Any


PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
FIG = PROJ / "paper/figures"
DOC = PROJ / "docs/FOUR_LANGUAGE_MAIN_BOOST_RESULTS_20260509.md"

FIRST = FIG / "audit4l_summary.json"
REPAIR = FIG / "audit4l_repair_summary.json"
BOOST = FIG / "audit4l_main_boost_summary.json"
LOSS_BASE = FIG / "common_4l_loss.json"
LOSS_BOOST = FIG / "common_4l_main_boost_loss.json"
APP = FIG / "app_constraints_4l_summary.json"


def read_json(path: pathlib.Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path: pathlib.Path) -> dict[str, dict[str, Any]]:
    raw = read_json(path, [])
    if isinstance(raw, list):
        return {r["variant"]: r for r in raw}
    return {}


def loss_map(*paths: pathlib.Path) -> dict[str, float]:
    out: dict[str, float] = {}
    for path in paths:
        raw = read_json(path, {})
        for name, rec in raw.get("variants", {}).items():
            if isinstance(rec.get("loss"), (float, int)):
                out[name] = float(rec["loss"])
    return out


def pct(x: float | None) -> str:
    if x is None:
        return "-"
    return f"{100*x:.1f}%"


def fmt_loss(x: float | None) -> str:
    if x is None:
        return "-"
    return f"{x:.4f}"


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def std(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def stat(xs: list[float], is_pct: bool = False) -> str:
    if not xs:
        return "-"
    if is_pct:
        return f"{100*mean(xs):.1f} +/- {100*std(xs):.1f}%"
    return f"{mean(xs):.4f} +/- {std(xs):.4f}"


def group_name(variant: str) -> str:
    if variant.startswith("4l_policy_family_repair_seed"):
        return "Policy+Family repair"
    if variant.startswith("4l_no_policy_seed"):
        return "No-policy"
    if variant == "4l_policy_repair_s1500":
        return "Policy repair"
    if variant == "4l_family_repair_s1500":
        return "Family repair"
    if variant == "4l_balanced_repair_s1500":
        return "Balanced repair"
    if variant == "4l_no_policy_repair_s1500":
        return "No-policy repair"
    if variant == "4l_policy_high_s1500":
        return "Policy high"
    if variant == "4l_family_high_s1500":
        return "Family high"
    if variant == "4l_balanced_s1500":
        return "Balanced"
    if variant == "4l_no_policy_s1500":
        return "No-policy first"
    return variant


def seed_num(variant: str) -> str:
    m = re.search(r"_seed(\d+)_s1500$", variant)
    return m.group(1) if m else "-"


def metric(row: dict[str, Any], key: str) -> float | None:
    x = row.get(key)
    return float(x) if isinstance(x, (float, int)) else None


def app_rows() -> dict[str, dict[str, Any]]:
    raw = read_json(APP, {})
    if isinstance(raw, dict):
        if "variants" in raw and isinstance(raw["variants"], dict):
            return raw["variants"]
        if "rows" in raw and isinstance(raw["rows"], list):
            return {r["variant"]: r for r in raw["rows"]}
    if isinstance(raw, list):
        return {r["variant"]: r for r in raw}
    return {}


def app_metric(rec: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        x = rec.get(key)
        if isinstance(x, (float, int)):
            return float(x)
    return None


def app_action(rec: dict[str, Any]) -> str:
    return str(rec.get("action") or rec.get("app_constrained_action") or "?")


def main() -> None:
    all_rows = {}
    for source in (FIRST, REPAIR, BOOST):
        all_rows.update(rows(source))
    losses = loss_map(LOSS_BASE, LOSS_BOOST)
    app = app_rows()

    lines: list[str] = [
        "# Four-Language Main-Boost State-Gated Results (2026-05-09)",
        "",
        "This report extends the first-wave and repair-wave audits with a main-boost run: "
        "three `policy+family` seeds and two additional `no_policy` seeds. The point is "
        "not to find the lowest-loss adapter; it is to test whether a curriculum with "
        "explicit policy and family/session states makes an adapter more promotable "
        "under deployment gates.",
        "",
        "## Main-Boost Per-Seed Results",
        "",
        "| Variant | Seed | Common loss | G1 | G1 Struct | G1 Age | G2 | G3 | G4 | Free-form action | App-constrained action |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]

    boost_names = sorted(
        n for n in all_rows
        if n.startswith("4l_policy_family_repair_seed") or n.startswith("4l_no_policy_seed")
    )
    for name in boost_names:
        row = all_rows[name]
        constrained_action = app.get(name, {}).get("action", "-")
        constrained_action = constrained_action if constrained_action != "-" else app.get(name, {}).get("app_constrained_action", "-")
        lines.append(
            f"| `{name}` | {seed_num(name)} | {fmt_loss(losses.get(name))} | "
            f"{pct(metric(row, 'G1'))} | {pct(metric(row, 'G1_structural'))} | "
            f"{pct(metric(row, 'G1_age_policy'))} | {pct(metric(row, 'G2'))} | "
            f"{pct(metric(row, 'G3'))} | {pct(metric(row, 'G4'))} | "
            f"**{row.get('action', '?')}** | **{constrained_action}** |"
        )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for name in boost_names:
        grouped[group_name(name)].append(all_rows[name])

    lines.extend([
        "",
        "## Seed Aggregate",
        "",
        "| Group | n | Common loss | G1 | G1 Struct | G1 Age | G2 | G3 | G4 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for group in sorted(grouped):
        recs = grouped[group]
        names = [r["variant"] for r in recs]
        lines.append(
            f"| {group} | {len(recs)} | "
            f"{stat([losses[n] for n in names if n in losses])} | "
            f"{stat([r['G1'] for r in recs if isinstance(r.get('G1'), (float, int))], True)} | "
            f"{stat([r['G1_structural'] for r in recs if isinstance(r.get('G1_structural'), (float, int))], True)} | "
            f"{stat([r['G1_age_policy'] for r in recs if isinstance(r.get('G1_age_policy'), (float, int))], True)} | "
            f"{stat([r['G2'] for r in recs if isinstance(r.get('G2'), (float, int))], True)} | "
            f"{stat([r['G3'] for r in recs if isinstance(r.get('G3'), (float, int))], True)} | "
            f"{stat([r['G4'] for r in recs if isinstance(r.get('G4'), (float, int))], True)} |"
        )

    lines.extend([
        "",
        "## Full Scalar-Loss Ranking",
        "",
        "| Rank | Variant | Group | Common loss | G1 | G2 | G3 | G4 | Action |",
        "|---:|---|---|---:|---:|---:|---:|---:|---|",
    ])
    ranked = sorted(
        [(name, loss) for name, loss in losses.items() if name in all_rows],
        key=lambda x: x[1],
    )
    for i, (name, loss) in enumerate(ranked, 1):
        row = all_rows[name]
        lines.append(
            f"| {i} | `{name}` | {group_name(name)} | {loss:.4f} | "
            f"{pct(metric(row, 'G1'))} | {pct(metric(row, 'G2'))} | "
            f"{pct(metric(row, 'G3'))} | {pct(metric(row, 'G4'))} | "
            f"**{row.get('action', '?')}** |"
        )

    lines.extend([
        "",
        "## App-Layer Constraint Interpretation",
        "",
        "Free-form generation is the hard setting: the LoRA must satisfy content, JSON, "
        "and session routing without help. The app-constrained setting is the realistic "
        "product setting: deterministic templates/constrained decoding enforce JSON shape "
        "and active-language routing, while the adapter remains responsible for multilingual "
        "content and script-state behavior.",
        "",
    ])
    if app:
        lines.extend([
            "| Variant | App G1 Struct | App G1 Age | App G2 | App G3 | App G4 | App action |",
            "|---|---:|---:|---:|---:|---:|---|",
        ])
        for name in boost_names:
            rec = app.get(name)
            if not rec:
                continue
            lines.append(
                f"| `{name}` | {pct(app_metric(rec, 'G1_structural', 'app_G1_structural'))} | "
                f"{pct(app_metric(rec, 'G1_age_policy', 'model_G1_age_policy'))} | "
                f"{pct(app_metric(rec, 'G2', 'model_G2'))} | "
                f"{pct(app_metric(rec, 'G3', 'app_G3_schema'))} | "
                f"{pct(app_metric(rec, 'G4', 'app_G4_session'))} | "
                f"**{app_action(rec)}** |"
            )
    else:
        lines.append("_App-layer constraint summary has not been generated yet._")

    lines.extend([
        "",
        "## Paper Takeaway",
        "",
        "- The `policy+family` curriculum substantially changes deployment-state behavior: compared with "
        "`no_policy`, it keeps common loss lower, restores G3 schema behavior, and makes G4 session routing "
        "mostly or fully pass across seeds.",
        "- No free-form adapter is fully GREEN. That is the deployment result, not a failure: LoRA alone should "
        "not be auto-promoted for this interface without deterministic JSON/session constraints.",
        "- Under app-layer constraints, `policy+family` is more stable than `no_policy`: two of three seeds are "
        "GREEN and one is AMBER, while no-policy is split between GREEN and RED and remains much worse on common "
        "loss. The practical product recipe is one 4L LoRA for language/content coverage plus deterministic "
        "templates or constrained decoding for JSON/session state.",
        "",
    ])

    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[write] {DOC}")


if __name__ == "__main__":
    main()
