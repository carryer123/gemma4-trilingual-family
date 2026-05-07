#!/bin/bash
# Initialize a clean Git repo for public release. Run in a fresh dir or after
# the relevant files have been committed.
set -euo pipefail
PROJ=/scratch/hpc198a01/젬마4해커톤
RELEASE=/scratch/hpc198a01/gemma4-trilingual-family-public
cd "$PROJ"

# Make a clean release directory by copying public-release files only.
mkdir -p "$RELEASE"
cd "$RELEASE"

git init -q
git remote remove origin 2>/dev/null || true

# Public files to include (Apache 2.0, no private docs)
rsync -av \
    --include='LICENSE' \
    --include='.gitignore' \
    --include='README.md' \
    --include='HACKATHON_SUBMISSION.md' \
    --include='DEMO_VIDEO_STORYBOARD.md' \
    --include='CREDENTIALS_NEEDED.md' \
    --include='setup_env.sh' \
    --include='install_packages.sh' \
    --include='paper/***' \
    --include='prototype/***' \
    --include='research/Gemma4_스펙_요약_*.md' \
    --include='research/대회규정_요약_*.md' \
    --include='research/MTP_드래프터_요약_*.md' \
    --include='research/다국어_데이터셋_큐레이션_*.md' \
    --include='scripts/***' \
    --include='tools/***' \
    --exclude='paper/build' \
    --exclude='research/대회규정_상세_*.md' \
    --exclude='docs/세종_지역특화콘텐츠_제안서_*.md' \
    --exclude='*.log' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='venv' \
    --exclude='hf_cache' \
    --exclude='torch_cache' \
    --exclude='pip_cache' \
    --exclude='tmp' \
    --exclude='models' \
    --exclude='ollama*' \
    --exclude='lora_out/*/checkpoint-*' \
    --exclude='lora_out/*/runs' \
    --exclude='lora_out/*/gguf-q4_k_m' \
    --exclude='prototype/data/raw' \
    --exclude='prototype/data/ablation' \
    --exclude='prototype/data/train_*.jsonl' \
    --exclude='prototype/data/eval_*.jsonl' \
    --exclude='hf_cache' \
    "$PROJ/" "$RELEASE/" 2>&1 | tail -20

cd "$RELEASE"

# Don't include adapter files in repo — too big (240MB each); host on HuggingFace
echo "lora_out/" >> .gitignore
echo "kagglehub_cache/" >> .gitignore

git add LICENSE .gitignore README.md HACKATHON_SUBMISSION.md \
        DEMO_VIDEO_STORYBOARD.md \
        paper/ prototype/ research/ scripts/ tools/ \
        setup_env.sh install_packages.sh 2>/dev/null || true

git -c user.email=carryer12345@gmail.com -c user.name="Byoungsang Lee" \
    commit -m "Initial public release: arXiv v1 + Gemma 4 Good Hackathon submission

- Trilingual KO+RU+EN family co-learning system on Gemma 4 E2B + LoRA
- Bridge-pivot data augmentation (247 → 12,408 trilingual triples, 50×)
- Family-as-Evaluator protocol (Appendix F + tools/fae_protocol/)
- 4-arm bridge-pivot ablation + 5-arm policy-frequency sweep
- Open data, code, LoRA recipe under Apache 2.0 / CC-BY 4.0

Co-Authored-By: Jung Heon Lee <jhlee7@skku.edu>" 2>&1 | tail -5

echo ""
echo "[ok] release dir prepared at: $RELEASE"
echo "[next] Create remote and push:"
echo "  cd $RELEASE"
echo "  gh repo create gemma4-trilingual-family --public --description 'Trilingual KO+RU+EN family co-learning on Gemma 4 E2B (Apache 2.0)'"
echo "  git push -u origin main"
echo ""
echo "[contents]"
ls -la "$RELEASE/" 2>&1 | head -20
echo "..."
du -sh "$RELEASE/" 2>&1
