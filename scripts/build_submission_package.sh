#!/bin/bash
# Build Paper6_EMNLP2026_submission.zip next to the Paper5 package.
set -euo pipefail
PROJ=/scratch/hpc198a01/젬마4해커톤
cd "$PROJ"
./venv/bin/python scripts/build_submission_package.py
