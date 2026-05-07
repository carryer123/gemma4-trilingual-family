#!/usr/bin/env python3
"""Auto-judge LoRA-v1 vs stock for objectively-checkable properties.

Properties checked:
  1. Empty response (any whitespace-only output)
  2. JSON parse rate for function-call probes
  3. Cyrillic-only output for phonetic_ko_to_cyr
  4. Hangul-only output for phonetic_ru_to_han
  5. Latin-only output for *_to_lat
  6. Required-key presence for function calls

Output: prototype/eval/auto_judge_summary.json
"""
import json, pathlib, re, unicodedata

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
SIDE = PROJ / "prototype/eval/lora_v1_vs_stock.jsonl"
OUT = PROJ / "prototype/eval/auto_judge_summary.json"


def script_of(s):
    """Return dominant script: 'cyr', 'han' (Hangul), 'lat', 'mix', 'empty'."""
    s = (s or "").strip()
    if not s:
        return "empty"
    counts = {"cyr": 0, "han": 0, "lat": 0, "other": 0}
    for ch in s:
        if not ch.isalpha():
            continue
        try:
            n = unicodedata.name(ch)
        except ValueError:
            continue
        if "CYRILLIC" in n:
            counts["cyr"] += 1
        elif "HANGUL" in n:
            counts["han"] += 1
        elif "LATIN" in n:
            counts["lat"] += 1
        else:
            counts["other"] += 1
    total = sum(counts.values())
    if total == 0:
        return "empty"
    sorted_scripts = sorted(counts.items(), key=lambda x: -x[1])
    if sorted_scripts[0][1] / total > 0.7:
        return sorted_scripts[0][0]
    return "mix"


def extract_json(s):
    """Find first {...} block in s, parse it. Return obj or None."""
    if not s:
        return None
    s = re.sub(r"```(?:json)?", "", s)
    m = re.search(r"\{.*\}", s, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def main():
    rows = [json.loads(l) for l in SIDE.open()]

    metrics = {"stock": {}, "lora": {}}

    def score_set(prefix, model_key):
        m = metrics[model_key]
        m["empty"] = 0
        m["empty_ids"] = []
        m["json_parse_ok"] = 0
        m["json_parse_total"] = 0
        m["json_required_keys_ok"] = 0
        m["transliteration_correct_script"] = 0
        m["transliteration_total"] = 0
        m["transliteration_failed_ids"] = []

        REQUIRED_KEYS = {
            "func_score_pronunciation": {"score", "mistakes"},
            "func_recommend_next": {"next", "why"},
            "func_explain_in_l1": {"explanation", "l1"},
            "func_daily_mission": {"mission", "duration_min", "steps"},
            "scenario_breakfast": set(),  # array
            "scenario_park": set(),
            "scenario_doctor": set(),
            "scenario_bedtime": set(),
            "age_0_2": {"script"},
            "age_2_4": {"script"},
            "age_4_6": {"story"},
            "age_6_8": {"hangul", "cyrillic", "latin"},
            "grammar_ru_l1_ko_error": {"pairs"},
            "grammar_ko_l1_ru_error": {"pairs"},
            "code_switch": {"ko", "ru", "en"},
            "phonetic_ko_cyr": set(),
            "phonetic_ru_han": set(),
            "func_score_pronunciation": {"score", "mistakes"},
        }

        TRANSLIT_EXPECTED = {
            "phonetic_ko_to_cyr": "cyr",
            "phonetic_ru_to_han": "han",
            "phonetic_ko_to_lat": "lat",
            "phonetic_ru_to_lat": "lat",
        }

        for r in rows:
            resp = r.get(f"{prefix}response", "")
            if not resp.strip():
                m["empty"] += 1
                m["empty_ids"].append(r["id"])
                continue
            # JSON parse for function/scenario
            if r["id"].startswith(("func_", "scenario_", "age_", "grammar_ru_l1", "grammar_ko_l1", "code_switch")):
                m["json_parse_total"] += 1
                obj = extract_json(resp)
                if obj is not None:
                    m["json_parse_ok"] += 1
                    needed = REQUIRED_KEYS.get(r["id"], set())
                    if not needed or (isinstance(obj, dict) and needed.issubset(obj)):
                        m["json_required_keys_ok"] += 1
            # transliteration script
            if r["id"] in TRANSLIT_EXPECTED:
                m["transliteration_total"] += 1
                if script_of(resp) == TRANSLIT_EXPECTED[r["id"]]:
                    m["transliteration_correct_script"] += 1
                else:
                    m["transliteration_failed_ids"].append({
                        "id": r["id"], "expected": TRANSLIT_EXPECTED[r["id"]],
                        "got_script": script_of(resp), "snippet": resp[:80]
                    })

    score_set("stock_", "stock")
    score_set("lora_", "lora")

    # Print human-readable
    out = {
        "n_probes": len(rows),
        "stock": metrics["stock"],
        "lora": metrics["lora"],
        "deltas": {
            "empty_change": metrics["lora"]["empty"] - metrics["stock"]["empty"],
            "json_parse_change": (
                (metrics["lora"]["json_parse_ok"] - metrics["stock"]["json_parse_ok"])
            ),
            "transliteration_change": (
                metrics["lora"]["transliteration_correct_script"] - metrics["stock"]["transliteration_correct_script"]
            ),
        }
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
