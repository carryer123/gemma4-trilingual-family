# 5. Experiments

We report five experiment groups: (i) baseline trilingual quality on
stock Gemma 4 E2B (5.1); (ii) the LoRA-v1 vs. stock auto-judge that
motivated the framework (5.2); (iii) a 9-arm bridge-pivot ablation on
two base models (5.3); (iv) a dense step × policy-frequency grid that
attempts to localize the regression cliff (5.4); (v) honest negative
findings and what they imply for state-gated audit (5.5). All
commands and seeds are in Appendix E. Sections 5.1–5.7 report the
historical 30-probe discovery audit, whose G2 component was a 4-probe
smoke test. Section 5.8 reruns the paper-critical adapters on the
52-probe G2 script-state promotion set used by the audit trace.

## 5.1 Baseline trilingual quality on stock Gemma 4 E2B

Stock `unsloth/gemma-4-E2B-it` on the 30-probe discovery audit set: 0/30 empty
responses, 4/4 G2 script-state correct, 10/14 JSON parse OK,
mean 17.16 tok/s under deterministic decoding. The model passes all of
G2 and most of G3 out of the box.

## 5.2 The motivating observation: LoRA-v1 vs. stock

Training a LoRA on 18,043 trilingual examples (Tatoeba 6-direction +
12,408 English-pivot triples + 1,294 distilled object cards + 1,006
distilled family-scenarios + 498 function-call seeds; *no transliteration
data*) for 4,512 steps (2 epochs) produces an adapter with cleanly-
descended train loss (1.535 → 0.151) and reasonable eval loss (0.5316),
yet the auto-judge on the 30-probe set shows:

| Metric | Stock | LoRA-v1 | Δ |
|---|---|---|---|
| Empty responses | 0/30 | 0/30 | 0 |
| JSON parse OK | 10/14 | 7/14 | −3 |
| **G2 script-state correct** | **4/4** | **1/4** | **−3 (−75 pp)** |

Hand-graded examples (Appendix D):

* `phonetic_ko_to_cyr`: stock emits "Аннёнхасеё, ури аги." (Cyrillic);
  LoRA-v1 emits "안녕하세요, 우리 아기." (source-script echo).
* `phonetic_ru_to_han`: stock emits "스파시바 모이 말리쉬" (Hangul
  transliteration); LoRA-v1 emits "고마워, 내 아기." (translation, not
  transliteration).
* `phonetic_ko_to_lat`: stock emits "Jubang-eseo bap meogeoyo"; LoRA-v1
  emits "주방에서 밥 먹어요." (source-script echo).
* `phonetic_ru_to_lat`: stock emits "spasibo, moy malysh."; LoRA-v1
  emits "Благодаря, малыш." (Cyrillic + wrong word).

Adding 300 explicit transliteration training pairs (1.46% of the new
20,513-example mix) and re-training 5,130 steps with the same other
hyperparameters produces LoRA-v2, which restores **G2 only** from 1/4
to 4/4 on the same 30-probe set. It does **not** repair G3: JSON parse
remains 7/14.

The LoRA-v1 → LoRA-v2 contrast is the *existence* result for targeted
G2 repair, not a claim that the adapter becomes deployment-ready under
all gates.

## 5.3 Bridge-pivot ablation across two base models (E2B and E4B)

To test whether the LoRA-v1 regression generalizes across data-mix
composition and base-model size, we trained nine ablation arms on two
bases (Gemma 4 E2B and E4B) holding hyperparameters fixed. All E2B and
E4B short-train arms (1500 steps for the 4 main arms; 600 steps for the
5-arm policy-fraction sub-sweep) included 300 transliteration training
pairs from the v1 transliteration set, except `L_policy_00` which had 0%.

| Arm | Base | Train steps | Translit share | G2 (script) | G3 (JSON) |
|---|---|---|---|---|---|
| stock | E2B | 0 | n/a | **4/4** | 10/14 |
| L_direct | E2B | 1500 | 1.5% | 4/4 | 9/14 |
| L_pivot_only | E2B | 1500 | 1.5% | 4/4 | 9/14 |
| L_pivot_filtered | E2B | 1500 | 1.5% | 4/4 | 9/14 |
| L_multilingual | E2B | 1500 | 1.4% | 4/4 | 8/14 |
| L_policy_00 | E2B | 1500 | **0%** | **4/4** | 10/14 |
| L_policy_01 | E2B | 1500 | 0.95% | 4/4 | 9/14 |
| L_policy_03 | E2B | 600 | 1.84% | 4/4 | 10/14 |
| L_policy_05 | E2B | 600 | 1.84% | 4/4 | 10/14 |
| L_policy_10 | E2B | 600 | 1.84% | 4/4 | 10/14 |
| **lora_v1** | **E2B** | **4512** | **0%** | **1/4** | 7/14 |
| lora_v2 | E2B | 5130 | 1.46% | 4/4 | 7/14 |
| E4B_L_direct | E4B | 1500 | 1.5% | 4/4 | 11/14 |
| E4B_L_pivot_only | E4B | 1500 | 1.5% | 4/4 | 10/14 |
| E4B_L_pivot_filtered | E4B | 1500 | 1.5% | 4/4 | 9/14 |
| E4B_L_multilingual | E4B | 1500 | 1.4% | 4/4 | 10/14 |
| E4B_L_policy_00 | E4B | 1500 | 0% | 4/4 | 9/14 |
| E4B_L_policy_01 | E4B | 1500 | 0.95% | 4/4 | 10/14 |
| E4B_L_policy_03 | E4B | 600 | 1.84% | 4/4 | 10/14 |
| E4B_L_policy_05 | E4B | 600 | 1.84% | 4/4 | 9/14 |
| E4B_L_policy_10 | E4B | 600 | 1.84% | 4/4 | 10/14 |

**Findings.**

1. **G2 script-state regression is concentrated at the high-step
   long-trained arm (lora_v1)**: every other variant — including 1500-step
   0%-translit arms (L_policy_00 and E4B_L_policy_00) — passes G2 = 4/4.
2. **G3 (JSON parse) regression is consistent across long-trained
   variants**: stock 10/14 → long-trained LoRAs 7/14 (lora_v1, lora_v2)
   regardless of transliteration share. JSON discipline is a separate
   gate from script-state discipline (Proposition 2 of §6.1).
3. **Bridge-pivot itself does not cause G2 regression**: L_pivot_only,
   L_pivot_filtered, L_multilingual all pass G2 = 4/4. The pivot
   triples are not the sole cause; the long-training-with-zero-target-
   policy combination is required.
4. **E4B short-train arms show identical short-horizon behavior to E2B
   short-train arms** (G2 4/4, G3 9-11/14). We do not use these arms to
   claim cross-base long-horizon replication; they are short-horizon
   boundary checks.

## 5.4 Dense step × policy-frequency grid (cliff localization attempt)

To localize the cliff between the 1500-step short training (no
regression in any 0%-translit arm) and the 4512-step long training
(regression in lora_v1), we trained a single LoRA on a v2-style data
mix (16K base, no object cards, no scenarios; 0% transliteration) for
5000 steps with save_steps=250, retaining all 20 intermediate
checkpoints. We trained a parallel LoRA on the same base + 1.5%
transliteration share. Independently, we trained eight policy-fraction
arms at 2500 steps with translit share ∈ {0%, 0.5%, 1%, 2%, 3%, 5%, 8%,
10%}.

Result on G2 (script-state correct, /4):

**E2B step-axis at 0% transliteration share:**

```
step    250  500  750 1000 1250 1500 1750 2000 2250 2500
ckpt    4/4  4/4  4/4  3/4  4/4  4/4  3/4  3/4  3/4  3/4
                            ↑ L_policy_00 = 4/4

step   2750 3000 3250 3500 3750 4000 4250 4500 4750 5000
ckpt    4/4  3/4  4/4  3/4  3/4  3/4  4/4  4/4  4/4  4/4
                                     ↑ lora_v1 = 1/4
```

**E2B step-axis at 1.5% transliteration share** (translit data 274
examples in 16K mix):

```
step    250  500  750 1000 1250 1500 1750 2000 2250 2500
ckpt    4/4  3/4  4/4  3/4  2/4  2/4  2/4  2/4  2/4  3/4
step   2750 3000 3250 3500 3750 4000 4250 4500 4750 5000
ckpt    2/4  4/4  2/4  2/4  2/4  3/4  3/4  3/4  3/4  3/4
```

**E2B policy-fraction at 2500 steps (Track B):**

| translit share | 0% | 0.5% | 1% | 2% | 3% | 5% | 8% | 10% |
|---|---|---|---|---|---|---|---|---|
| G2 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |

**Findings — what we expected vs what we observed.**

We expected a clean step-axis cliff at f=0% (regression onset between
steps 1500 and 4500) and full preservation at f=1.5%. Neither
prediction held cleanly:

1. **The 0%-translit step-axis dense grid does not reproduce
   lora_v1's 1/4 regression at 4500–5000 steps.** Most checkpoints sit
   at 3/4 or 4/4 — a small, *noisy* dip from stock's 4/4 rather than
   the −75 pp collapse seen in lora_v1.
2. **The 1.5%-translit step-axis dense grid is *worse than expected*:
   most mid-training checkpoints sit at 2/4–3/4**, indicating that the
   transliteration data does *not* fully prevent G2 degradation in
   this data-mix composition. The 1.5% share is insufficient to hold
   G2 at 4/4 across the full step range.
3. **The 2500-step policy-fraction sweep shows no regression at any
   share** (including 0%). 2500 steps is below the regression
   threshold for this data-mix.

The most parsimonious reconciliation:
*lora_v1's −75 pp G2 regression is data-mix-specific*. The 18,043-example
mix lora_v1 trained on (which included object cards, family scenarios,
and a different translation-pair distribution) interacts with long
training to produce a sharp G2 collapse, while the 16K-example mix used
in the dense grid produces only a mild (3/4 ↔ 4/4) wobble. The
transliteration-policy frequency dimension matters less than expected;
the *composition of the dominant policy mix* matters more.

## 5.5 What this means

We had hoped to report a clean *training-duration × policy-frequency
interaction* cliff. The dense grid does not support that hypothesis in
its strong form. Instead the data support:

* **Existence (Tier 1)**: a gate-failing scalar-pass LoRA trajectory
  exists (`lora_v1` → 1/4 G2 while loss remains attractive). Recovery
  of this gate via targeted policy injection is observed in one follow-up
  run (`lora_v2` → 4/4). These are direct measurements (§5.2), not
  prevalence estimates.
* **Generalization across short-train arms**: 18 short-train E2B+E4B
  arms all pass G2 = 4/4 regardless of pivot composition or
  transliteration share (§5.3). G2 regression is absent at short
  training.
* **The cliff is *not* a single-knob phenomenon**: the dense grid (5.4)
  does not show a clean cliff in either step-axis or policy-fraction-
  axis when run on a slightly different data mix. Whatever drives the
  lora_v1 G2 collapse interacts with the *full data composition* (object
  cards + scenarios + Tatoeba mix), not with training duration or
  translit share alone.

To investigate the data-mix dependence directly, §5.6 reports an
additional 5000-step dense-step LoRA on the reconstructed `lora_v1`
data mix (~21K including object cards and scenarios, no
transliteration) with `save_steps=250`.

## 5.6 v1-data-mix dense step grid + leave-one-out isolation

To probe whether the lora_v1 collapse is a property of the data mix
(object_cards + family_scenarios + bridge-pivot triples + Tatoeba
6-direction), we ran two follow-up experiments on a 5000-step dense
step grid with `save_steps=250`:

(a) **L_v1_recreate** — reconstructed lora_v1 mix (~21K examples, 0%
transliteration), retrained from scratch with seed 20260507.

(b) **Leave-one-out isolation** — three variants each removing one
component:

| Arm | Composition | Train size |
|---|---|---|
| V1_no_cards | base + triples + scenarios + fc | 19,998 |
| V1_no_scenarios | base + triples + cards + fc | 20,286 |
| V1_no_triples | base + cards + scenarios + fc | 9,292 |

For each arm we evaluate every save-step ckpt (250–5000, Δ=250) on the
full 30-probe set.

### 5.6.1 lora_v1 cliff is not reproduced under controlled retraining

The L_v1_recreate dense step curve at 0% transliteration shows
**G2 = 4/4 at every checkpoint** from step 250 to step 5000 — including
step 4500 where lora_v1 itself sits at 1/4. The cliff that motivated
the entire framework does not reproduce when the same data mix and the
same hyperparameters are used.

| Variant | step | translit /4 | json /14 |
|---|---|---|---|
| **lora_v1** | **4512** | **1/4** | **7/14** |
| L_v1_recreate_step04500 | 4500 | 4/4 | 8/14 |
| L_v1_recreate_step04750 | 4750 | 4/4 | 7/14 |
| L_v1_recreate_step05000 | 5000 | 4/4 | 7/14 |

Two interpretations are consistent with this observation:

1. **lora_v1 may be a stochastic endpoint.** A single training run can
   land in a local minimum that fails G2 even when nearby retrainings do
   not show the same 1/4 collapse. We test this directly with the
   multi-seed and r/α sweeps in §5.7. The evidence supports
   non-reproduction of the deterministic cliff, not a population rarity
   estimate.
2. **A non-controlled covariate (data-shuffle ordering, library
   versioning, hardware nondeterminism, or a transient kernel fault)
   shifted between the original lora_v1 run and the recreate run.**
   This would still be honestly reportable but would mean the
   gate-failing scalar-pass observation rests on a footing weaker than its
   first-pass framing suggested.

We retain the lora_v1 → lora_v2 contrast as a *Tier 1 existence
claim* (§4.4): a configuration *exists* that produces a 1/4 G2 score
on the 30-probe set, and a 300-pair transliteration-policy injection
recovers G2 to 4/4 while leaving G3 at 7/14. We do **not** claim the
cliff is a property of the data mix or training duration in isolation;
the dense grids above are inconsistent with the strong form of that
claim.

**Diagnostic evidence for the stochastic-endpoint interpretation.** We
compared the LoRA delta-weights ΔW = BA of `lora_v1` against
`L_v1_recreate` (same mix, same hyperparameters, same target_modules,
same step count) layer by layer. Across 353 matched LoRA modules the
median relative Frobenius distance ‖ΔW_recreate − ΔW_v1‖_F /
‖ΔW_v1‖_F = **1.29**, with p90 = 1.49 (Fig. delta_svd_per_layer).
Two LoRA adapters trained on the same data with the same
hyperparameters land in *substantially different* regions of weight
space — consistent with the stochastic-endpoint hypothesis above, but
not proof of it. Same-state
local minima in the LoRA loss landscape are evidently far enough
apart that surface-level tasks (G2 script-state discipline) can resolve
differently between two runs.

### 5.6.2 Leave-one-out isolation: cards modestly reduce G2; scenarios + triples support G3

The three leave-one-out arms reveal a smaller, *internally consistent*
effect:

| Arm | translit /4 (median across step 1000–5000) | json /14 (final 5000) |
|---|---|---|
| L_v1_recreate (full mix) | 4/4 | 7/14 |
| V1_no_cards | **3/4** (consistent across 17/20 ckpts) | 7/14 |
| V1_no_scenarios | 4/4 | 5/14 |
| V1_no_triples | 4/4 | 5/14 |

* Removing **object_cards** drops G2 from 4/4 to a stable 3/4 across
  step 1000–5000 — a small, repeatable effect, but ~25 pp shy of the
  lora_v1 collapse depth (1/4).
* Removing **family_scenarios** or **bridge-pivot triples** has no
  detectable effect on G2 and a ~2 pp drop on G3 (7/14 → 5/14).
* No leave-one-out variant reproduces the 1/4 lora_v1 collapse.

The cards' ~25 pp G2 contribution is the strongest data-side
evidence we have for any composition-level mechanism, but it is a
mild gradient effect, not a cliff. We do not over-claim it.

## 5.7 Multi-seed and r/α capacity sweep

To probe directly whether the lora_v1 1/4 G2 collapse is reproduced
under controlled changes (§5.6.1), we ran a 12-job 4-GPU queue:

* **Multi-seed (5 arms).** Identical training pipeline to lora_v1
  (recreated v1 mix, r=32, α=64, lr=2e-4 cosine, warmup=0.03,
  bf16, AdamW-8bit, 4500 steps), with seeds
  $S \in \{42, 1234, 7777, 99999, 2026\}$.
* **LoRA-rank/α capacity sweep (7 arms).** Recreated v1 mix,
  fixed seed 20260507, $(r, \alpha) \in
  \{(8,16), (8,64), (16,32), (16,64), (64,16), (64,64), (64,128)\}$.
  Two questions: does a smaller capacity (r=8) avoid the cliff at
  this mix? does a larger capacity (r=64) trigger more cliffs?

Each arm trains for 4500 steps with `EVAL_STEPS=0` (the eval-OOM bug
encountered during the §5.6 mix-isolation run is documented in
Appendix E, §E.2). Final adapters and intermediate save_steps=1500
checkpoints are evaluated on the 30-probe discovery audit set.

**Pre-registered prediction.** If the 1/4 G2 collapse is an
unstable endpoint rather than a deterministic cliff (the §5.6 / §6.6
working hypothesis), the
expected number of seeds at G2 = 1/4 is

$$\mathbb{E}[\#\text{collapse}] \approx 5 \cdot p_{\text{collapse}} = 5 \cdot \frac{1}{162} \approx 0.03,$$

i.e. *zero* collapses are expected with high probability. Observing
0/5 leaves the outlier hypothesis intact; observing ≥1/5 promotes
the hypothesis to a genuine seed-stochastic phenomenon at
$p_{\text{collapse}} \gtrsim 0.10$. The r/α sweep is exploratory.

### 5.7.1 Result: zero cliffs across 12 controlled retrainings

**Multi-seed sweep (lora_v1 mix, r=32, α=64, 4500 steps).** All five
seeds pass G2 at 4/4. None reproduce the 1/4 collapse.

| seed | G2 (script /4) | G3 (json /14) |
|---|---|---|
| 42 | **4/4** | 8/14 |
| 1234 | **4/4** | 6/14 |
| 7777 | **4/4** | 7/14 |
| 99999 | **4/4** | 6/14 |
| 2026 | **4/4** | 10/14 |

**LoRA capacity sweep (lora_v1 mix, seed=20260507, 4500 steps).** All
seven (r, α) configurations pass G2 at 4/4. Capacity is not the
cliff's source.

| (r, α) | G2 | G3 |
|---|---|---|
| (8, 16) | **4/4** | 7/14 |
| (8, 64) | **4/4** | 7/14 |
| (16, 32) | **4/4** | 9/14 |
| (16, 64) | **4/4** | 9/14 |
| (64, 16) | **4/4** | 10/14 |
| (64, 64) | **4/4** | 7/14 |
| (64, 128) | **4/4** | 6/14 |

**Combined with §5.6.** Including `L_v1_recreate` (same mix, same
hp, dense 20-checkpoint grid, all 4/4) the cliff-non-reproduction
record is **0 cliffs in 13 controlled retrainings** (5 seeds + 7
(r, α) + 1 same-config retrain). The single 1/4 G2 outcome in the
audit atlas corresponds to the original `lora_v1` adapter
(at steps 4000 and 4512, two checkpoints of the *same* training
run). A one-sided 95% confidence upper bound on the per-config
G2=1/4 event probability is

$$p_{\text{cliff}} \le 1 - 0.05^{1/13} \approx 0.21$$

(Clopper–Pearson upper bound on a 0/13 outcome). The point estimate
is 0%, with the interval covering up to 21% — i.e. we cannot rule
out a moderate seed-stochastic phenomenon. The controlled data are
therefore inconsistent with the deterministic-cliff hypotheses we
tested (training-duration × policy frequency, and capacity-dependent
threshold), but they do not prove the phenomenon is rare.

**Implications for the paper's framing.**

(i) The controlled experiments do not reproduce the cliff. We therefore
treat the original trajectory as an **N=1 gate-failing scalar-pass observation**
and a negative result for deterministic mechanism claims, not as an
estimate of a population cliff rate.

(ii) The pre-registered §5.7 prediction (zero collapses among 5
seeds under the outlier hypothesis) is satisfied.

(iii) G3 forgetting remains a separate phenomenon: across all 12
sweep arms, G3 ranges 6–10/14, with the same mix-universal
forgetting power-law as in §6.6. Proposition 2 (independent gates)
is not affected.

(iv) The G2 = 1/4 `lora_v1` outcome remains one independent training
trajectory in a dependent audit atlas. We do not convert this into a
checkpoint-level prevalence estimate; the point is that the audit
records a selector-relevant violation that loss does not.

## 5.8 Promotion-decision audit trace

The framework's value claim is not that state-gated audit is a
calibrated detector or that it dominates scalar selectors. It is that
an adapter promotion decision should expose the behavioral state that scalar
metrics hide. We therefore trace four promotion rules over the audit
atlas:

* **S-loss.** Promote the adapter with the lowest held-out
  cross-entropy loss. (Standard practice in LoRA fine-tuning
  pipelines.)
* **S-task.** Promote the adapter with the highest BLEU on the
  held-out 1,079-example translation set (chrF as tie-breaker).
* **S-rand.** Promote the final-step (4500 / 5130) adapter of any
  fine-tuned arm. (Random in the sense that it does not consult
  any post-hoc evaluation.)
* **S-gate.** Promote any adapter that passes loss threshold AND
  strict behavioral gates on the audit protocol. For G2-52 we report
  three bands: **green** ($\ge 50/52$ and every direction $\ge 12/13$),
  **amber** ($\ge 48/52$ and every direction $\ge 10/13$), and
  **red** (anything below amber). For G3-80 we use a parallel schema
  triage: **green** ($\ge 72/80$ and every 20-probe group $\ge 18/20$),
  **amber** ($\ge 64/80$ and every group $\ge 15/20$), and **red**
  below that floor. Strict promotion requires green G2 and green G3;
  amber adapters are not deployment-ready but are distinguishable from
  red failures.

The 52-probe rerun changes the story in a useful way. It preserves the
original scalar/gate disagreement but prevents an overclaim. `lora_v1`
is still the most severe G2 failure (36/52; worst direction 6/13) and
is also RED on G3-80 (52/80; worst group 3/20), but
strict state-gated audit also rejects several controlled adapters
because G2 or the independent G3 schema gate remains unresolved. Thus
S-gate is a conservative deployment rule, not a calibrated classifier.

| Selector | Promotes lora_v1? | Reason |
|---|---|---|
| S-loss | ✓ | eval loss 0.531 (third-best of fine-tuned arms) |
| S-task | ✓ | BLEU 31.4 on held-out (within 0.6 of best) |
| S-rand | ✓ | step-4500 final adapter exists |
| **S-gate** | **✗** | G2 = 36/52 RED and G3 = 52/80 RED |

### 5.8.1 G2-52 decision-state table

We rerun the 16 paper-critical adapters (stock, `lora_v1`, `lora_v2`,
`L_v1_recreate`, five seed retrainings, and seven r/α capacity arms)
on the 52-probe G2 promotion set.

| Variant | G2-52 | Worst direction | G2 band | G3-80 | G3 band | Strict promote? |
|---|---:|---:|---:|---:|---|
| `stock` | 51/52 | 12/13 `ko->cyr` | **GREEN** | 78/80 | **GREEN** | **PASS** |
| `lora_v1` | 36/52 | 6/13 `ko->cyr` | **RED** | 52/80 | **RED** | **REJECT** |
| `lora_v2` | 52/52 | 13/13 `ko->cyr` | **GREEN** | 73/80 | **AMBER** | **REJECT** |
| `L_v1_recreate` | 49/52 | 10/13 `ko->cyr` | **AMBER** | 72/80 | **AMBER** | **REJECT** |
| `v1seed_42` | 51/52 | 12/13 `ko->cyr` | **GREEN** | 77/80 | **GREEN** | **PASS** |
| `v1seed_1234` | 52/52 | 13/13 `ko->cyr` | **GREEN** | 79/80 | **GREEN** | **PASS** |
| `v1seed_7777` | 51/52 | 12/13 `ru->han` | **GREEN** | 45/80 | **RED** | **REJECT** |
| `v1seed_99999` | 51/52 | 12/13 `ru->han` | **GREEN** | 73/80 | **AMBER** | **REJECT** |
| `v1seed_2026` | 52/52 | 13/13 `ko->cyr` | **GREEN** | 71/80 | **AMBER** | **REJECT** |
| `v1ra_r08_a16` | 52/52 | 13/13 `ko->cyr` | **GREEN** | 66/80 | **RED** | **REJECT** |
| `v1ra_r08_a64` | 48/52 | 10/13 `ru->han` | **AMBER** | 73/80 | **AMBER** | **REJECT** |
| `v1ra_r16_a32` | 51/52 | 12/13 `ru->han` | **GREEN** | 76/80 | **GREEN** | **PASS** |
| `v1ra_r16_a64` | 49/52 | 11/13 `ko->cyr` | **AMBER** | 75/80 | **AMBER** | **REJECT** |
| `v1ra_r64_a16` | 52/52 | 13/13 `ko->cyr` | **GREEN** | 68/80 | **RED** | **REJECT** |
| `v1ra_r64_a64` | 51/52 | 12/13 `ru->han` | **GREEN** | 72/80 | **RED** | **REJECT** |
| `v1ra_r64_a128` | 44/52 | 6/13 `ru->lat` | **RED** | 63/80 | **RED** | **REJECT** |

The table has two consequences. First, G2-52 supports the original
failure as a severe red-band script-state failure rather than a fragile
4-probe artifact. Second, it shows why strict promotion must be read as
triage: several otherwise plausible controls are threshold-sensitive on
G2 or blocked by the independent G3-80 schema gate. We therefore report
the promotion trace as a triage protocol and explicitly do not claim
that S-gate is calibrated.

### 5.8.2 G2 threshold sensitivity

Because the G2 bands are deployment thresholds rather than calibrated
statistical cutoffs, we report how the 16-adapter subset changes under
three plausible script-state rules.

| Rule | G2 criterion | G2-pass variants | G2+G3-80 GREEN variants | Always-rejected examples |
|---|---|---:|---:|---|
| Relaxed G2 | total ≥48/52 and every direction ≥10/13 | 14/16 | 4/16 | `lora_v1`, `v1ra_r64_a128` |
| Current green G2 | total ≥50/52 and every direction ≥12/13 | 11/16 | 4/16 | `L_v1_recreate`, `lora_v1`, `v1ra_r64_a128` |
| Perfect G2 | total ≥52/52 and every direction ≥13/13 | 5/16 | 1/16 | `L_v1_recreate`, `lora_v1`, `v1ra_r64_a128` |

| Variant | 48/52 + dir≥10 | 50/52 + dir≥12 | 52/52 + dir=13 | G3-80 | Interpretation |
|---|---:|---:|---:|---:|---|
| `stock` | PASS | PASS | FAIL | 78/80 GREEN | stable positive control |
| `lora_v1` | FAIL | FAIL | FAIL | 52/80 RED | rejected under every G2 cutoff and G3-80 |
| `lora_v2` | PASS | PASS | PASS | 73/80 AMBER | G2-clean but still schema-review |
| `L_v1_recreate` | PASS | FAIL | FAIL | 72/80 AMBER | threshold-sensitive G2 and G3 boundary case |
| `v1ra_r64_a128` | FAIL | FAIL | FAIL | 63/80 RED | rejected under every G2 cutoff and G3-80 |
| `v1ra_r16_a64` | PASS | FAIL | FAIL | 75/80 AMBER | relaxed-only G2 boundary case |
| `v1seed_42` | PASS | PASS | FAIL | 77/80 GREEN | passes current G2 and G3-80 |
| `v1seed_2026` | PASS | PASS | PASS | 71/80 AMBER | perfect G2 but schema-review |

This sensitivity check supports two claims only: `lora_v1` is not an
artifact of the current 50/52 cutoff, and several controls are
threshold-sensitive or blocked by the independent G3-80 gate. It does not
calibrate G2 precision or recall.

### 5.8.3 What the triage states trigger

The protocol is operational: each state causes a different promotion
pipeline action rather than merely changing a table label.

| Adapter | Audit state | Triggered action | Why |
|---|---|---|---|
| `stock` | GREEN | Eligible baseline; log raw generations and gate version | G2=51/52, G3=78/80 |
| `lora_v1` | RED | Block promotion; rollback or retrain with targeted script-state/schema repair | G2=36/52 and G3=52/80 |
| `lora_v2` | GREEN on G2, AMBER on G3 | Hold deployment; inspect JSON failures, add schema-repair slice or constrained decoding, rerun G3 | G2=52/52 but G3=73/80 |
| `L_v1_recreate` | AMBER on G2 and G3 | Human review of raw outputs; targeted repair or scoped waiver; rerun G2 and G3 | G2=49/52; G3=72/80 |
| `v1ra_r64_a128` | RED | Block promotion; do not treat as a boundary case | G2=44/52 and G3=63/80 |

For automatic gates the review loop is intentionally small: inspect the
raw failed generations, assign an error label (source-script echo,
wrong target script, mixed script, malformed JSON, missing key, enum
violation), add a targeted repair slice or declare a waiver, and rerun
only the failed gates before the adapter can move from AMBER to GREEN.
RED states skip the waiver-first path because they are materially below
the deployment threshold: they cannot be waived unless the deployment
specification itself changes and the full audit is rerun.

We caveat the promotion-decision audit trace.

(i) Disagreement is observed in a small, dependent atlas. We have not
estimated a population false-positive rate (S-gate rejects a good
adapter) or a population false-negative rate.

(ii) The observed scalar/gate disagreement is on a single
deployment-critical gate (script state). Other selectors that
incorporate even a small targeted-policy spot check would also catch
this case.

(iii) The audit cost is non-trivial: 132 automatic probes under
deterministic decode take minutes per adapter on the A100 evaluation
node. For pipelines training hundreds of arms this becomes additional
batch compute, not free.

The point is not that S-gate is the right selector for every deployment,
but that it names the behavioral debts that scalar selectors ignore.
Whether those debts should block deployment, trigger retraining, or
enter a human review queue is a deployment-policy choice; this paper
provides the audit state needed to make that choice explicit.

## 5.9 Distillation throughput (systems result)

For completeness: the synthetic-data pipeline (§3.4) achieves 0.87
cards/s with `think:False` + 4-port round-robin Ollama on 4× A100, vs.
0.04 cards/s on a single Ollama instance with thinking enabled — a 22×
speedup attributable almost entirely to the `think:False` setting.
This is a reproducibility note for practitioners running the pipeline
on Gemma 4 E4B/26B distillation, not a contribution claim.
