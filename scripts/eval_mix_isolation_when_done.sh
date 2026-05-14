#!/bin/bash
# Wait for all 4 mix-isolation LoRAs to finish, then evaluate.
# Robust signal: lora_out/{NAME}/checkpoint-5000 directory existence (4/4 → done).
# (process counting is unreliable — wrappers/zsh self-match the pgrep pattern.)
set -u
PROJ=/PATH/REDACTED
cd "$PROJ"
source venv/bin/activate

NAMES=(L_v1_recreate V1_no_cards V1_no_scenarios V1_no_triples)
LOGS=(v1_recreate mix_V1_no_cards mix_V1_no_scenarios mix_V1_no_triples)

echo "[wait] for checkpoint-5000 in 4 arms..."
while true; do
    DONE=0
    for N in "${NAMES[@]}"; do
        if [ -d "lora_out/${N}/checkpoint-5000" ] || [ -f "lora_out/${N}/adapter_model.safetensors" ]; then
            DONE=$((DONE+1))
        fi
    done
    if [ "$DONE" -ge 4 ]; then
        echo "[ok] 4/4 final ckpts present."
        break
    fi
    for L in "${LOGS[@]}"; do
        STEP=$(grep -oE '[0-9]+/5000' logs/${L}.log 2>/dev/null | tail -1)
        echo "  [$L] ${STEP:-no-progress-yet}"
    done
    echo "  [progress] $DONE/4 final ckpts"
    sleep 180
done

echo "[ok] all mix-isolation training done. Launching parallel eval (4 GPUs)."

# Brief settle so trainer.save_model finishes flushing safetensors
sleep 30

nohup env CUDA_VISIBLE_DEVICES=0 ONLY_NEW=1 VARIANTS_INCLUDE_CHECKPOINTS=1 \
    VARIANTS_FILTER=L_v1_recreate \
    ./venv/bin/python prototype/eval/eval_all_variants.py > logs/eval_mix_v1.log 2>&1 &
P0=$!
nohup env CUDA_VISIBLE_DEVICES=1 ONLY_NEW=1 VARIANTS_INCLUDE_CHECKPOINTS=1 \
    VARIANTS_FILTER=V1_no_cards \
    ./venv/bin/python prototype/eval/eval_all_variants.py > logs/eval_mix_no_cards.log 2>&1 &
P1=$!
nohup env CUDA_VISIBLE_DEVICES=2 ONLY_NEW=1 VARIANTS_INCLUDE_CHECKPOINTS=1 \
    VARIANTS_FILTER=V1_no_scenarios \
    ./venv/bin/python prototype/eval/eval_all_variants.py > logs/eval_mix_no_scens.log 2>&1 &
P2=$!
nohup env CUDA_VISIBLE_DEVICES=3 ONLY_NEW=1 VARIANTS_INCLUDE_CHECKPOINTS=1 \
    VARIANTS_FILTER=V1_no_triples \
    ./venv/bin/python prototype/eval/eval_all_variants.py > logs/eval_mix_no_triples.log 2>&1 &
P3=$!

echo "[eval pids] $P0 $P1 $P2 $P3"
wait $P0 $P1 $P2 $P3
echo "[done] all evals complete. Final analysis."
./venv/bin/python prototype/eval/analyze_all_variants.py > logs/analyze_mix_isolation.log 2>&1
echo "[done] paper/figures/ updated"
