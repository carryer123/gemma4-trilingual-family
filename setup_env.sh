#!/bin/bash
# Gemma 4 해커톤 환경 셋업 — 모든 것을 /scratch/hpc198a01/젬마4해커톤/ 안에 격리
set -euo pipefail

PROJ=/scratch/hpc198a01/젬마4해커톤
cd "$PROJ"

# venv 가 이미 있어야 함 (python3.10 -m venv 로 생성됨)
source venv/bin/activate

# HuggingFace 캐시 + 로그 + 데이터셋 캐시 격리
export HF_HOME="$PROJ/hf_cache"
export TRANSFORMERS_CACHE="$PROJ/hf_cache"
export HF_DATASETS_CACHE="$PROJ/hf_cache/datasets"
export HF_HUB_ENABLE_HF_TRANSFER=1
export TORCH_HOME="$PROJ/torch_cache"
export PIP_CACHE_DIR="$PROJ/pip_cache"
export TMPDIR="$PROJ/tmp"
mkdir -p "$HF_HOME" "$TORCH_HOME" "$PIP_CACHE_DIR" "$TMPDIR" "$PROJ/models" "$PROJ/data" "$PROJ/lora_out" "$PROJ/logs"

echo "[setup] venv: $(which python)"
echo "[setup] python: $(python --version)"
echo "[setup] HF_HOME: $HF_HOME"
echo "[setup] CUDA visible: ${CUDA_VISIBLE_DEVICES:-all}"

python -c "import torch; print('[torch]', torch.__version__, 'cuda', torch.cuda.is_available(), 'devs', torch.cuda.device_count())" 2>&1 || true
