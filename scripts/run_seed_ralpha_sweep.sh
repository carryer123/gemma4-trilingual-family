#!/bin/bash
# 4-GPU queue runner: pulls jobs from seed_ralpha_queue.txt, runs ≤4 in parallel.
# Each line: name|train_file|max_steps|lora_r|lora_alpha|seed|lr
set -u
PROJ=/scratch/hpc198a01/젬마4해커톤
cd "$PROJ"
source venv/bin/activate

QUEUE="$PROJ/scripts/seed_ralpha_queue.txt"
LOG_DIR="$PROJ/logs"
STATE_DIR="$PROJ/logs/sweep_state"
mkdir -p "$STATE_DIR"

# Read jobs (skip comments + blanks)
mapfile -t JOBS < <(grep -vE '^\s*#|^\s*$' "$QUEUE")
echo "[queue] ${#JOBS[@]} jobs"

declare -A GPU_PID  # GPU_PID[gpu_id] = pid (0 if free)
for G in 0 1 2 3; do GPU_PID[$G]=0; done

JOB_IDX=0
launch_on_gpu() {
    local gpu="$1" line="$2"
    IFS='|' read -r name tf ms r a sd lr <<< "$line"
    local out="lora_out/${name}"
    local log="logs/sweep_${name}.log"
    echo "[launch] gpu=$gpu  name=$name  r=$r α=$a seed=$sd  step=$ms"
    nohup env CUDA_VISIBLE_DEVICES="$gpu" \
        BASE_MODEL=models/unsloth-gemma-4-E2B-it \
        TRAIN_FILE="$tf" OUT_DIR="$out" \
        MAX_STEPS="$ms" SAVE_STEPS=1500 SAVE_TOTAL_LIMIT=999 \
        EVAL_STEPS=0 \
        LORA_R="$r" LORA_ALPHA="$a" SEED="$sd" LR="$lr" \
        ./venv/bin/python prototype/train/lora_ablation_runner.py > "$log" 2>&1 &
    GPU_PID[$gpu]=$!
    echo "$name $! $(date +%s)" > "$STATE_DIR/gpu${gpu}.state"
}

is_done() {
    local name="$1"
    [ -d "lora_out/${name}/checkpoint-4500" ] || \
    [ -f "lora_out/${name}/adapter/adapter_model.safetensors" ]
}

# Initial fill
while [ $JOB_IDX -lt ${#JOBS[@]} ]; do
    free_gpu=""
    for G in 0 1 2 3; do
        pid="${GPU_PID[$G]}"
        if [ "$pid" = "0" ] || ! kill -0 "$pid" 2>/dev/null; then
            free_gpu="$G"; break
        fi
    done
    if [ -n "$free_gpu" ] && [ $JOB_IDX -lt ${#JOBS[@]} ]; then
        # Skip already-done jobs
        IFS='|' read -r jname _ <<< "${JOBS[$JOB_IDX]}"
        if is_done "$jname"; then
            echo "[skip] $jname already done"
            JOB_IDX=$((JOB_IDX+1))
            continue
        fi
        launch_on_gpu "$free_gpu" "${JOBS[$JOB_IDX]}"
        JOB_IDX=$((JOB_IDX+1))
        sleep 30  # stagger model-loads to avoid concurrent disk thrash
    else
        sleep 60
        # Print status
        for G in 0 1 2 3; do
            if [ -f "$STATE_DIR/gpu${G}.state" ]; then
                read sname spid sstart < "$STATE_DIR/gpu${G}.state"
                if kill -0 "$spid" 2>/dev/null; then
                    STEP=$(grep -oE '[0-9]+/[0-9]+' "logs/sweep_${sname}.log" 2>/dev/null | tail -1)
                    echo "  [gpu$G] $sname  step=$STEP"
                fi
            fi
        done
    fi
done

# Wait for the remaining jobs
echo "[queue] all $JOB_IDX jobs dispatched. Waiting for tail..."
for G in 0 1 2 3; do
    pid="${GPU_PID[$G]}"
    [ "$pid" != "0" ] && wait "$pid" 2>/dev/null
done

echo "[done] all 12 sweep jobs complete."

# Auto-eval all sweep variants
echo "[eval] launching 4-GPU eval of all sweep variants..."
SWEEP_NAMES=$(grep -vE '^\s*#|^\s*$' "$QUEUE" | cut -d'|' -f1 | tr '\n' ',' | sed 's/,$//')
nohup env CUDA_VISIBLE_DEVICES=0 ONLY_NEW=1 VARIANTS_INCLUDE_CHECKPOINTS=1 \
    VARIANTS_FILTER="v1seed_42,v1seed_1234,v1seed_7777" \
    ./venv/bin/python prototype/eval/eval_all_variants.py > logs/eval_sweep_g0.log 2>&1 &
nohup env CUDA_VISIBLE_DEVICES=1 ONLY_NEW=1 VARIANTS_INCLUDE_CHECKPOINTS=1 \
    VARIANTS_FILTER="v1seed_99999,v1seed_2026,v1ra_r08_a16" \
    ./venv/bin/python prototype/eval/eval_all_variants.py > logs/eval_sweep_g1.log 2>&1 &
nohup env CUDA_VISIBLE_DEVICES=2 ONLY_NEW=1 VARIANTS_INCLUDE_CHECKPOINTS=1 \
    VARIANTS_FILTER="v1ra_r08_a64,v1ra_r16_a32,v1ra_r16_a64" \
    ./venv/bin/python prototype/eval/eval_all_variants.py > logs/eval_sweep_g2.log 2>&1 &
nohup env CUDA_VISIBLE_DEVICES=3 ONLY_NEW=1 VARIANTS_INCLUDE_CHECKPOINTS=1 \
    VARIANTS_FILTER="v1ra_r64_a16,v1ra_r64_a64,v1ra_r64_a128" \
    ./venv/bin/python prototype/eval/eval_all_variants.py > logs/eval_sweep_g3.log 2>&1 &
wait

echo "[eval] all sweep evals done. Final analysis..."
./venv/bin/python prototype/eval/analyze_all_variants.py > logs/analyze_sweep.log 2>&1
echo "[done] analysis updated. See paper/figures/."
