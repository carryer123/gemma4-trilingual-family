#!/bin/bash
# Auto-pipeline: when object distill finishes, kick off scenario distill.
set -euo pipefail

cd /PATH/REDACTED

echo "[wait] for object distill to finish..."
while pgrep -f "04_run_synth_via_ollama" >/dev/null; do
  sleep 30
  N_OK=$(wc -l < prototype/data/raw/object_cards.jsonl 2>/dev/null || echo 0)
  N_FAIL=$(wc -l < prototype/data/raw/object_cards_failed.jsonl 2>/dev/null || echo 0)
  echo "  [obj] ok=$N_OK fail=$N_FAIL"
done

echo "[next] kick off scenario distill"
nohup env MODEL=gemma4:e4b TARGET=scenario PARALLEL=8 ./venv/bin/python prototype/data/04_run_synth_via_ollama.py > logs/distill_scen_e4b.log 2>&1 &
SCEN_PID=$!
echo "[scen] PID=$SCEN_PID"

while pgrep -f "04_run_synth_via_ollama" >/dev/null; do
  sleep 60
  N_OK=$(wc -l < prototype/data/raw/family_scenarios.jsonl 2>/dev/null || echo 0)
  N_FAIL=$(wc -l < prototype/data/raw/family_scenarios_failed.jsonl 2>/dev/null || echo 0)
  echo "  [scen] ok=$N_OK fail=$N_FAIL"
done

echo "[merge] re-running merge with synth data filled"
./venv/bin/python prototype/data/10_merge_train_jsonl.py
echo "[done] full distill pipeline complete"
