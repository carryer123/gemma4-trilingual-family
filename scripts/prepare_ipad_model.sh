#!/usr/bin/env bash
set -euo pipefail

MODEL="<HOME>/Downloads/gguf_models/gemma4_e2b_policy.Q4_K_M.gguf"
OUT_DIR="<repo-root>/Gemma4Good_iPad/ipad_transfer"
EXPECTED_SHA="2ea9dffb0af54e88d15a17bec5ea0c4bcd4a37d88045a0f158771555907b3575"

if [ ! -f "$MODEL" ]; then
  echo "missing model: $MODEL" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

ACTUAL_SHA="$(shasum -a 256 "$MODEL" | awk '{print $1}')"
if [ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]; then
  echo "sha256 mismatch" >&2
  echo "expected: $EXPECTED_SHA" >&2
  echo "actual:   $ACTUAL_SHA" >&2
  exit 1
fi

ln -sf "$MODEL" "$OUT_DIR/gemma4_e2b_policy.Q4_K_M.gguf"

cat > "$OUT_DIR/README_TRANSFER_TO_IPAD.txt" <<'EOF'
Copy gemma4_e2b_policy.Q4_K_M.gguf to:

Files app > On My iPad > llama.swiftui

Then open the app:

View Models > Load Local GGUF From Files > select gemma4_e2b_policy.Q4_K_M.gguf

Do not put this 3.4GB model into the app bundle for first testing.
EOF

echo "ready: $OUT_DIR"
ls -lh "$OUT_DIR"

