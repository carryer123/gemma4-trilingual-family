#!/usr/bin/env python3
"""Build the main-boost 4L policy+family repair corpus.

This combines the two successful partial repairs:

* policy_repair fixed G3 schema discipline.
* family_repair fixed most G4 session routing.

The resulting corpus is a deduplicated union with extra G1/G4 examples. Audit
objects remain held out; examples use the training object list from the repair
corpus builder.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import random


PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
DATA = PROJ / "prototype/data"
OUT_TRAIN = DATA / "train_4l_policy_family_repair.jsonl"
OUT_EVAL = DATA / "eval_4l_policy_family_repair.jsonl"
SEED = 20260509


def load_module():
    path = DATA / "24_build_four_language_repair_corpora.py"
    spec = importlib.util.spec_from_file_location("repair_builder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def canon(row: dict) -> str:
    return json.dumps(row, ensure_ascii=False, sort_keys=True)


def write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"[write] {len(rows):,} -> {path.relative_to(PROJ)}")


def main() -> None:
    repair = load_module()
    rows_by_hash: dict[str, dict] = {}
    sources = [
        DATA / "train_4l_policy_repair.jsonl",
        DATA / "train_4l_family_repair.jsonl",
        DATA / "train_4l_balanced_repair.jsonl",
    ]
    for path in sources:
        for row in load_jsonl(path):
            rows_by_hash.setdefault(hashlib.sha256(canon(row).encode("utf-8")).hexdigest(), row)
    rows = list(rows_by_hash.values())

    # Add stronger explicit examples for the two gates that mattered in the
    # repair audit. Keep objects disjoint from the audit holdout list.
    repair.add_g1_repair(rows, repeat=16)
    repair.add_g4_repair(rows, repeat=24)
    rng = random.Random(SEED)
    rng.shuffle(rows)
    write_jsonl(OUT_TRAIN, rows)

    # Common-ish eval for trainer plumbing only; final comparisons use
    # eval_4l_common.jsonl.
    eval_rows = load_jsonl(DATA / "eval_4l_policy_repair.jsonl") + load_jsonl(DATA / "eval_4l_family_repair.jsonl")
    eval_by_hash = {}
    for row in eval_rows:
        eval_by_hash.setdefault(hashlib.sha256(canon(row).encode("utf-8")).hexdigest(), row)
    eval_out = list(eval_by_hash.values())
    rng.shuffle(eval_out)
    write_jsonl(OUT_EVAL, eval_out[:1600])


if __name__ == "__main__":
    main()
