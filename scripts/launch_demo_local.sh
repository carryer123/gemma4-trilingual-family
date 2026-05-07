#!/bin/bash
# Launch the Gradio demo locally on port 7860 with the LoRA-v2 adapter.
set -euo pipefail
PROJ=/scratch/hpc198a01/젬마4해커톤
cd "$PROJ"
source venv/bin/activate

# Install gradio if missing
python -c "import gradio" 2>/dev/null || pip install --quiet gradio

ADAPTER_PATH="${ADAPTER_PATH:-$PROJ/lora_out/lora_v2/adapter}"
PORT="${DEMO_PORT:-7860}"
GPU="${CUDA_VISIBLE_DEVICES:-0}"

echo "[demo] adapter=$ADAPTER_PATH port=$PORT GPU=$GPU"
nohup env CUDA_VISIBLE_DEVICES=$GPU ADAPTER_PATH=$ADAPTER_PATH \
    ./venv/bin/python prototype/demo/app.py > logs/demo_gradio.log 2>&1 &
echo "DEMO PID: $!"
sleep 3
tail -5 logs/demo_gradio.log
