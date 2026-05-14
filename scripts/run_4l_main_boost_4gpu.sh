#!/bin/bash
# Main-boost experiment for EMNLP: policy+family repair seeds plus no-policy
# seed controls. Uses all 4 GPUs in the first wave.
set -u

PROJ=/PATH/REDACTED
cd "$PROJ" || exit 1
source venv/bin/activate

mkdir -p logs lora_out

COMMON=(
  EPOCHS=1
  MAX_STEPS="${MAX_STEPS:-1500}"
  MAX_SEQ="${MAX_SEQ:-2048}"
  LORA_R="${LORA_R:-32}"
  LORA_ALPHA="${LORA_ALPHA:-64}"
  LR="${LR:-2e-4}"
  EVAL_STEPS=0
  SAVE_STEPS=500
  SAVE_TOTAL_LIMIT=3
)

PIDS=()

launch() {
  local gpu="$1"
  local train_name="$2"
  local out_name="$3"
  local seed="$4"
  echo "[main-boost] GPU${gpu} ${out_name} seed=${seed}" >&2
  env CUDA_VISIBLE_DEVICES="$gpu" \
    "${COMMON[@]}" \
    SEED="$seed" \
    TRAIN_FILE="$PROJ/prototype/data/train_${train_name}.jsonl" \
    EVAL_FILE="$PROJ/prototype/data/eval_${train_name}.jsonl" \
    OUT_DIR="$PROJ/lora_out/${out_name}" \
    "$PROJ/venv/bin/python" -u "$PROJ/prototype/train/lora_ablation_runner.py" \
    > "$PROJ/logs/train_${out_name}.log" 2>&1 &
  PIDS+=("$!")
}

"$PROJ/venv/bin/python" "$PROJ/prototype/data/26_build_policy_family_repair.py"

launch 0 "4l_policy_family_repair" "4l_policy_family_repair_seed09_s1500" "20260509"
launch 1 "4l_policy_family_repair" "4l_policy_family_repair_seed10_s1500" "20260510"
launch 2 "4l_policy_family_repair" "4l_policy_family_repair_seed11_s1500" "20260511"
launch 3 "4l_no_policy" "4l_no_policy_seed10_s1500" "20260510"

echo "[main-boost] wave1 launched pids: ${PIDS[*]}"
wait "${PIDS[@]}"
echo "[main-boost] wave1 done"

PIDS=()
launch 0 "4l_no_policy" "4l_no_policy_seed11_s1500" "20260511"
echo "[main-boost] wave2 launched pids: ${PIDS[*]}"
wait "${PIDS[@]}"
echo "[main-boost] all done"
