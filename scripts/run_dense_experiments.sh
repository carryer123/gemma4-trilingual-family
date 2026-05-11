#!/bin/bash
# Dense experiments to nail down the cliff:
#  Track A — single LoRA with frequent checkpoints (cliff onset resolution)
#  Track B — 8 policy-fraction LoRAs at long training (cliff width resolution)
# Run after E4B 4-arm phase 1 finishes (GPU 1/2/3 freed up).
set -u

PROJ=/scratch/hpc198a01/젬마4해커톤
cd "$PROJ"
source venv/bin/activate

ABL=prototype/data/ablation
TRAIN=prototype/train/lora_ablation_runner.py
BASE=$PROJ/models/unsloth-gemma-4-E2B-it

# wait until E4B 4-arm phase 1 frees GPU 1/2/3
echo "[wait] for E4B phase 1 to finish (4 ablation arms in parallel)..."
while pgrep -f "BASE_MODEL.*E4B-it.*L_(direct|pivot_only|pivot_filtered|multilingual)" >/dev/null 2>&1; do
    sleep 60
    echo "  [E4B phase 1] still running..."
done
# Also check if any 'lora_ablation_runner.py' is still running E4B phase 1
while pgrep -af "lora_ablation_runner" 2>/dev/null | grep -E "L_(direct|pivot_only|pivot_filtered|multilingual)" >/dev/null; do
    sleep 60
done
echo "[ok] E4B phase 1 done. Starting dense experiments on GPU 1/2/3."

# Track A — single dense-step LoRA on GPU 1
# save_steps=250 → checkpoint at step 250, 500, 750, ..., 5000 (20 ckpts)
nohup env CUDA_VISIBLE_DEVICES=1 \
    BASE_MODEL=$BASE \
    TRAIN_FILE=$ABL/L_step_dense_p0_train.jsonl \
    OUT_DIR=lora_out/L_step_dense_p0 \
    MAX_STEPS=5000 \
    SAVE_STEPS=250 \
    ./venv/bin/python $TRAIN > logs/dense_step_p0.log 2>&1 &
echo "[launch] dense step 0% on GPU 1 PID=$!"

# Track A second curve (1.5% translit) on GPU 2 — for comparison
nohup env CUDA_VISIBLE_DEVICES=2 \
    BASE_MODEL=$BASE \
    TRAIN_FILE=$ABL/L_step_dense_p1_5_train.jsonl \
    OUT_DIR=lora_out/L_step_dense_p1_5 \
    MAX_STEPS=5000 \
    SAVE_STEPS=250 \
    ./venv/bin/python $TRAIN > logs/dense_step_p1_5.log 2>&1 &
echo "[launch] dense step 1.5% on GPU 2 PID=$!"

# Track B — policy fraction grid, sequential on GPU 3 (8 variants × 1500 step each)
# Use 1500 steps to keep wall-clock manageable; long enough to be in regression zone
# (we know step ~4000 is regression; 1500 probably won't show cliff but tests a lower bound)
# For TRUE cliff investigation we need 4500 steps each → 8 × 1.7hr = ~13hr, too long
# Compromise: train at 2500 steps each (between 1500 baseline and 4000 onset) = 8 × 50min = 6.7hr
GRID_STEPS=2500
for PCT in 00p0 00p5 01p0 02p0 03p0 05p0 08p0 10p0; do
    echo "[track B] launching L_pf_${PCT} on GPU 3 (${GRID_STEPS} steps)"
    CUDA_VISIBLE_DEVICES=3 \
        BASE_MODEL=$BASE \
        TRAIN_FILE=$ABL/L_pf_${PCT}_train.jsonl \
        OUT_DIR=lora_out/L_pf_${PCT} \
        MAX_STEPS=$GRID_STEPS \
        ./venv/bin/python $TRAIN > logs/dense_pf_${PCT}.log 2>&1
    echo "[done] L_pf_${PCT}"
done

echo "[wait] for Track A to finish too..."
wait
echo "[done] all dense experiments finished"
