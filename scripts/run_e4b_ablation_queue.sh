#!/bin/bash
# E4B 9-arm ablation — same data as E2B ablation, different base model.
# Run: nohup bash scripts/run_e4b_ablation_queue.sh > logs/e4b_queue.log 2>&1 &
set -u

PROJ=/PATH/REDACTED
cd "$PROJ"
source venv/bin/activate

ABL=prototype/data/ablation
TRAIN=prototype/train/lora_ablation_runner.py
BASE=$PROJ/models/unsloth-gemma-4-E4B-it

# Phase 1: 4 main ablation arms in parallel, one per GPU
launch_one() {
    local GPU=$1; local NAME=$2; local STEPS=$3
    nohup env CUDA_VISIBLE_DEVICES=$GPU \
        BASE_MODEL=$BASE \
        TRAIN_FILE=$ABL/${NAME}_train.jsonl \
        OUT_DIR=lora_out/E4B_$NAME \
        MAX_STEPS=$STEPS \
        ./venv/bin/python $TRAIN > logs/e4b_${NAME}.log 2>&1 &
    echo "[launch] E4B/$NAME on GPU $GPU PID=$!"
}

STEPS_MAIN=1500

launch_one 0 L_direct $STEPS_MAIN
launch_one 1 L_pivot_only $STEPS_MAIN
launch_one 2 L_pivot_filtered $STEPS_MAIN
launch_one 3 L_multilingual $STEPS_MAIN

echo "[queue] waiting for phase 1 (4 ablation arms)..."
wait
echo "[queue] phase 1 complete"

# Phase 2: policy-fraction sweep, sequential on GPU 0
for PCT in 00 01 03 05 10; do
    echo "[queue] launching E4B/L_policy_${PCT}"
    CUDA_VISIBLE_DEVICES=0 \
        BASE_MODEL=$BASE \
        TRAIN_FILE=$ABL/L_policy_${PCT}_train.jsonl \
        OUT_DIR=lora_out/E4B_L_policy_${PCT} \
        MAX_STEPS=600 \
        ./venv/bin/python $TRAIN > logs/e4b_L_policy_${PCT}.log 2>&1
    echo "[done] E4B/L_policy_${PCT}"
done

echo "[queue] all E4B ablation runs complete"
