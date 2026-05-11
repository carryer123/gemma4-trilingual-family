#!/usr/bin/env python3
"""Roll-up analysis across all variant_*.jsonl files.

Auto-discovers everything in prototype/eval/variant_*.jsonl, infers the
training meta from the variant name (training-share %, step count, base
model), and emits the cliff curves and the ablation tables.
"""
from __future__ import annotations
import json, pathlib, re, unicodedata
import collections

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


def parse_meta(name: str):
    """Infer (base_model, training_share_pct, step) from variant name.

    Examples:
      stock                → (E2B, None, 0)
      L_direct             → (E2B, ~1.5%, 1500)
      L_policy_00          → (E2B, 0%, 1500)
      L_policy_01          → (E2B, 0.95%, 1500)
      L_policy_03/05/10    → (E2B, 1.84%, 600)
      L_pf_00p5            → (E2B, 0.5%, 2500)
      L_pf_05p0            → (E2B, 5.0%, 2500)
      L_step_dense_p0_step01000 → (E2B, 0%, 1000)
      L_step_dense_p1_5_step02000 → (E2B, 1.5%, 2000)
      lora_v1              → (E2B, 0%, 4512)
      lora_v1_step4000     → (E2B, 0%, 4000)
      lora_v2              → (E2B, 1.46%, 5130)
      lora_v2_step4500     → (E2B, 1.46%, 4500)
      E4B_L_direct         → (E4B, ~1.5%, 1500)
      E4B_L_policy_00      → (E4B, 0%, 1500)
    """
    base = "E4B" if name.startswith("E4B_") else "E2B"
    short = name[len("E4B_"):] if base == "E4B" else name

    # step extraction
    step = None
    m = re.search(r"_step(\d+)$", short)
    if m:
        step = int(m.group(1))
        short = short[:m.start()]

    # specific names
    map_step = {
        "stock": 0, "lora_v1": 4512, "lora_v2": 5130,
        "lora_smoke": 50,
    }
    map_pct = {
        "stock": None, "lora_v1": 0.0, "lora_v2": 1.46,
        "L_policy_00": 0.0, "L_policy_01": 0.95,
        "L_policy_03": 1.84, "L_policy_05": 1.84, "L_policy_10": 1.84,
        "L_direct": 1.50, "L_pivot_only": 1.50,
        "L_pivot_filtered": 1.50, "L_multilingual": 1.40,
    }
    if short in map_step:
        if step is None: step = map_step[short]
    if short in map_pct:
        # FIX: 'step or default' is buggy when step=0 (stock); use explicit None check
        default_step = {"L_policy_03": 600, "L_policy_05": 600, "L_policy_10": 600}.get(short, 1500)
        final_step = step if step is not None else default_step
        return base, map_pct[short], final_step

    # L_pf_XXpY pattern → policy fraction
    m = re.match(r"L_pf_(\d+)p(\d+)$", short)
    if m:
        pct = float(m.group(1)) + float(m.group(2)) / 10
        return base, pct, step if step is not None else 2500

    # L_step_dense_p0 or L_step_dense_p1_5 → 0% or 1.5%
    m = re.match(r"L_step_dense_p(\d+)(?:_(\d+))?$", short)
    if m:
        if m.group(2):
            pct = float(m.group(1)) + float(m.group(2)) / 10
        else:
            pct = float(m.group(1))
        return base, pct, step if step is not None else 5000

    return base, None, step


def score_variant(rows):
    out = {
        "n": len(rows), "empty": 0, "json_parse_ok": 0, "json_parse_total": 0,
        "json_required_keys_ok": 0, "translit_correct_script": 0,
        "translit_total": len(EXPECTED_SCRIPT),
        "mean_tps": 0.0,
    }
    tps_acc = []
    for r in rows:
        resp = r.get("response", "")
        if not resp.strip(): out["empty"] += 1
        if "tps" in r: tps_acc.append(r["tps"])
        if r["id"] in EXPECTED_SCRIPT:
            scr = script_of(resp)
            if scr == EXPECTED_SCRIPT[r["id"]]: out["translit_correct_script"] += 1
        if r["id"] in REQUIRED_KEYS:
            out["json_parse_total"] += 1
            obj = extract_json(resp)
            if obj is not None:
                out["json_parse_ok"] += 1
                req = REQUIRED_KEYS[r["id"]]
                if not req or (isinstance(obj, dict) and req.issubset(obj)):
                    out["json_required_keys_ok"] += 1
    if tps_acc: out["mean_tps"] = round(sum(tps_acc)/len(tps_acc), 2)
    return out


def main():
    summaries = {}
    for f in sorted(EVAL.glob("variant_*.jsonl")):
        name = f.stem.replace("variant_", "")
        rows = [json.loads(l) for l in f.open()]
        if len(rows) < 25:
            print(f"[skip] {name}: only {len(rows)} rows (incomplete eval)")
            continue
        s = score_variant(rows)
        base, pct, step = parse_meta(name)
        s.update({"base": base, "pct": pct, "step": step})
        summaries[name] = s

    print(f"[discover] {len(summaries)} variants")
    print(f"{'name':<32} {'base':<5} {'pct':<7} {'step':<6} {'translit':<10} {'json':<10}")
    for n, s in sorted(summaries.items(), key=lambda x: (x[1]["base"], x[1].get("pct") or -1, x[1].get("step") or 0)):
        print(f"{n:<32} {s['base']:<5} {str(s['pct']):<7} {str(s['step']):<6} "
              f"{s['translit_correct_script']}/{s['translit_total']:<8} "
              f"{s['json_parse_ok']}/{s['json_parse_total']}")

    out_json = OUT / "all_variants_scores.json"
    out_json.write_text(json.dumps(summaries, ensure_ascii=False, indent=2))

    # ---- 4-arm bridge-pivot ablation table (Section 5.3) ----
    md = ["# Section 5.3 — 4-arm bridge-pivot ablation\n",
          "| Arm | Base | Empty | JSON parse | Translit script | tok/s |",
          "|---|---|---|---|---|---|"]
    for arm in ["stock", "L_direct", "L_pivot_only", "L_pivot_filtered", "lora_v2", "L_multilingual",
                "E4B_L_direct", "E4B_L_pivot_only", "E4B_L_pivot_filtered", "E4B_L_multilingual"]:
        if arm not in summaries: continue
        s = summaries[arm]
        md.append(f"| **{arm}** | {s['base']} | {s['empty']}/30 | "
                  f"{s['json_parse_ok']}/{s['json_parse_total']} | "
                  f"{s['translit_correct_script']}/{s['translit_total']} | "
                  f"{s['mean_tps']} |")

    md.append("\n# Section 5.4 — policy-frequency curve (E2B)\n")
    md.append("| Variant | translit% | translit/4 | json/14 |")
    md.append("|---|---|---|---|")
    pf = [(n,s) for n,s in summaries.items() if s["base"]=="E2B" and s.get("pct") is not None]
    pf.sort(key=lambda x: x[1]["pct"])
    for n, s in pf:
        md.append(f"| {n} | {s['pct']}% (step {s['step']}) | "
                  f"{s['translit_correct_script']}/4 | {s['json_parse_ok']}/14 |")

    md.append("\n# Step-axis cliff (0% policy data)\n")
    md.append("| variant | step | translit/4 |")
    md.append("|---|---|---|")
    step_curve_p0 = [(n,s) for n,s in summaries.items() if s.get("pct")==0.0]
    step_curve_p0.sort(key=lambda x: x[1].get("step") or 0)
    for n, s in step_curve_p0:
        md.append(f"| {n} | {s['step']} | {s['translit_correct_script']}/4 |")

    out_md = OUT / "section_5_3_5_4_fill.md"
    out_md.write_text("\n".join(md), encoding="utf-8")
    print(f"\n[md] -> {out_md}")
    print(f"[json] -> {out_json}")

    # ---- PF-1 cliff figure ----
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # E2B policy-fraction curve at "long" training (step >= 2500)
        pts_long = [(s["pct"], s["translit_correct_script"]/s["translit_total"]*100, n)
                    for n,s in summaries.items()
                    if s["base"]=="E2B" and s.get("pct") is not None
                    and (s.get("step") or 0) >= 2500]
        pts_long.sort()
        pts_short = [(s["pct"], s["translit_correct_script"]/s["translit_total"]*100, n)
                     for n,s in summaries.items()
                     if s["base"]=="E2B" and s.get("pct") is not None
                     and (s.get("step") or 0) < 2500 and (s.get("step") or 0) > 0]
        pts_short.sort()

        plt.figure(figsize=(7, 4))
        if pts_long:
            xs, ys, _ = zip(*pts_long)
            plt.plot(xs, ys, "o-", linewidth=2, markersize=8, label="long train (≥2500 steps)", color="C3")
        if pts_short:
            xs, ys, _ = zip(*pts_short)
            plt.plot(xs, ys, "s--", linewidth=2, markersize=8, label="short train (<2500 steps)", color="C0", alpha=0.7)
        plt.axhline(100, color="gray", linestyle=":", alpha=0.5, label="stock baseline (100%)")
        plt.xlabel("Transliteration share of training data (%)")
        plt.ylabel("Transliteration script accuracy (%)")
        plt.title("Policy-Frequency × Training-Duration Interaction\n(E2B base, transliteration policy)")
        plt.grid(alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(OUT / "fig_pf_curve.png", dpi=160)
        plt.savefig(OUT / "fig_pf_curve.pdf")

        # Step-axis curve at f=0
        pts0 = sorted([(s["step"], s["translit_correct_script"]/s["translit_total"]*100, n)
                       for n,s in summaries.items() if s.get("pct")==0.0 and s["base"]=="E2B" and s.get("step") is not None])
        if pts0:
            plt.figure(figsize=(7, 4))
            xs, ys, _ = zip(*pts0)
            plt.plot(xs, ys, "o-", linewidth=2, markersize=8, color="C3", label="0% transliteration data")
            plt.axhline(100, color="gray", linestyle=":", alpha=0.5, label="stock baseline (100%)")
            plt.xlabel("Training steps")
            plt.ylabel("Transliteration script accuracy (%)")
            plt.title("Step-axis cliff (E2B, 0% target policy data)")
            plt.grid(alpha=0.3)
            plt.legend()
            plt.tight_layout()
            plt.savefig(OUT / "fig_step_cliff.png", dpi=160)
            plt.savefig(OUT / "fig_step_cliff.pdf")
        print(f"[fig] -> {OUT / 'fig_pf_curve.png'}, {OUT / 'fig_step_cliff.png'}")
    except Exception as e:
        print(f"[fig] matplotlib failed: {e}")


if __name__ == "__main__":
    main()
