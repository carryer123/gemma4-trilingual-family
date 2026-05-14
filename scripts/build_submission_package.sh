#!/bin/bash
# Build Paper6_EMNLP2026_submission.zip next to the Paper5 package.
set -euo pipefail
PROJ=/PATH/REDACTED
cd "$PROJ"
./venv/bin/python scripts/build_submission_package.py
