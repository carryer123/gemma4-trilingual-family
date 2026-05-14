#!/bin/bash
# 4-GPU parallel: each GPU handles a subset of the 16 paper-critical variants.
# G2 extended (52 probes, ko-cyr/ru-han/ko-lat/ru-lat × 13 each).
set -u
PROJ=/PATH/REDACTED
cd "$PROJ"
source venv/bin/activate

mkdir -p logs

# Bucket assignments (ensure each subprocess writes to a different output)
# We write to a per-GPU JSON, then merge at the end.
nohup env CUDA_VISIBLE_DEVICES=0 \
    PYTHONUNBUFFERED=1 \
    G2EXT_OUT_FILE=$PROJ/paper/figures/g2_extended_scores_g0.json \
    VARIANTS_FILTER="stock,lora_v1,lora_v2,L_v1_recreate" \
    ./venv/bin/python prototype/eval/eval_g2_extended.py > logs/g2ext_g0.log 2>&1 &
P0=$!
nohup env CUDA_VISIBLE_DEVICES=1 \
    PYTHONUNBUFFERED=1 \
    G2EXT_OUT_FILE=$PROJ/paper/figures/g2_extended_scores_g1.json \
    VARIANTS_FILTER="v1seed_42,v1seed_1234,v1seed_7777" \
    ./venv/bin/python prototype/eval/eval_g2_extended.py > logs/g2ext_g1.log 2>&1 &
P1=$!
nohup env CUDA_VISIBLE_DEVICES=2 \
    PYTHONUNBUFFERED=1 \
    G2EXT_OUT_FILE=$PROJ/paper/figures/g2_extended_scores_g2.json \
    VARIANTS_FILTER="v1seed_99999,v1seed_2026,v1ra_r08_a16,v1ra_r08_a64" \
    ./venv/bin/python prototype/eval/eval_g2_extended.py > logs/g2ext_g2.log 2>&1 &
P2=$!
nohup env CUDA_VISIBLE_DEVICES=3 \
    PYTHONUNBUFFERED=1 \
    G2EXT_OUT_FILE=$PROJ/paper/figures/g2_extended_scores_g3.json \
    VARIANTS_FILTER="v1ra_r16_a32,v1ra_r16_a64,v1ra_r64_a16,v1ra_r64_a64,v1ra_r64_a128" \
    ./venv/bin/python prototype/eval/eval_g2_extended.py > logs/g2ext_g3.log 2>&1 &
P3=$!

echo "[g2ext] launched pids: $P0 $P1 $P2 $P3"
wait $P0 $P1 $P2 $P3
echo "[g2ext] all 4 GPUs done"

# Merge per-GPU JSONs
./venv/bin/python -c "
import json, pathlib
p = pathlib.Path('paper/figures')
merged = {'variants': {}}
for f in sorted(p.glob('g2_extended_scores_g*.json')):
    d = json.loads(f.read_text())
    for k, v in d.get('variants', {}).items():
        merged['variants'][k] = v
out = p / 'g2_extended_scores.json'
out.write_text(json.dumps(merged, indent=2, ensure_ascii=False))
print(f'[merge] {len(merged[\"variants\"])} variants -> {out}')
for n, r in sorted(merged['variants'].items()):
    print(f'  {n:30s} G2={r[\"g2_score\"]:>2}/{r[\"g2_total\"]} ({r[\"g2_pass_rate\"]:.1%})')
"
