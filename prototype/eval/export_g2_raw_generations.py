#!/usr/bin/env python3
"""Export G2-52 per-probe generations and compare recheck runs.

Inputs:
  paper/figures/g2_extended_scores.json
  paper/figures/g2_recheck_*.json

Outputs:
  paper/figures/g2_extended_raw_generations.jsonl
  paper/figures/g2_recheck_raw_generations.jsonl
  paper/figures/g2_recheck_comparison.md
"""
from __future__ import annotations

import json
import pathlib

PROJ = pathlib.Path("/PATH/REDACTED")
FIG = PROJ / "paper/figures"
PROBES = PROJ / "tools/fae_protocol/probes_v2_translit.jsonl"
MAIN = FIG / "g2_extended_scores.json"
RAW_OUT = FIG / "g2_extended_raw_generations.jsonl"
RECHECK_RAW_OUT = FIG / "g2_recheck_raw_generations.jsonl"
COMPARE_OUT = FIG / "g2_recheck_comparison.md"


def load_probes() -> dict[str, dict]:
    probes = {}
    for line in PROBES.read_text().splitlines():
        if line.strip():
            p = json.loads(line)
            probes[p["id"]] = p
    return probes


def load_variants(path: pathlib.Path) -> dict:
    return json.loads(path.read_text()).get("variants", {})


def score_by_direction(row: dict) -> str:
    parts = []
    for direction, val in sorted(row.get("by_direction", {}).items()):
        parts.append(f"{direction}:{val['correct']}/{val['total']}")
    return ", ".join(parts)


def main() -> None:
    probes = load_probes()
    main_variants = load_variants(MAIN)

    with RAW_OUT.open("w") as f:
        for variant, row in sorted(main_variants.items()):
            for item in row.get("per_probe", []):
                probe = probes.get(item["id"], {})
                rec = {
                    "run_id": "g2_extended_original",
                    "variant": variant,
                    "probe_id": item["id"],
                    "direction": item.get("direction"),
                    "expect_script": item.get("expect_script"),
                    "prompt": probe.get("prompt"),
                    "output": item.get("output", ""),
                    "script_correct": item.get("script_correct"),
                    "target_ratio": item.get("target_ratio"),
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    with RECHECK_RAW_OUT.open("w") as f:
        for path in sorted(FIG.glob("g2_recheck_*.json")):
            if path.name == "g2_recheck_comparison.json":
                continue
            variants = load_variants(path)
            run_id = path.stem
            for variant, row in sorted(variants.items()):
                for item in row.get("per_probe", []):
                    probe = probes.get(item["id"], {})
                    rec = {
                        "run_id": run_id,
                        "variant": variant,
                        "probe_id": item["id"],
                        "direction": item.get("direction"),
                        "expect_script": item.get("expect_script"),
                        "prompt": probe.get("prompt"),
                        "output": item.get("output", ""),
                        "script_correct": item.get("script_correct"),
                        "target_ratio": item.get("target_ratio"),
                    }
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    lines = [
        "# G2-52 Recheck Comparison",
        "",
        "| Variant | Original | Recheck | Match? | Original directions | Recheck directions |",
        "|---|---:|---:|---|---|---|",
    ]
    for path in sorted(FIG.glob("g2_recheck_*.json")):
        variants = load_variants(path)
        for variant, recheck in sorted(variants.items()):
            original = main_variants.get(variant)
            if not original:
                match = "missing-original"
                orig_score = "?"
                orig_dirs = "?"
            else:
                match = (
                    original["g2_score"] == recheck["g2_score"]
                    and original["g2_total"] == recheck["g2_total"]
                )
                match = "YES" if match else "NO"
                orig_score = f"{original['g2_score']}/{original['g2_total']}"
                orig_dirs = score_by_direction(original)
            rec_score = f"{recheck['g2_score']}/{recheck['g2_total']}"
            lines.append(
                f"| `{variant}` | {orig_score} | {rec_score} | **{match}** | "
                f"{orig_dirs} | {score_by_direction(recheck)} |"
            )

    COMPARE_OUT.write_text("\n".join(lines) + "\n")
    print(f"[write] {RAW_OUT}")
    print(f"[write] {RECHECK_RAW_OUT}")
    print(f"[write] {COMPARE_OUT}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
