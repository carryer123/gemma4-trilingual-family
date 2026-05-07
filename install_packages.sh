#!/bin/bash
# Gemma 4 해커톤 패키지 설치 — venv 안에서 격리
set -euo pipefail

PROJ=/scratch/hpc198a01/젬마4해커톤
cd "$PROJ"
source venv/bin/activate
export PIP_CACHE_DIR="$PROJ/pip_cache"
mkdir -p "$PIP_CACHE_DIR"

echo "[install] python = $(which python)"

# 핵심 도구
pip install --upgrade pip wheel setuptools

# PyTorch (CUDA 12.1, A100 SM 80 호환)
pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121

# Hugging Face 스택
pip install \
  "transformers>=4.50" \
  "datasets>=3.0" \
  "accelerate>=1.0" \
  "huggingface_hub>=0.24" \
  "hf_transfer" \
  "tokenizers>=0.20" \
  "safetensors"

# Fine-tuning 스택
pip install \
  "peft>=0.13" \
  "trl>=0.12" \
  "bitsandbytes>=0.44" \
  "sentencepiece" \
  "protobuf"

# Unsloth — Gemma 4 day-0 지원
pip install --no-deps "unsloth[cu121-ampere-torch251] @ git+https://github.com/unslothai/unsloth.git"
pip install --no-deps "unsloth_zoo"

# 평가 + 유틸
pip install \
  "evaluate" \
  "scikit-learn" \
  "sacrebleu" \
  "wandb" \
  "tqdm" \
  "pandas" \
  "openpyxl" \
  "soundfile" \
  "librosa"

# 합성 데이터 생성용 (vLLM 또는 transformers 직접)
pip install "vllm>=0.6" || echo "[warn] vllm install failed (optional)"

echo ""
echo "[install] done. Verifying..."
python -c "
import torch
print('torch=', torch.__version__, 'cuda=', torch.cuda.is_available(), 'devs=', torch.cuda.device_count())
import transformers; print('transformers=', transformers.__version__)
import peft; print('peft=', peft.__version__)
import trl; print('trl=', trl.__version__)
import bitsandbytes; print('bitsandbytes=', bitsandbytes.__version__)
try:
    import unsloth; print('unsloth=', unsloth.__version__)
except Exception as e:
    print('unsloth import error:', e)
"
echo "[install] OK"
