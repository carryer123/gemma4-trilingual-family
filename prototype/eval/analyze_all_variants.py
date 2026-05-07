#!/usr/bin/env python3
"""Analyze all variant_*.jsonl files and produce:
  - PF-1 curve figure (paper Fig. 4)
  - 4-arm bridge-pivot ablation table (markdown)
  - Section 5 numbers ready to paste
  - Per-variant auto-judge summary
"""
from __future__ import annotations
import json, pathlib, re, unicodedata, sys

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
EVAL = PROJ / "prototype/eval"
OUT = PROJ / "paper/figures"
OUT.mkdir(parents=True, exist_ok=True)

EXPECTED_SCRIPT = {
    "phonetic_ko_to_cyr": "cyr",
    "phonetic_ru_to_han": "han",
    "phonetic_ko_to_lat": "lat",
    "phonetic_ru_to_lat": "lat",
}

REQUIRED_KEYS = {
    "func_score_pronunciation": {"score", "mistakes"},
    "func_recommend_next": {"next", "why"},
    "func_explain_in_l1": {"explanation"},
    "func_daily_mission": {"mission", "duration_min", "steps"},
    "code_switch": {"ko", "ru", "en"},
    "grammar_ru_l1_ko_error": {"pairs"},
    "grammar_ko_l1_ru_error": {"pairs"},
    "scenario_breakfast": set(),
    "scenario_park": set(),
    "scenario_doctor": set(),
    "scenario_bedtime": set(),
    "age_0_2": {"script"},
    "age_2_4": {"script"},
    "age_4_6": {"story"},
    "age_6_8": {"hangul", "cyrillic", "latin"},
}


def script_of(s):
    s = (s or "").strip()
    if not s: return "empty"
    counts = {"cyr":0, "han":0, "lat":0, "other":0}
    for ch in s:
        if not ch.isalpha(): continue
        try: n = unicodedata.name(ch)
        except: continue
        if "CYRILLIC" in n: counts["cyr"] += 1
        elif "HANGUL" in n: counts["han"] += 1
        elif "LATIN" in n: counts["lat"] += 1
        else: counts["other"] += 1
    total = sum(counts.values())
    if total == 0: return "empty"
    s2 = sorted(counts.items(), key=lambda x: -x[1])
    if s2[0][1]/total > 0.7: return s2[0][0]
    return "mix"


def extract_json(s):
    if not s: return None
    s = re.sub(r"```(?:json)?", "", s)
    m = re.search(r"\{.*\}", s, re.S)
    if not m: return None
    try: return json.loads(m.group(0))
    except: return None


def score_variant(rows):
    out = {
        "n": len(rows),
        "empty": 0,
        "json_parse_ok": 0,
        "json_parse_total": 0,
        "json_required_keys_ok": 0,
        "translit_correct_script": 0,
        "translit_total": len(EXPECTED_SCRIPT),
        "translit_per_probe": {},
        "mean_tps": 0.0,
    }
    tps_acc = []
    for r in rows:
        resp = r.get("response", "")
        if not resp.strip():
            out["empty"] += 1
        if "tps" in r:
            tps_acc.append(r["tps"])
        if r["id"] in EXPECTED_SCRIPT:
            scr = script_of(resp)
            ok = scr == EXPECTED_SCRIPT[r["id"]]
            if ok: out["translit_correct_script"] += 1
            out["translit_per_probe"][r["id"]] = {"got": scr, "ok": ok, "snippet": resp[:80]}
        if r["id"] in REQUIRED_KEYS:
            out["json_parse_total"] += 1
            obj = extract_json(resp)
            if obj is not None:
                out["json_parse_ok"] += 1
                req = REQUIRED_KEYS[r["id"]]
                if not req or (isinstance(obj, dict) and req.issubset(obj)):
                    out["json_required_keys_ok"] += 1
    if tps_acc:
        out["mean_tps"] = round(sum(tps_acc)/len(tps_acc), 2)
    return out


def main():
    summaries = {}
    for f in sorted(EVAL.glob("variant_*.jsonl")):
        name = f.stem.replace("variant_", "")
        rows = [json.loads(l) for l in f.open()]
        summaries[name] = score_variant(rows)
        s = summaries[name]
        print(f"[{name:18}] n={s['n']:2}  empty={s['empty']}/30  "
              f"json={s['json_parse_ok']}/{s['json_parse_total']}  "
              f"translit={s['translit_correct_script']}/{s['translit_total']}  "
              f"tps={s['mean_tps']}")

    out_json = OUT / "all_variants_scores.json"
    out_json.write_text(json.dumps(summaries, ensure_ascii=False, indent=2))

    # ---- 4-arm bridge-pivot ablation table (Section 5.3) ----
    md = []
    md.append("# Section 5.3 fill — 4-arm bridge-pivot ablation\n")
    md.append("| Arm | Empty | JSON parse | Translit script | tok/s |")
    md.append("|---|---|---|---|---|")
    for arm in ["stock", "L_direct", "L_pivot_only", "L_pivot_filtered", "lora_v2", "L_multilingual"]:
        if arm not in summaries: continue
        s = summaries[arm]
        md.append(f"| **{arm}** | {s['empty']}/30 | {s['json_parse_ok']}/{s['json_parse_total']} ({100*s['json_parse_ok']/max(1,s['json_parse_total']):.0f}%) | {s['translit_correct_script']}/{s['translit_total']} ({100*s['translit_correct_script']/s['translit_total']:.0f}%) | {s['mean_tps']} |")
    md.append("")
    # ---- PF-1 curve table (Section 5.4) ----
    md.append("# Section 5.4 fill — policy-frequency curve")
    md.append("(translit_share_actual_pct from ablation builder)")
    md.append("| Variant | Translit share % | Translit script-correct | JSON parse |")
    md.append("|---|---|---|---|")
    pct_lookup = {"L_policy_00": 0.0, "L_policy_01": 0.95, "L_policy_03": 1.84,
                  "L_policy_05": 1.84, "L_policy_10": 1.84,
                  "lora_v1": 0.0, "lora_v2": 1.46, "stock": float("nan")}
    for arm in ["stock", "L_policy_00", "L_policy_01", "L_policy_03", "L_policy_05", "L_policy_10", "lora_v2"]:
        if arm not in summaries: continue
        s = summaries[arm]
        pct = pct_lookup.get(arm, "?")
        md.append(f"| **{arm}** | {pct} | {s['translit_correct_script']}/{s['translit_total']} ({100*s['translit_correct_script']/s['translit_total']:.0f}%) | {s['json_parse_ok']}/{s['json_parse_total']} |")
    md.append("")
    out_md = OUT / "section_5_3_5_4_fill.md"
    out_md.write_text("\n".join(md), encoding="utf-8")
    print(f"\n[md] -> {out_md}")
    print(f"[json] -> {out_json}")

    # ---- PF-1 figure ----
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        pf_x = []
        pf_y = []
        labels = []
        for arm in ["L_policy_00", "L_policy_01", "L_policy_03", "lora_v2"]:
            if arm not in summaries: continue
            s = summaries[arm]
            pct = pct_lookup[arm]
            acc = s["translit_correct_script"] / s["translit_total"] * 100
            pf_x.append(pct); pf_y.append(acc); labels.append(arm)
        if "stock" in summaries:
            s = summaries["stock"]
            stock_acc = s["translit_correct_script"] / s["translit_total"] * 100
        else:
            stock_acc = 100
        plt.figure(figsize=(6, 4))
        plt.plot(pf_x, pf_y, "o-", linewidth=2, markersize=10, label="LoRA")
        plt.axhline(stock_acc, color="gray", linestyle="--", alpha=0.7, label=f"Stock E2B ({stock_acc:.0f}%)")
        for x, y, l in zip(pf_x, pf_y, labels):
            plt.annotate(l.replace("L_policy_", "p"), (x, y), textcoords="offset points",
                         xytext=(5, -10), fontsize=8)
        plt.xlabel("Transliteration share of training data (%)")
        plt.ylabel("Transliteration script accuracy (%)")
        plt.title("PF-1: Policy-Frequency Curve\n(transliteration regresses below f*, recovers above)")
        plt.grid(alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(OUT / "fig_pf1_curve.png", dpi=160)
        plt.savefig(OUT / "fig_pf1_curve.pdf")
        print(f"[fig] -> {OUT / 'fig_pf1_curve.png'}")
    except Exception as e:
        print(f"[fig] matplotlib failed: {e}")


if __name__ == "__main__":
    main()
