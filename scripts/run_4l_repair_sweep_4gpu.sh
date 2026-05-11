#!/bin/bash
# Second-wave same-day sweep: explicit G1/G4 repair curriculum.
set -u

PROJ=/scratch/hpc198a01/젬마4해커톤
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
  SEED="${SEED:-20260509}"
  EVAL_STEPS=0
  SAVE_STEPS=500
  SAVE_TOTAL_LIMIT=3
)

launch() {
  local gpu="$1"
  local name="$2"
  echo "[repair] GPU${gpu} ${name}" >&2
  env CUDA_VISIBLE_DEVICES="$gpu" \
    "${COMMON[@]}" \
    TRAIN_FILE="$PROJ/prototype/data/train_${name}.jsonl" \
    EVAL_FILE="$PROJ/prototype/data/eval_${name}.jsonl" \
    OUT_DIR="$PROJ/lora_out/${name}_s1500" \
    "$PROJ/venv/bin/python" -u "$PROJ/prototype/train/lora_ablation_runner.py" \
    > "$PROJ/logs/train_${name}_s1500.log" 2>&1 &
  PIDS+=("$!")
}

PIDS=()
launch 0 "4l_balanced_repair"
launch 1 "4l_policy_repair"
launch 2 "4l_family_repair"
launch 3 "4l_no_policy_repair"

echo "[repair] launched pids: ${PIDS[*]}"
wait "${PIDS[@]}"
echo "[repair] all done"
