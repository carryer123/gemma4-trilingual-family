#!/bin/bash
# Wait for L_v1_recreate to finish, then evaluate its checkpoints (single-GPU fallback).
# Same fix: pgrep on cmdline, not on env-only NAME.
set -u
PROJ=/PATH/REDACTED
cd "$PROJ"
source venv/bin/activate

while true; do
    NPROC=$(pgrep -fc 'lora_ablation_runner' || echo 0)
    if [ "$NPROC" -le 0 ]; then
        if [ -d "lora_out/L_v1_recreate/checkpoint-5000" ] || [ -f "lora_out/L_v1_recreate/adapter_model.safetensors" ]; then
            break
        fi
    fi
    STEP=$(grep -oE '[0-9]+/5000' logs/v1_recreate.log 2>/dev/null | tail -1)
    echo "[wait v1_recreate] $STEP  (procs=$NPROC)"
    sleep 120
done

echo "[ok] L_v1_recreate done. Evaluating all checkpoints on GPU 0."

nohup env CUDA_VISIBLE_DEVICES=0 ONLY_NEW=1 VARIANTS_INCLUDE_CHECKPOINTS=1 \
    VARIANTS_FILTER=L_v1_recreate \
    ./venv/bin/python prototype/eval/eval_all_variants.py > logs/eval_v1_recreate.log 2>&1
echo "[done] v1_recreate eval done. Re-running analysis..."

./venv/bin/python prototype/eval/analyze_all_variants.py > logs/analyze_with_v1_recreate.log 2>&1
echo "[done] full analysis updated. See paper/figures/."
