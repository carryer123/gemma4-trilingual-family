#!/bin/bash
# Watch for the current eval to finish, then relaunch to pick up new variants.
# Each iteration the script's skip-logic ensures we don't re-eval completed ones.
set -u
PROJ=/PATH/REDACTED
cd "$PROJ"

# wait for current eval
while pgrep -f "eval_all_variants" >/dev/null; do
    sleep 30
done
echo "[watchdog] previous eval finished. Relaunching to pick up new variants..."

source venv/bin/activate
nohup env CUDA_VISIBLE_DEVICES=0 ./venv/bin/python prototype/eval/eval_all_variants.py > logs/eval_all_v4.log 2>&1 &
WD_PID=$!
echo "[watchdog] eval_all_v4 started PID=$WD_PID"

# wait for that one too
while pgrep -f "eval_all_variants" >/dev/null; do
    sleep 60
    N=$(ls $PROJ/prototype/eval/variant_*.jsonl 2>/dev/null | wc -l)
    echo "[watchdog] $N variants completed"
done
echo "[watchdog] all evals complete. Running analysis..."
./venv/bin/python prototype/eval/analyze_all_variants.py > logs/analyze_final.log 2>&1
echo "[watchdog] done. See paper/figures/ for outputs."
