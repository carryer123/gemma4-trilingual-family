#!/usr/bin/env python3
"""Build a shared four-language evaluation set for cross-variant loss.

Variant-specific eval splits are useful during training but not for comparing
loss across curricula. This script deduplicates the existing 4L eval files and
writes one fixed common eval set used by every adapter.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import random


PROJ = pathlib.Path("/PATH/REDACTED")
DATA = PROJ / "prototype/data"
OUT = DATA / "eval_4l_common.jsonl"
MANIFEST = DATA / "eval_4l_common_manifest.json"
SEED = 20260509
MAX_ROWS = 2400

INPUTS = [
    DATA / "eval_4l_balanced.jsonl",
    DATA / "eval_4l_policy_high.jsonl",
    DATA / "eval_4l_family_high.jsonl",
    DATA / "eval_4l_no_policy.jsonl",
    DATA / "eval_4l_balanced_repair.jsonl",
    DATA / "eval_4l_policy_repair.jsonl",
    DATA / "eval_4l_family_repair.jsonl",
    DATA / "eval_4l_no_policy_repair.jsonl",
]


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def family(ex: dict) -> str:
    msgs = ex.get("messages") or []
    sys = (msgs[0].get("content", "") if msgs else "").lower()
    user = (msgs[1].get("content", "") if len(msgs) > 1 else "").lower()
    joined = sys + "\n" + user
    if "json" in joined or "active_languages" in joined:
        return "schema_or_family"
    if "transliter" in joined or "phonetic" in joined or "script" in joined:
        return "script_policy"
    if "translate" in joined:
        return "translation"
    return "other"


def main() -> None:
    by_hash: dict[str, dict] = {}
    source_counts = {}
    family_counts = {}
    for path in INPUTS:
        if not path.exists():
            continue
        count = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            canon = json.dumps(obj, ensure_ascii=False, sort_keys=True)
            by_hash.setdefault(sha(canon), obj)
            count += 1
        source_counts[path.name] = count

    rows = list(by_hash.values())
    rng = random.Random(SEED)
    rng.shuffle(rows)
    if len(rows) > MAX_ROWS:
        rows = rows[:MAX_ROWS]

    for row in rows:
        f = family(row)
        family_counts[f] = family_counts.get(f, 0) + 1

    OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest = {
        "seed": SEED,
        "max_rows": MAX_ROWS,
        "rows": len(rows),
        "deduped_pool_rows": len(by_hash),
        "source_counts": source_counts,
        "family_counts": family_counts,
        "output": str(OUT),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[write] {OUT} rows={len(rows)}")
    print(f"[write] {MANIFEST}")
    print(json.dumps(family_counts, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
