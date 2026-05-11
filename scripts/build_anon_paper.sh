#!/bin/bash
# Build an anonymized copy of paper/ for EMNLP/ARR double-blind submission.
# Strips author names, affiliations, ORCID, repo URLs, region-identifying terms.
set -u
PROJ=/scratch/hpc198a01/젬마4해커톤
SRC="$PROJ/paper"
DST="$PROJ/paper_anon"

rm -rf "$DST"
mkdir -p "$DST/sections"

# Copy figures, references unchanged (figures are anonymous; references will be patched in-place)
cp -r "$SRC/figures" "$DST/" 2>/dev/null || true
cp "$SRC/references.bib" "$DST/references.bib" 2>/dev/null || true

# List of section files to anonymize
for f in "$SRC"/main.md "$SRC"/sections/*.md; do
    rel=${f#$SRC/}
    out="$DST/$rel"
    mkdir -p "$(dirname "$out")"
    sed -E \
        -e 's/Byoungsang Lee/Anonymous Author 1/g' \
        -e 's/Yunchul Kim/Anonymous Author 2/g' \
        -e 's/Youmin Shim/Anonymous Author 3/g' \
        -e 's/Chaewon Kwak/Anonymous Author 4/g' \
        -e 's/Jung Heon Lee/Anonymous Author 5/g' \
        -e 's/@misc[{]lee2026fae/@misc{anon2026fae/g' \
        -e 's/Park, J\. and Lee, H\./Anonymous and Anonymous/g' \
        -e 's/Lee, Byoungsang and Kim, Yunchul and Shim, Youmin and Kwak, Chaewon and Lee, Jung Heon/Anonymous and Anonymous and Anonymous and Anonymous and Anonymous/g' \
        -e 's/Lee, Byoungsang and Lee, Jung Heon/Anonymous and Anonymous/g' \
        -e 's/Sungkyunkwan University \(SKKU\)/[University, anonymized]/g' \
        -e 's/Sungkyunkwan University/[University, anonymized]/g' \
        -e 's/\bSKKU\b/[University, anonymized]/g' \
        -e 's/MoonTechnology/[Industry partner, anonymized]/g' \
        -e 's/Sejong Multicultural Family Center \(다문화가족지원센터\)/[Multicultural Family Center, anonymized]/g' \
        -e 's/Sejong Multicultural Family Center/[Multicultural Family Center, anonymized]/g' \
        -e 's/Sejong Regional Specialized Content Development/[Regional support program, anonymized]/g' \
        -e 's/the Sejong (proposal|program|panel|pipeline)/[the regional partnership]/g' \
        -e 's/Sejong N=20/[Anonymous N=20 panel]/g' \
        -e 's/Sejong/[Region, anonymized]/g' \
        -e 's/\bSejong-?i\b/[Character A, anonymized]/g' \
        -e 's/Mallangi/[Character B, anonymized]/g' \
        -e 's/Tomi \(또미\)/[Character C, anonymized]/g' \
        -e 's/세종이|또미|말랑이/[character names anonymized]/g' \
        -e 's/MiraeN/[Industry partner B, anonymized]/g' \
        -e 's/Suwon, Korea//g' \
        -e 's/Mapo-gu, Seoul[^,]*//g' \
        -e 's/Suwon 16419, Korea//g' \
        -e 's/jhlee[0-9]*@skku\.edu/anonymous@example.com/g' \
        -e 's|https://github\.com/[^/[:space:])]*/[A-Za-z0-9_-]*|[GitHub URL, anonymized]|g' \
        -e 's|github\.com/[^/[:space:])]*/[A-Za-z0-9_-]*|[GitHub URL, anonymized]|g' \
        -e 's/0000-000[0-9-]+/[ORCID, anonymized]/g' \
        -e 's|/scratch/hpc198a01/[^[:space:]`]*|[local path]|g' \
        -e 's/carryer[0-9]*/anon/g' \
        "$f" > "$out"
done

# Anonymize bibliography too. Keep third-party citations intact; strip only
# self-identifying author names, local repo placeholders, and affiliations.
if [ -f "$DST/references.bib" ]; then
    sed -i -E \
        -e 's/Lee, Byoungsang/Anonymous/g' \
        -e 's/Kim, Yunchul/Anonymous/g' \
        -e 's/Shim, Youmin/Anonymous/g' \
        -e 's/Kwak, Chaewon/Anonymous/g' \
        -e 's/Lee, Jung Heon/Anonymous/g' \
        -e 's/Park, J\. and Lee, H\./Anonymous and Anonymous/g' \
        -e 's/@misc[{]lee2026fae/@misc{anon2026fae/g' \
        -e 's/gemma4-trilingual-family/[repository anonymized]/g' \
        -e 's/Sejong/[Region, anonymized]/g' \
        -e 's/sejong/[region-anonymized]/g' \
        -e 's/MiraeN/[Industry partner B, anonymized]/g' \
        -e 's|https://github\\.com/[^}[:space:]]+|[GitHub URL, anonymized]|g' \
        -e 's/jhlee[0-9]*@skku\\.edu/anonymous@example.com/g' \
        "$DST/references.bib"
fi

# Special-case main.md author block: replace with anonymous boilerplate
python3 - <<PY
import re, pathlib
p = pathlib.Path("$DST/main.md")
t = p.read_text()
# Replace the author block (lines 3-11 in original) with anonymous boilerplate
t = re.sub(
    r"\*\*Authors(?:\*\*:|\.\*\*).*?(?=\n---)",
    "**Authors**: Anonymous (under double-blind review for EMNLP 2026)\n\n**Affiliation**: [Author Affiliation, anonymized for review]\n\n**Correspondence**: anonymous@example.com\n",
    t,
    count=1,
    flags=re.DOTALL,
)
p.write_text(t)
print("[main.md] author block anonymized")
PY

# Also strip the acknowledgements paragraph from main.md if present
sed -i -E '/We are grateful to the.*University.*Engineering and.*for/,/of this work\./d' "$DST/main.md" 2>/dev/null || true

# Remove planning docs from anon version (PAPER_OUTLINE / PLAN_AB_UPGRADE contain identifying material and are not part of the submission)
echo "[anon] copying done. Top-level files:"
ls "$DST/"
echo ""
echo "[anon] residual identifying terms (should be empty or expected):"
grep -rEi "Lee|MoonTech|Sungkyunkwan|SKKU|Sejong|Mapo|Suwon|MetaBio|jhlee|Byoungsang|carryer|0000-000" "$DST/" 2>&1 | grep -vE "^Binary|^${DST}/figures" | head -20

echo ""
echo "[anon] paper_anon/ ready: $(find $DST -type f -name '*.md' | wc -l) markdown files"
