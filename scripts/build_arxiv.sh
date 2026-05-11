#!/bin/bash
# Pandoc Markdown → LaTeX → PDF for arXiv submission.
# Run: bash scripts/build_arxiv.sh
set -euo pipefail
PROJ=/scratch/hpc198a01/젬마4해커톤
cd "$PROJ"

OUT=$PROJ/paper/build
mkdir -p "$OUT"

# Concatenate all sections in order (main.md is just an index, skip it)
cat paper/sections/01_introduction.md \
    paper/sections/02_related_work.md \
    paper/sections/03_method.md \
    paper/sections/04_family_as_evaluator.md \
    paper/sections/05_experiments.md \
    paper/sections/06_discussion.md \
    paper/sections/07_future_work.md \
    paper/sections/08_conclusion.md > "$OUT/body.md"

cat paper/sections/appendix_A_dataset.md \
    paper/sections/appendix_B_hparams.md \
    paper/sections/appendix_D_failure_gallery.md \
    paper/sections/appendix_E_repro.md \
    paper/sections/appendix_F_protocol.md > "$OUT/appendices.md"

# Header with author block
cat > "$OUT/header.md" <<'HEADER'
---
title: "Beyond BLEU: Family-as-Evaluator for Trilingual L1-Aware On-Device Tutoring with Gemma 4"
author:
  - Byoungsang Lee$^{1,2,*}$
  - Jung Heon Lee$^{1,3,\dagger}$
date: \today
abstract: |
  Multicultural families with two parental L1s and a child growing up trilingual
  are a fast-growing demographic, yet existing language-tutoring products treat
  each user as a monolingual literate single learner. We present a trilingual
  KO+RU+EN co-learning system built around Gemma 4 E2B running entirely on a
  phone, with a moon1-hosted Gemma 4 26B + MTP-drafter + SoulX-FlashHead avatar
  premium tier. We contribute (i) a 50× English-pivot data augmentation taking
  247 KO-RU pairs to 12,408 trilingual triples; (ii) a Family-as-Evaluator
  protocol that surfaces failure modes invisible to BLEU and JSON-parse rate;
  (iii) empirical confirmation that LoRA can regress on under-represented
  policies (transliteration: 100% → 25%) under full training, and recovery
  with 1.5% targeted policy data. We release code, dataset, LoRA adapter, and
  the FaE protocol under Apache 2.0 / CC-BY 4.0.
geometry: margin=1in
fontsize: 11pt
linkcolor: blue
header-includes:
  - \usepackage{booktabs}
  - \usepackage{longtable}
---

\noindent
$^{1}$ School of Advanced Materials Science and Engineering, Sungkyunkwan University (SKKU), Suwon 16419, Korea\
$^{2}$ MoonTechnology, 3F, 29-5, World Cup Buk-ro 48-gil, Mapo-gu, Seoul 03927, Korea\
$^{3}$ Department of MetaBioHealth, Sungkyunkwan University (SKKU), Suwon 16419, Korea\
$^{*}$ First author. $^{\dagger}$ Correspondence: Prof. Jung Heon Lee (jhlee7@skku.edu)\
ORCID: Byoungsang Lee 0000-0001-6874-0935 \quad Jung Heon Lee 0000-0003-4790-3525

\vspace{1em}

HEADER

# Stitch
cat "$OUT/header.md" "$OUT/body.md" > "$OUT/full.md"
echo -e "\n\n# Appendices\n" >> "$OUT/full.md"
cat "$OUT/appendices.md" >> "$OUT/full.md"

if ! command -v pandoc >/dev/null 2>&1; then
    echo "[err] pandoc not installed. Try: conda install -c conda-forge pandoc texlive-core"
    echo "      Or download a binary: https://github.com/jgm/pandoc/releases/latest"
    exit 1
fi

# PDF
pandoc "$OUT/full.md" \
    --bibliography=paper/references.bib \
    --citeproc \
    --pdf-engine=xelatex \
    -V mainfont="Noto Serif" \
    -V CJKmainfont="Noto Serif CJK KR" \
    -V monofont="Noto Sans Mono CJK KR" \
    -o "$OUT/paper.pdf" || {
        echo "[warn] xelatex/CJK fonts failed; falling back to default"
        pandoc "$OUT/full.md" --bibliography=paper/references.bib --citeproc -o "$OUT/paper.pdf"
    }

# LaTeX source (for arXiv)
pandoc "$OUT/full.md" \
    --bibliography=paper/references.bib \
    --citeproc \
    --standalone \
    -o "$OUT/paper.tex"

echo "[ok] PDF: $OUT/paper.pdf"
echo "[ok] LaTeX: $OUT/paper.tex"
echo "[ok] Combined Markdown: $OUT/full.md"
ls -la "$OUT/" 2>&1
