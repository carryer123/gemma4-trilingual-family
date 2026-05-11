#!/bin/bash
# Parallel four-language audit. Each GPU writes a shard; shards are merged after
# all workers finish. This avoids stale shared JSON writes and uses all 4 A100s.
set -u

PROJ=/scratch/hpc198a01/젬마4해커톤
cd "$PROJ" || exit 1
source venv/bin/activate

mkdir -p logs paper/figures

RUN_ID="${AUDIT4L_RUN_ID:-4l_s1500_$(date +%Y%m%d_%H%M%S)}"
COMMON_ENV=(
  FORCE_AUDIT=1
  AUDIT4L_RESET=1
  AUDIT4L_RUN_ID="$RUN_ID"
)
PIDS=()

launch() {
  local gpu="$1"
  local variants="$2"
  local tag="$3"
  echo "[audit4l] GPU${gpu} ${tag}: ${variants}" >&2
  env CUDA_VISIBLE_DEVICES="$gpu" \
    "${COMMON_ENV[@]}" \
    VARIANTS_FILTER="$variants" \
    AUDIT4L_OUT_FILE="$PROJ/paper/figures/audit4l_scores_${tag}.json" \
    AUDIT4L_RAW_FILE="$PROJ/paper/figures/audit4l_raw_generations_${tag}.jsonl" \
    "$PROJ/venv/bin/python" -u "$PROJ/prototype/eval/eval_4l_audit.py" \
    > "$PROJ/logs/audit4l_${tag}.log" 2>&1 &
  PIDS+=("$!")
}

launch 0 "stock,lora_v2" "g0"
launch 1 "4l_balanced_s1500,4l_policy_high_s1500" "g1"
launch 2 "4l_family_high_s1500" "g2"
launch 3 "4l_no_policy_s1500" "g3"

echo "[audit4l] launched pids: ${PIDS[*]}"
wait "${PIDS[@]}"
echo "[audit4l] workers complete; merging"

"$PROJ/venv/bin/python" - <<'PY'
import json
import pathlib
import shutil

proj = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
fig = proj / "paper/figures"
merged = {"run_id": None, "variants": {}}
for path in sorted(fig.glob("audit4l_scores_g*.json")):
    data = json.loads(path.read_text(encoding="utf-8"))
    if merged["run_id"] is None:
        merged["run_id"] = data.get("run_id")
        merged["probe_file"] = data.get("probe_file")
        merged["probe_sha256"] = data.get("probe_sha256")
    merged["variants"].update(data.get("variants", {}))
out = fig / "audit4l_scores.json"
out.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")

raw_out = fig / "audit4l_raw_generations.jsonl"
with raw_out.open("w", encoding="utf-8") as w:
    for path in sorted(fig.glob("audit4l_raw_generations_g*.jsonl")):
        with path.open(encoding="utf-8") as r:
            shutil.copyfileobj(r, w)
print(f"[merge] {len(merged['variants'])} variants -> {out}")
print(f"[merge] raw -> {raw_out}")
PY

"$PROJ/venv/bin/python" "$PROJ/prototype/eval/summarize_4l_audit.py"
