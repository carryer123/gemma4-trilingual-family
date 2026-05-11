#!/bin/bash
# Run the four-language audit once the same-day 4L LoRA sweep has produced
# adapters/checkpoints.
set -u

PROJ=/scratch/hpc198a01/젬마4해커톤
cd "$PROJ" || exit 1
source venv/bin/activate

mkdir -p logs paper/figures

VARIANTS="stock,lora_v2,4l_balanced_s1500,4l_policy_high_s1500,4l_family_high_s1500,4l_no_policy_s1500"
RUN_ID="${AUDIT4L_RUN_ID:-4l_s1500_$(date +%Y%m%d_%H%M%S)}"

env CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}" \
  VARIANTS_FILTER="$VARIANTS" \
  FORCE_AUDIT="${FORCE_AUDIT:-1}" \
  AUDIT4L_RESET="${AUDIT4L_RESET:-1}" \
  AUDIT4L_RUN_ID="$RUN_ID" \
  AUDIT4L_OUT_FILE="$PROJ/paper/figures/audit4l_scores.json" \
  AUDIT4L_RAW_FILE="$PROJ/paper/figures/audit4l_raw_generations.jsonl" \
  "$PROJ/venv/bin/python" -u "$PROJ/prototype/eval/eval_4l_audit.py" \
  | tee "$PROJ/logs/audit4l.log"

"$PROJ/venv/bin/python" "$PROJ/prototype/eval/summarize_4l_audit.py"
