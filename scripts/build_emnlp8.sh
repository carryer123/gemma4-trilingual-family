#!/bin/bash
# Build the compressed EMNLP/ARR-style draft.
set -euo pipefail
PROJ=/scratch/hpc198a01/젬마4해커톤
cd "$PROJ"

OUT="$PROJ/paper/build_emnlp8"
mkdir -p "$OUT"

cp paper/main_emnlp8.md "$OUT/main_emnlp8.md"

if ! command -v pandoc >/dev/null 2>&1; then
    echo "[warn] pandoc not installed; wrote markdown only: $OUT/main_emnlp8.md"
    exit 0
fi

pandoc "$OUT/main_emnlp8.md" \
    --bibliography=paper/references.bib \
    --citeproc \
    --standalone \
    -o "$OUT/main_emnlp8.tex"

pandoc "$OUT/main_emnlp8.md" \
    --bibliography=paper/references.bib \
    --citeproc \
    --pdf-engine=xelatex \
    -V geometry:margin=1in \
    -o "$OUT/main_emnlp8.pdf" || {
        echo "[warn] pdf build failed; tex/markdown are still available"
    }

echo "[ok] $OUT/main_emnlp8.md"
test -f "$OUT/main_emnlp8.tex" && echo "[ok] $OUT/main_emnlp8.tex"
test -f "$OUT/main_emnlp8.pdf" && echo "[ok] $OUT/main_emnlp8.pdf"
