#!/bin/bash
# Relaunch dense step grid with SAVE_TOTAL_LIMIT=999 to preserve all checkpoints.
# The first run (in progress) used the default save_total_limit=2 which deletes
# every old checkpoint as new ones are written. This recovery launches a fresh
# 5000-step run that keeps every save_steps=250 checkpoint.
set -u
PROJ=/PATH/REDACTED
cd "$PROJ"
source venv/bin/activate

ABL=prototype/data/ablation
TRAIN=prototype/train/lora_ablation_runner.py
BASE=$PROJ/models/unsloth-gemma-4-E2B-it

# Wait until the original Track A finishes on GPU 1 and 2
echo "[wait] for original Track A (step grid) to finish..."
while pgrep -f "L_step_dense_p0_train.jsonl\|L_step_dense_p1_5_train.jsonl" >/dev/null; do
    sleep 60
done
echo "[ok] original Track A done. Launching new run with SAVE_TOTAL_LIMIT=999"

# Move the broken outputs aside (they have only 2 checkpoints — keep for evidence)
mv lora_out/L_step_dense_p0     lora_out/L_step_dense_p0_only2     2>/dev/null
mv lora_out/L_step_dense_p1_5   lora_out/L_step_dense_p1_5_only2   2>/dev/null

# Re-launch with full checkpoint retention
nohup env CUDA_VISIBLE_DEVICES=1 \
    BASE_MODEL=$BASE \
    TRAIN_FILE=$ABL/L_step_dense_p0_train.jsonl \
    OUT_DIR=lora_out/L_step_dense_p0 \
    MAX_STEPS=5000 \
    SAVE_STEPS=250 \
    SAVE_TOTAL_LIMIT=999 \
    ./venv/bin/python $TRAIN > logs/dense_step_p0_v2.log 2>&1 &
echo "[launch v2] step 0% on GPU 1 PID=$!"

nohup env CUDA_VISIBLE_DEVICES=2 \
    BASE_MODEL=$BASE \
    TRAIN_FILE=$ABL/L_step_dense_p1_5_train.jsonl \
    OUT_DIR=lora_out/L_step_dense_p1_5 \
    MAX_STEPS=5000 \
    SAVE_STEPS=250 \
    SAVE_TOTAL_LIMIT=999 \
    ./venv/bin/python $TRAIN > logs/dense_step_p1_5_v2.log 2>&1 &
echo "[launch v2] step 1.5% on GPU 2 PID=$!"

wait
echo "[done] dense step grid v2 (all checkpoints preserved)"
