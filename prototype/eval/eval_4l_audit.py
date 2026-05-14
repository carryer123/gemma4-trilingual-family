#!/usr/bin/env python3
"""Evaluate four-language KO/RU/FR/EN audit probes on selected variants.

Gates:
  G1: family-card behavior (schema + mode/session constraints)
  G2: script-state compliance (Unicode-block scorer)
  G3: JSON/schema discipline
  G4: session-routing constraint (four supported languages, <=3 active)

Env:
  VARIANTS_FILTER=stock,lora_v2,4l_balanced_s1500
  AUDIT4L_OUT_FILE=paper/figures/audit4l_scores.json
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import time
import hashlib
from typing import Any

os.environ.setdefault("HF_HOME", "/PATH/REDACTED")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
import unsloth
from unsloth import FastLanguageModel

PROJ = pathlib.Path("/PATH/REDACTED")
sys.path.insert(0, str(PROJ / "tools/fae_protocol"))
from score_schema_auto import extract_json, score_one as score_schema  # noqa: E402
from score_translit_auto import score_one as score_script, script_counts  # noqa: E402

PROBES_FILE = PROJ / "tools/fae_protocol/probes_v4_4l_audit.jsonl"
OUT_FILE = pathlib.Path(os.environ.get("AUDIT4L_OUT_FILE", str(PROJ / "paper/figures/audit4l_scores.json")))
RAW_OUT_FILE = pathlib.Path(os.environ.get("AUDIT4L_RAW_FILE", str(PROJ / "paper/figures/audit4l_raw_generations.jsonl")))
LORA_OUT = PROJ / "lora_out"
STOCK = pathlib.Path(os.environ.get("STOCK_PATH", str(PROJ / "models/unsloth-gemma-4-E2B-it")))
STOCK_LABEL = os.environ.get("STOCK_LABEL", "stock")
FILTER = os.environ.get("VARIANTS_FILTER", "")
MAX_SEQ = int(os.environ.get("MAX_SEQ", "2048"))
MAX_NEW = int(os.environ.get("MAX_NEW", "180"))
FORCE = os.environ.get("FORCE_AUDIT", "0") == "1"
RESET = os.environ.get("AUDIT4L_RESET", "0") == "1"
RUN_ID = os.environ.get("AUDIT4L_RUN_ID", time.strftime("%Y%m%d_%H%M%S"))

FRENCH_MARKERS = {
    "bonjour", "merci", "pomme", "chat", "chien", "lait", "eau", "livre",
    "maison", "voiture", "le", "la", "les", "une", "des", "parapluie",
    "brosse", "dents", "couverture", "lapin", "crayon", "chaussettes",
    "savon", "assiette", "serviette", "banane", "chapeau",
}

BABY_FORBIDDEN = {
    "quiz", "read the sentence", "write", "spell", "homework", "grammar",
    "test", "worksheet",
}
CHILD_SIGNAL = {
    "say", "point", "choose", "find", "repeat", "play", "touch", "speak",
    "show", "look",
}


def log(msg: str) -> None:
    print(msg, flush=True)


def load_probes() -> list[dict]:
    return [json.loads(line) for line in PROBES_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def checkpoint_step(path: pathlib.Path) -> int:
    try:
        return int(path.name.rsplit("-", 1)[-1])
    except ValueError:
        return -1


def discover() -> list[tuple[str, str, bool]]:
    wanted = {p.strip() for p in FILTER.split(",") if p.strip()}
    items: list[tuple[str, str, bool]] = []
    if not wanted or STOCK_LABEL in wanted or "stock" in wanted:
        items.append((STOCK_LABEL, str(STOCK), False))
    for d in sorted(LORA_OUT.iterdir()):
        if not d.is_dir() or (wanted and d.name not in wanted):
            continue
        ad = d / "adapter"
        if ad.is_dir() and (ad / "adapter_config.json").exists():
            items.append((d.name, str(ad), True))
            continue
        # Same-day runs may be evaluated before final adapter save.
        checkpoints = sorted(
            [c for c in d.glob("checkpoint-*") if (c / "adapter_config.json").exists()],
            key=checkpoint_step,
        )
        if checkpoints:
            items.append((d.name, str(checkpoints[-1]), True))
    return items


def gen_one(model, tok, prompt: str) -> str:
    msgs = [{"role": "user", "content": prompt}]
    base_tok = getattr(tok, "tokenizer", tok)
    if getattr(base_tok, "chat_template", None):
        text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    else:
        # Fallback for non-chat base models (e.g. BLOOMz): raw instruction prompt.
        text = prompt + "\n"
    text_tok = getattr(tok, "tokenizer", tok)
    enc = text_tok(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=MAX_NEW, do_sample=False,
                             temperature=None, top_p=None, top_k=None)
    new_ids = out[0][enc["input_ids"].shape[1]:]
    return text_tok.decode(new_ids, skip_special_tokens=True).strip()


def normalize_langs(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v).strip().lower() for v in value]


def flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(flatten_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(flatten_text(v) for v in value)
    return str(value)


def contains_french_marker(text: str) -> bool:
    toks = set(re.findall(r"[a-zà-ÿ']+", text.lower()))
    return bool(toks & FRENCH_MARKERS)


def inactive_language_ok(output: str, obj: Any, forbidden: str | None) -> bool:
    if not forbidden:
        return True
    hay = output + "\n" + flatten_text(obj)
    if forbidden == "ru":
        return script_counts(hay)["cyrillic"] == 0
    if forbidden == "ko":
        return script_counts(hay)["hangul"] == 0
    if forbidden == "fr":
        return not contains_french_marker(hay)
    if forbidden == "en":
        # English is hard to distinguish from French in Latin script. Treat this
        # as a field-level constraint only unless an explicit marker list is added.
        return True
    return True


def family_age_policy_ok(obj: Any, probe: dict) -> bool:
    if probe.get("gate") != "G1" or not isinstance(obj, dict):
        return True
    text = flatten_text(obj).lower()
    mode = probe.get("expect_mode")
    if mode == "baby_0_2":
        return not any(bad in text for bad in BABY_FORBIDDEN)
    if mode == "child_3_6":
        return any(sig in text for sig in CHILD_SIGNAL)
    return True


def language_materialized(output: str, lang: str) -> bool:
    counts = script_counts(output)
    if lang == "ko":
        return counts["hangul"] > 0
    if lang == "ru":
        return counts["cyrillic"] > 0
    if lang == "fr":
        return contains_french_marker(output)
    if lang == "en":
        return bool(re.search(r"[A-Za-z]{3,}", output))
    return True


def materialized_languages_ok(output: str, expected: list[str]) -> bool:
    return all(language_materialized(output, lang) for lang in expected)


def score_json_constraints(output: str, probe: dict) -> dict:
    base = score_schema(output, probe)
    obj, parse_reason = extract_json(output)
    gate = probe.get("gate")
    active = []
    mode_ok = False
    age_ok = False
    active_ok = False
    forbidden_ok = True
    inactive_output_ok = True
    card_lang_ok = False
    age_policy_ok = True
    materialized_ok = False
    expected = [x.lower() for x in probe.get("expect_active_languages", [])]
    if isinstance(obj, dict):
        active = normalize_langs(obj.get("active_languages"))
        mode_ok = obj.get("mode") == probe.get("expect_mode")
        # G1/G4 are action gates, not strict schema gates. If mode is correct
        # but age_band is omitted, G3 should fail it while G1/G4 can still
        # credit the family/session behavior.
        age_ok = obj.get("age_band") == probe.get("expect_age_band") or (
            gate in {"G1", "G4"} and mode_ok
        )
        active_ok = sorted(active) == sorted(expected) and len(active) <= 3
        forbidden = probe.get("forbidden_language")
        if forbidden:
            forbidden_ok = forbidden.lower() not in active
        card = obj.get("card")
        if isinstance(card, dict):
            card_lang_ok = all(lang in card for lang in expected)
            if forbidden:
                forbidden_ok = forbidden_ok and forbidden.lower() not in {str(k).lower() for k in card}
        inactive_output_ok = inactive_language_ok(output, obj, probe.get("forbidden_language"))
        age_policy_ok = family_age_policy_ok(obj, probe)
        materialized_ok = materialized_languages_ok(output, expected)
        if gate in {"G1", "G4"}:
            # For G1/G4, accept language materialization anywhere in the output,
            # not only as top-level card keys. G3 remains the strict schema gate.
            card_lang_ok = card_lang_ok or materialized_ok
    if gate == "G3":
        ok = (
            base["schema_correct"]
            and mode_ok
            and age_ok
            and active_ok
            and forbidden_ok
            and inactive_output_ok
            and card_lang_ok
            and age_policy_ok
        )
    elif gate == "G1":
        ok = (
            base["json_parse_ok"]
            and mode_ok
            and age_ok
            and active_ok
            and card_lang_ok
            and age_policy_ok
        )
    elif gate == "G4":
        ok = (
            base["json_parse_ok"]
            and mode_ok
            and active_ok
            and forbidden_ok
            and inactive_output_ok
            and len(active) <= 3
        )
    else:
        ok = base["schema_correct"]
    return {
        **base,
        "json_parse_reason": parse_reason,
        "mode_ok": mode_ok,
        "age_ok": age_ok,
        "active_languages": active,
        "active_ok": active_ok,
        "forbidden_ok": forbidden_ok,
        "inactive_output_ok": inactive_output_ok,
        "card_lang_ok": card_lang_ok,
        "age_policy_ok": age_policy_ok,
        "materialized_languages_ok": materialized_ok,
        "gate_correct": bool(ok),
    }


def score_output(output: str, probe: dict) -> dict:
    gate = probe["gate"]
    if gate == "G2":
        s = score_script(output, probe["expect_script"])
        sanity = [str(x).lower() for x in probe.get("expect_any_substring", [])]
        out_l = output.lower()
        sanity_ok = True if not sanity else any(x in out_l for x in sanity)
        return {
            **s,
            "content_sanity_ok": sanity_ok,
            "content_sanity_terms": sanity,
            "gate_correct": bool(s["script_correct"] and sanity_ok),
        }
    return score_json_constraints(output, probe)


def score_variant(name: str, path: str, is_adapter: bool, probes: list[dict]) -> dict:
    log(f"[load] {name} from {path}")
    t0 = time.time()
    model, tok = FastLanguageModel.from_pretrained(
        model_name=path,
        max_seq_length=MAX_SEQ,
        load_in_4bit=False,
        load_in_16bit=True,
        full_finetuning=False,
    )
    FastLanguageModel.for_inference(model)
    log(f"[load] {name} done in {time.time() - t0:.1f}s")

    by_gate: dict[str, dict[str, int]] = {}
    by_group: dict[str, dict[str, int]] = {}
    by_subgate: dict[str, dict[str, int]] = {}
    per_probe = []
    with RAW_OUT_FILE.open("a", encoding="utf-8") as rawf:
        for i, probe in enumerate(probes, 1):
            output = gen_one(model, tok, probe["prompt"])
            score = score_output(output, probe)
            gate = probe["gate"]
            group = probe.get("group", gate)
            by_gate.setdefault(gate, {"correct": 0, "total": 0})
            by_group.setdefault(group, {"correct": 0, "total": 0})
            by_gate[gate]["total"] += 1
            by_group[group]["total"] += 1
            if score["gate_correct"]:
                by_gate[gate]["correct"] += 1
                by_group[group]["correct"] += 1
            if gate == "G1":
                structural_ok = bool(
                    score.get("json_parse_ok")
                    and score.get("mode_ok")
                    and score.get("age_ok")
                    and score.get("active_ok")
                    and score.get("card_lang_ok")
                )
                age_policy_ok = bool(score.get("age_policy_ok"))
                for subgate, ok in {
                    "G1_structural": structural_ok,
                    "G1_age_policy": age_policy_ok,
                }.items():
                    by_subgate.setdefault(subgate, {"correct": 0, "total": 0})
                    by_subgate[subgate]["total"] += 1
                    if ok:
                        by_subgate[subgate]["correct"] += 1
            row = {
                "run_id": RUN_ID,
                "variant": name,
                "adapter_path": path,
                "id": probe["id"],
                "gate": gate,
                "group": group,
                "output": output,
                "gate_correct": score["gate_correct"],
                "score": score,
            }
            rawf.write(json.dumps(row, ensure_ascii=False) + "\n")
            per_probe.append({
                "id": probe["id"],
                "gate": gate,
                "group": group,
                "gate_correct": score["gate_correct"],
                "output_preview": output[:160],
                "score": score,
            })
            log(f"[probe] {name} {i:03d}/{len(probes)} {probe['id']} "
                f"{'PASS' if score['gate_correct'] else 'FAIL'}")
    del model, tok
    torch.cuda.empty_cache()
    return {
        "name": name,
        "run_id": RUN_ID,
        "adapter_path": path,
        "is_adapter": is_adapter,
        "probe_file": str(PROBES_FILE),
        "probe_sha256": sha256_file(PROBES_FILE),
        "adapter_config_sha256": sha256_file(pathlib.Path(path) / "adapter_config.json") if is_adapter and (pathlib.Path(path) / "adapter_config.json").exists() else None,
        "by_gate": {
            g: {"correct": v["correct"], "total": v["total"], "pass_rate": v["correct"] / v["total"]}
            for g, v in by_gate.items()
        },
        "by_group": {
            g: {"correct": v["correct"], "total": v["total"], "pass_rate": v["correct"] / v["total"]}
            for g, v in by_group.items()
        },
        "by_subgate": {
            g: {"correct": v["correct"], "total": v["total"], "pass_rate": v["correct"] / v["total"]}
            for g, v in by_subgate.items()
        },
        "per_probe": per_probe,
    }


def action(summary: dict) -> str:
    gates = summary["by_gate"]
    floors = {"G1": 0.80, "G2": 0.85, "G3": 0.90, "G4": 0.90}
    rates = {g: gates.get(g, {}).get("pass_rate", 0.0) for g in floors}
    if all(rates[g] >= floors[g] for g in floors):
        return "GREEN"
    if any(rates[g] < 0.60 for g in floors):
        return "RED"
    return "AMBER"


def main() -> None:
    probes = load_probes()
    log(f"[probes] {len(probes)} 4L audit probes loaded")
    if RESET:
        OUT_FILE.unlink(missing_ok=True)
        RAW_OUT_FILE.unlink(missing_ok=True)
    existing = json.loads(OUT_FILE.read_text()) if OUT_FILE.exists() else {"run_id": RUN_ID, "variants": {}}
    existing.setdefault("run_id", RUN_ID)
    existing.setdefault("probe_file", str(PROBES_FILE))
    existing.setdefault("probe_sha256", sha256_file(PROBES_FILE))
    for name, path, is_adapter in discover():
        if name in existing["variants"] and not FORCE:
            log(f"[skip] {name}")
            continue
        try:
            summary = score_variant(name, path, is_adapter, probes)
        except Exception as exc:
            log(f"[fail] {name}: {exc}")
            continue
        summary["action"] = action(summary)
        existing["variants"][name] = summary
        OUT_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
        log(f"[score] {name} action={summary['action']} gates={summary['by_gate']}")
    log(f"[write] {OUT_FILE}")


if __name__ == "__main__":
    main()
