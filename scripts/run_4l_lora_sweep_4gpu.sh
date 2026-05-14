#!/bin/bash
# Four-language KO/RU/FR/EN LoRA sweep.
#
# One GPU per state-gated data curriculum variant:
#   0: balanced
#   1: policy_high   (more G2/G3 policy examples)
#   2: family_high   (more family-card/age-band examples)
#   3: no_policy     (ablation without explicit script/schema policy examples)
#
# The first pass is capped at MAX_STEPS=1500 so it can finish within a same-day
# experiment window. Rerun with MAX_STEPS=0 EPOCHS=2 for full training.
set -u

PROJ=/PATH/REDACTED
cd "$PROJ" || exit 1
source venv/bin/activate

mkdir -p logs lora_out

COMMON_ENV=(
  MAX_STEPS=1500
  EPOCHS=1
  MAX_SEQ=2048
  SAVE_STEPS=500
  SAVE_TOTAL_LIMIT=2
  EVAL_STEPS=0
  LORA_R=32
  LORA_ALPHA=64
  LR=2e-4
)

launch() {
  local gpu="$1"
  local name="$2"
  local seed="$3"
  echo "[4l] launch gpu=${gpu} name=${name} seed=${seed}" >&2
  nohup env CUDA_VISIBLE_DEVICES="$gpu" \
    "${COMMON_ENV[@]}" \
    SEED="$seed" \
    TRAIN_FILE="$PROJ/prototype/data/train_${name}.jsonl" \
    EVAL_FILE="$PROJ/prototype/data/eval_${name}.jsonl" \
    OUT_DIR="$PROJ/lora_out/${name}_s1500" \
    "$PROJ/venv/bin/python" -u "$PROJ/prototype/train/lora_ablation_runner.py" \
    > "$PROJ/logs/${name}_s1500.log" 2>&1 &
  echo $!
}

P0=$(launch 0 4l_balanced 20260509)
P1=$(launch 1 4l_policy_high 20260510)
P2=$(launch 2 4l_family_high 20260511)
P3=$(launch 3 4l_no_policy 20260512)

echo "[4l] pids: $P0 $P1 $P2 $P3"
echo "[4l] logs:"
echo "  logs/4l_balanced_s1500.log"
echo "  logs/4l_policy_high_s1500.log"
echo "  logs/4l_family_high_s1500.log"
echo "  logs/4l_no_policy_s1500.log"
echo "[4l] wait with: tail -f logs/4l_*_s1500.log"
