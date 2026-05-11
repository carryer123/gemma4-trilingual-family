#!/bin/bash
# Common eval loss for main-boost seed variants.
set -u

PROJ=/scratch/hpc198a01/젬마4해커톤
cd "$PROJ" || exit 1
source venv/bin/activate

mkdir -p logs paper/figures

COMMON_ENV=(
  FORCE_COMMON_LOSS=1
  COMMON_EVAL_FILE="$PROJ/prototype/data/eval_4l_common.jsonl"
  COMMON_LOSS_MAX_EXAMPLES="${COMMON_LOSS_MAX_EXAMPLES:-1200}"
)
PIDS=()

launch() {
  local gpu="$1"
  local variants="$2"
  local tag="$3"
  echo "[main-loss] GPU${gpu} ${tag}: ${variants}" >&2
  env CUDA_VISIBLE_DEVICES="$gpu" \
    "${COMMON_ENV[@]}" \
    VARIANTS_FILTER="$variants" \
    COMMON_LOSS_OUT_FILE="$PROJ/paper/figures/common_4l_main_boost_loss_${tag}.json" \
    "$PROJ/venv/bin/python" -u "$PROJ/prototype/eval/eval_4l_common_loss.py" \
    > "$PROJ/logs/common_4l_main_boost_loss_${tag}.log" 2>&1 &
  PIDS+=("$!")
}

launch 0 "4l_policy_family_repair_seed09_s1500" "g0"
launch 1 "4l_policy_family_repair_seed10_s1500" "g1"
launch 2 "4l_policy_family_repair_seed11_s1500" "g2"
launch 3 "4l_no_policy_seed10_s1500,4l_no_policy_seed11_s1500" "g3"

echo "[main-loss] launched pids: ${PIDS[*]}"
wait "${PIDS[@]}"
echo "[main-loss] workers complete; merging"

"$PROJ/venv/bin/python" - <<'PY'
import json
import pathlib

proj = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
fig = proj / "paper/figures"
merged = {"variants": {}}
for path in sorted(fig.glob("common_4l_main_boost_loss_g*.json")):
    data = json.loads(path.read_text(encoding="utf-8"))
    merged["common_eval_file"] = data.get("common_eval_file")
    merged["variants"].update(data.get("variants", {}))
out = fig / "common_4l_main_boost_loss.json"
out.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"[merge] {len(merged['variants'])} variants -> {out}")
for name, res in sorted(merged["variants"].items(), key=lambda kv: kv[1].get("loss", 999)):
    print(f"  {name:40s} loss={res.get('loss', 0):.4f} ppl={res.get('perplexity', 0):.2f}")
PY
