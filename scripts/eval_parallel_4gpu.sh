#!/bin/bash
# Parallel evaluation across 4 GPUs.
# Splits the variant list 4 ways and runs eval_all_variants.py simultaneously
# with VARIANTS_FILTER to partition work.
#
# Run when ALL training is done. Prerequisites:
#  - Track A v2 done (lora_out/L_step_dense_p*/adapter exists OR you don't need final)
#  - Track B done (lora_out/L_pf_*/adapter for all 8)
#  - E4B done (lora_out/E4B_*/adapter for all 9)
#
# Skip-logic in eval_all_variants.py prevents re-evaluation.
set -u

PROJ=/scratch/hpc198a01/젬마4해커톤
cd "$PROJ"
source venv/bin/activate

# Wait until ALL training procs are gone
echo "[wait] for all training to finish..."
while pgrep -f "lora_ablation_runner" >/dev/null; do
    sleep 60
    N=$(pgrep -f lora_ablation_runner | wc -l)
    echo "  [eval-wait] $N training procs still alive"
done
echo "[ok] all training done. Launching parallel eval."

# Use VARIANTS_FILTER to split work; each GPU handles a disjoint subset
# Partition 1: stock + E4B variants (GPU 0)
# Partition 2: L_step_dense_p0 + L_pf (GPU 1)
# Partition 3: L_step_dense_p1_5 + L_direct/pivot/multilingual (GPU 2)
# Partition 4: L_policy_* + lora_v1/v2 + remaining (GPU 3)

# Simpler: filter by name substring per GPU
nohup env CUDA_VISIBLE_DEVICES=0 ONLY_NEW=1 VARIANTS_INCLUDE_CHECKPOINTS=0 \
    VARIANTS_FILTER=E4B_ \
    ./venv/bin/python prototype/eval/eval_all_variants.py > logs/eval_g0_e4b.log 2>&1 &
echo "[launch] GPU 0: E4B variants"

nohup env CUDA_VISIBLE_DEVICES=1 ONLY_NEW=1 VARIANTS_INCLUDE_CHECKPOINTS=1 \
    VARIANTS_FILTER=L_step_dense_p0 \
    ./venv/bin/python prototype/eval/eval_all_variants.py > logs/eval_g1_step0.log 2>&1 &
echo "[launch] GPU 1: L_step_dense_p0 + checkpoints"

nohup env CUDA_VISIBLE_DEVICES=2 ONLY_NEW=1 VARIANTS_INCLUDE_CHECKPOINTS=1 \
    VARIANTS_FILTER=L_step_dense_p1_5 \
    ./venv/bin/python prototype/eval/eval_all_variants.py > logs/eval_g2_step15.log 2>&1 &
echo "[launch] GPU 2: L_step_dense_p1_5 + checkpoints"

nohup env CUDA_VISIBLE_DEVICES=3 ONLY_NEW=1 VARIANTS_INCLUDE_CHECKPOINTS=0 \
    VARIANTS_FILTER=L_pf_ \
    ./venv/bin/python prototype/eval/eval_all_variants.py > logs/eval_g3_pf.log 2>&1 &
echo "[launch] GPU 3: L_pf fractions"

wait
echo "[done] parallel eval complete. Running analysis..."
./venv/bin/python prototype/eval/analyze_all_variants.py > logs/analyze_final.log 2>&1
echo "[done] analysis written to paper/figures/"
