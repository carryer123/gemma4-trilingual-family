#!/usr/bin/env bash
# Pull official Gemma 4 E2B litert-lm artifacts from HuggingFace into HPC cache.
# These are the inputs for merge_lora_and_export.py.
#
# Usage:
#   bash download_base_model.sh
#
# Variants (we pull all three; pick the right one for the target device):
#   gemma-4-E2B-it.litertlm                 — generic CPU, 2.59GB (safe fallback)
#   gemma-4-E2B-it_qualcomm_sm8750.litertlm — SD 8 Elite Gen 4 GPU, 3.02GB
#   gemma-4-E2B-it_qualcomm_qcs8275.litertlm — QCS GPU, 3.29GB
#
# We will use these as REFERENCE outputs after our own merge+export.
# The .litertlm we ship in the APK assets is produced by merge_lora_and_export.py,
# NOT one of these files directly (which lack the LoRA-v2 fine-tune).
set -euo pipefail

REPO_ID="litert-community/gemma-4-E2B-it-litert-lm"
DEST="/scratch/hpc198a01/젬마4해커톤/hf_cache/litert/${REPO_ID//\//__}"
mkdir -p "$DEST"

# Use huggingface_hub if available; fall back to git lfs.
if python3 -c "import huggingface_hub" 2>/dev/null; then
  python3 - <<PY
from huggingface_hub import snapshot_download
import os
path = snapshot_download(
    repo_id="$REPO_ID",
    local_dir="$DEST",
    local_dir_use_symlinks=False,
    allow_patterns=[
        "*.litertlm",
        "gemma-4-E2B-it-web.task",
        "README.md",
        "chat_template.jinja",
    ],
)
print("downloaded to:", path)
for f in sorted(os.listdir(path)):
    full = os.path.join(path, f)
    if os.path.isfile(full):
        print(f"  {os.path.getsize(full)/1e9:5.2f} GB  {f}")
PY
else
  echo "[error] huggingface_hub not installed — pip install -U huggingface_hub" >&2
  exit 1
fi

echo
echo "[ok] reference artifacts cached at: $DEST"
