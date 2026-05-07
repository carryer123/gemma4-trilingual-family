#!/bin/bash
# Queued ablation training across 4 GPUs. Each variant goes on a free GPU.
# Run: nohup bash scripts/run_ablation_queue.sh > logs/ablation_queue.log 2>&1 &
set -u

PROJ=/scratch/hpc198a01/젬마4해커톤
cd "$PROJ"
source venv/bin/activate

ABL=prototype/data/ablation
TRAIN=prototype/train/lora_ablation_runner.py

# Wait until LoRA-v2 finishes (it's on GPU 0)
echo "[queue] waiting for LoRA-v2 to finish on GPU 0..."
while pgrep -f "lora_v2_full.py" >/dev/null; do
    sleep 60
    STEP=$(grep -oE '[0-9]+/5130' logs/lora_v2.log 2>/dev/null | tail -1)
    echo "[v2 wait] step=$STEP"
done
echo "[queue] LoRA-v2 done. Launching ablation queue."

# Phase 1: 4 main ablation arms in parallel, one per GPU
launch_one() {
    local GPU=$1; local NAME=$2; local STEPS=$3
    nohup env CUDA_VISIBLE_DEVICES=$GPU \
        TRAIN_FILE=$ABL/${NAME}_train.jsonl \
        OUT_DIR=lora_out/$NAME \
        MAX_STEPS=$STEPS \
        ./venv/bin/python $TRAIN > logs/ablation_${NAME}.log 2>&1 &
    echo "[launch] $NAME on GPU $GPU PID=$!"
}

# Use 1500 steps for each arm to keep wall-clock manageable while still
# letting loss curves cleanly converge below 0.2
STEPS_MAIN=1500

launch_one 0 L_direct $STEPS_MAIN
launch_one 1 L_pivot_only $STEPS_MAIN
launch_one 2 L_pivot_filtered $STEPS_MAIN
launch_one 3 L_multilingual $STEPS_MAIN

# Wait for them all
echo "[queue] waiting for phase 1 (4 ablation arms)..."
wait
echo "[queue] phase 1 complete"

# Phase 2: policy-fraction sweep on GPU 0 (sequential, smaller runs)
for PCT in 00 01 03 05 10; do
    echo "[queue] launching L_policy_${PCT}"
    CUDA_VISIBLE_DEVICES=0 \
        TRAIN_FILE=$ABL/L_policy_${PCT}_train.jsonl \
        OUT_DIR=lora_out/L_policy_${PCT} \
        MAX_STEPS=600 \
        ./venv/bin/python $TRAIN > logs/ablation_L_policy_${PCT}.log 2>&1
    echo "[done] L_policy_${PCT}"
done

echo "[queue] all ablation runs complete"
