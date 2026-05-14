#!/bin/bash
# 4-GPU parallel G3-80 JSON/schema evaluation.
set -u

PROJ=/PATH/REDACTED
cd "$PROJ" || exit 1
source venv/bin/activate

mkdir -p logs paper/figures

nohup env CUDA_VISIBLE_DEVICES=0 \
    G3EXT_OUT_FILE=$PROJ/paper/figures/g3_extended_scores_g0.json \
    VARIANTS_FILTER="stock,lora_v1,lora_v2,L_v1_recreate" \
    python -u prototype/eval/eval_g3_extended.py > logs/g3ext_g0.log 2>&1 &
P0=$!

nohup env CUDA_VISIBLE_DEVICES=1 \
    G3EXT_OUT_FILE=$PROJ/paper/figures/g3_extended_scores_g1.json \
    VARIANTS_FILTER="v1seed_42,v1seed_1234,v1seed_7777" \
    python -u prototype/eval/eval_g3_extended.py > logs/g3ext_g1.log 2>&1 &
P1=$!

nohup env CUDA_VISIBLE_DEVICES=2 \
    G3EXT_OUT_FILE=$PROJ/paper/figures/g3_extended_scores_g2.json \
    VARIANTS_FILTER="v1seed_99999,v1seed_2026,v1ra_r08_a16,v1ra_r08_a64" \
    python -u prototype/eval/eval_g3_extended.py > logs/g3ext_g2.log 2>&1 &
P2=$!

nohup env CUDA_VISIBLE_DEVICES=3 \
    G3EXT_OUT_FILE=$PROJ/paper/figures/g3_extended_scores_g3.json \
    VARIANTS_FILTER="v1ra_r16_a32,v1ra_r16_a64,v1ra_r64_a16,v1ra_r64_a64,v1ra_r64_a128" \
    python -u prototype/eval/eval_g3_extended.py > logs/g3ext_g3.log 2>&1 &
P3=$!

echo "[g3ext] launched pids: $P0 $P1 $P2 $P3"
wait $P0 $P1 $P2 $P3
echo "[g3ext] all 4 GPUs done"

python - <<'PY'
import json, pathlib
p = pathlib.Path('paper/figures')
merged = {'variants': {}}
for f in sorted(p.glob('g3_extended_scores_g*.json')):
    d = json.loads(f.read_text())
    merged['variants'].update(d.get('variants', {}))
out = p / 'g3_extended_scores.json'
out.write_text(json.dumps(merged, indent=2, ensure_ascii=False))
print(f'[merge] {len(merged["variants"])} variants -> {out}')
for name, row in sorted(merged['variants'].items()):
    print(f'  {name:30s} G3={row["g3_score"]:>2}/{row["g3_total"]} ({row["g3_pass_rate"]:.1%})')
PY

python prototype/eval/summarize_g3_extended.py
python prototype/eval/build_selector_audit_trace.py
