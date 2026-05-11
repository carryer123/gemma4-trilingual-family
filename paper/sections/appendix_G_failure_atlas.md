# Appendix G — Audit Atlas (176 evaluated artifacts)

This atlas catalogs every fine-tuned artifact in the public LoRA tree
(`lora_out/`) by its discovery-audit outcome. Each row corresponds to a
directly evaluated adapter or intermediate checkpoint, not an iid sample
from a population. The atlas combines the historical discovery artifacts
with the multi-seed and r/α controlled retraining sweep. The variants are
grouped by the dominant failure they
exhibit at the §4-defined gates G2 (script-state correct) and
G3 (JSON parse OK, /14). The atlas exists to make the *claim boundary*
of this paper explicit: we report which configurations land in which
failure mode, and which configurations do not reproduce a previously
claimed failure.

We preserve negative results to support the claim boundary, rather than
pruning them.

## Coverage

| metric | count |
|---|---|
| Total variants evaluated | **176** |
| Stock-baseline (E2B, no fine-tuning) | 1 |
| Fine-tuned final adapters (E2B + E4B) | 36 |
| Intermediate step-axis checkpoints | 139 |
| of which: multi-seed sweep arms | 5 |
| of which: r/α capacity sweep arms | 7 |

## G2 outcome distribution

| G2 score | # artifacts |
|---|---:|
| 4/4 (no script-state regression) | 125 |
| 3/4 (mild) | 36 |
| 2/4 (moderate) | 13 |
| 1/4 (the lora_v1 observation) | **2** |
| 0/4 | 0 |

The 1/4 collapse is observed in only two variants (`lora_v1` at
step 4512 and `lora_v1_step4000`), which are two checkpoints of the
*same* training run. No other variant — across 4 training mixes,
2 base models, 9-arm bridge-pivot ablation, 8-fraction policy sweep,
20-step dense grid at 0% transliteration share, 20-step dense grid
at 1.5% transliteration share, 4-arm leave-one-out mix isolation,
**5-seed sweep, and 7-config LoRA r/α capacity sweep** — reproduces
the 1/4 score. The G2=1/4 observation is therefore one independent
training trajectory in this dataset.

### G2 = 1/4 cliff non-reproduction

| Controlled retraining | Same mix? | Same hp? | n | G2 = 1/4 observed? |
|---|---|---|---|---|
| L_v1_recreate (dense step grid) | ✓ | ✓ | 1 (× 20 ckpts) | 0/20 |
| Multi-seed sweep | ✓ | ✓ except seed | 5 | 0/5 |
| r/α capacity sweep | ✓ | ✓ except (r, α) | 7 | 0/7 |
| **Total** | | | **13** | **0/13** |

The one-sided Clopper–Pearson 95% upper bound on the G2=1/4 event probability per
controlled config is $1 - 0.05^{1/13} \approx 0.21$.

### 52-probe G2 promotion subset

The 16 paper-critical adapters were rerun on the stricter 52-probe G2
promotion set. This rerun confirms that `lora_v1` is not merely a
4-probe artifact: it is the worst G2 state in the selector subset
(36/52; worst direction 6/13). It also shows why the result should be
reported as triage rather than as a clean binary detector: some
controlled adapters are amber, and `v1ra_r64_a128` is red under the
expanded script-state check.

| Band | Rule | Variants |
|---|---|---|
| Green | total ≥50/52 and every direction ≥12/13 | `stock`, `lora_v2`, `v1seed_42`, `v1seed_1234`, `v1seed_7777`, `v1seed_99999`, `v1seed_2026`, `v1ra_r08_a16`, `v1ra_r16_a32`, `v1ra_r64_a16`, `v1ra_r64_a64` |
| Amber | total ≥48/52 and every direction ≥10/13 | `L_v1_recreate`, `v1ra_r08_a64`, `v1ra_r16_a64` |
| Red | below amber floor | `lora_v1`, `v1ra_r64_a128` |

## Failure-mode categories

### F1 — The 1/4 G2 collapse (lora_v1 only)

* **Variants**: `lora_v1` (4512 steps), `lora_v1_step4000`.
* **Configuration**: trilingual mix v1 (~18K examples; Tatoeba
  6-direction + 12,408 English-pivot triples + 1,294 distilled
  object cards + 1,006 family scenarios + 498 function-call seeds;
  no transliteration), Gemma 4 E2B base, r=32 α=64,
  warmup=0.03, lr=2e-4 cosine, bf16, AdamW-8bit, seed=20260507.
* **Recovery**: adding 300 transliteration training pairs (1.46%
  of mix) and retraining (lora_v2) repairs G2 only (4/4 on the
  discovery set; 52/52 on G2-52) and remains AMBER on the expanded
  G3-80 schema audit (73/80). The recovery is gate-specific.
* **Status**: *not reproduced* under same-mix-same-hyperparameter
  retraining (`L_v1_recreate`, all 20 dense ckpts: 4/4). Two
  matched-state LoRA adapters trained on the same data with
  identical hyperparameters land in regions of weight space whose
  median per-layer relative ΔW Frobenius distance is 1.29 (§5.6.1).
  We treat F1 as a *Tier-1 existence observation* (a configuration
  exists that produces 1/4 G2; injection at 1.46% recovers G2 to 4/4),
  not as a Tier-2 reproducible cliff.

### F2 — Mid-step G2 wobble at 1.5% transliteration share

* **Variants**: `L_step_dense_p1_5_step01250..03750` (9 ckpts at
  G2 = 2/4), plus `L_step_dense_p1_5_step02500/04500..05000` at
  3/4.
* **Configuration**: 16K mix without object_cards / family_scenarios,
  274 transliteration pairs (1.5% share), 5000-step dense grid,
  E2B.
* **Failure mode**: G2 *partially regresses* in the mid-training
  region (steps 1250–3750) with the very policy injection that
  prevented F1 in lora_v2. Final-step recovery (3/4 at step 5000)
  is incomplete.
* **Implication**: 1.5% transliteration is *insufficient* to hold
  G2 at 4/4 when the dominant data composition lacks
  object_cards + family_scenarios; the 4/4 G2 of lora_v2 (which
  contained the cards + scenarios) and the *partial* 3/4 G2 of
  L_step_dense_p1_5 (which did not) together demonstrate that the
  cards/scenarios mass interacts with the protective effect of
  the transliteration injection.

### F3 — Cards-removal mild G2 reduction

* **Variants**: `V1_no_cards_step01000..05000` (consistent 3/4
  across step 1000–5000).
* **Configuration**: lora_v1 mix minus the 1,294 object_cards;
  19,998 examples, 5000-step dense grid, E2B, no transliteration.
* **Failure mode**: G2 = 3/4 at all post-warmup ckpts. A small,
  *internally consistent* 25 pp G2 reduction. Does not reach the
  1/4 lora_v1 collapse depth.
* **Implication**: object_cards contribute a small protective
  effect on G2 but cannot fully account for F1.

### F4 — JSON-parse (G3) reduction in long-trained variants

* **Variants**: most ≥4500-step LoRAs lose 2–5 G3 points relative
  to the 10/14 stock baseline (e.g., `lora_v1` 7/14, `lora_v2`
  7/14, `V1_no_scenarios_step05000` 5/14, `V1_no_triples_step05000`
  5/14).
* **Failure mode**: persistent G3 reduction across long-trained
  variants, *independent of* the transliteration share.
* **Implication**: G3 (JSON discipline) is a *separate gate* from
  G2 (script discipline). It admits a different recovery
  strategy (e.g., constrained generation or schema-guided
  decoding), and it is consistent with Proposition 2 (gates are
  not recoverable through a shared knob).

### F5 — Empty / refusal failures

* **Variants**: none observed across the discovery atlas.
* **Implication**: Gemma 4 E2B/E4B + LoRA does not produce empty
  or refusal-flavored failures on the 30-probe set; the gates
  that bind in this regime are G2 and G3, not G1 or G6.

## What this atlas does not contain

* The 176-artifact counts use the historical 30-probe discovery audit.
  The stricter 52-probe G2 rerun is available for the 16 paper-critical
  selector adapters, not for all 176 artifacts.
* We do not catalog cross-base-model results (Llama / Qwen) — the
  cross-model replication is future work (§7).

## How to read this atlas relative to the main claim

The main contribution of this paper is the **state-gated audit
workflow + gate suite + claim-tier discipline** (§3, §4). The
atlas exists to keep the framework honest: a methodology paper that
surveys how the available LoRA artifacts score on its own gates is more
credible than one that selects only a convenient subset.
F1 (lora_v1 1/4) demonstrates the *existence* of a configuration
which a validation-loss-only pipeline would have promoted (eval loss
0.53, train loss 0.15) while breaking G2 — the gate-failing
scalar-pass case the workflow is designed to surface before deployment.

This remains a Tier-1 selector disagreement, not a prevalence claim.
The atlas shows that a gate can reject a loss-attractive gate-failing
trajectory; it does not show how often such trajectories occur in the
population.
