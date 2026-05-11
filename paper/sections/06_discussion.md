# 6. Discussion

## 6.1 Three propositions

We formalize the empirical findings of §5 as three propositions about
LoRA fine-tuning under a state-gated audit rule.

**Proposition 1 (loss does not certify state).** *Let $\mathcal{V}$ be
any finite held-out validation set and let $\ell(L; \mathcal{V})$ be the
cross-entropy loss of an adapter $L$ on $\mathcal{V}$. There exist two
adapters $L_1, L_2$ such that $\ell(L_1; \mathcal{V}) =
\ell(L_2; \mathcal{V})$ and yet for at least one behavioral gate $G_k$,
$G_k(L_1) \neq G_k(L_2)$.*

*Proof sketch.* A finite validation set has positive measure of
behavioral surface uncovered. Any policy whose effect is concentrated
in that uncovered region — for example, cross-script state discipline on
prompts the validation set does not contain — can have arbitrarily
different gate scores while contributing zero measure to the loss
sum. Specifically, in §5.2 we construct two adapters
(LoRA-v1 at step 4000 vs. L_policy_00 at step 1500) whose validation
losses agree to within bf16 noise yet whose G2 scores are 1/4 vs. 4/4.
$\square$

**Proposition 2 (gates are non-redundant in the audit atlas).** *On our
16-adapter selector subset and the wider atlas, multiple gates disagree
under the same scalar training trajectory; passing one gate does not
certify another.*

*Empirical evidence.* The L_pivot_only arm passes G1 (translation,
1500 steps, bridge-pivot data), agrees with stock on G2 (4/4) and G6/G7/G8,
yet drops G3 from 10/14 to 9/14. The lora_v1 long-trained arm passes G1
and agrees with stock on G6/G7/G8 yet drops G2 from 4/4 to 1/4 and G3
to 7/14. The L_multilingual arm agrees on G2 (4/4) yet drops G3 to 8/14
because of cross-direction trade-offs. Each pair isolates a distinct
gate as the sole disagreement axis. The full pairwise non-redundancy
table is in Appendix D. We do not claim exhaustive pairwise separation
for all eight gates.
$\square$

**Proposition 3 (repair is a Pareto problem).** *Targeted policy
augmentation improves the targeted gate but does not Pareto-dominate
all other gates simultaneously.*

*Empirical evidence.* Adding 300 transliteration training pairs
(LoRA-v2 vs. LoRA-v1) repairs G2 only (1/4 to 4/4) and does not improve
G3 (still 7/14), so LoRA-v2 repairs one gate while remaining
non-deployable under strict promotion. Conversely, the L_pivot_filtered arm raises G1
translation BLEU but does not move G2 above stock. The repair frontier
is Pareto-shaped, not pruning-shaped: a single-term loss objective
cannot move all eight gates simultaneously, and gate weighting must be
declared before training. Concretely, our ablation traces the frontier:
short training preserves all gates at the cost of less-trained
target-task accuracy; long training improves target accuracy at the
cost of dropped under-represented gates; targeted augmentation raises
the augmented gate without changing the others.
$\square$

## 6.2 What LoRA actually learned

The auto-judge results (§5) and the failure-mode catalog (Appendix D)
together produce a diagnosis that is more specific than "LoRA forgets":
LoRA can preserve high-frequency task performance while changing
low-frequency deployment policies. In this atlas, the original
`lora_v1` trajectory is the only run that collapses G2 to 1/4; the
same mix, seed-resampled variants, and capacity variants do not
reproduce it. The safest interpretation is therefore not a deterministic
forgetting law, but an unstable endpoint that scalar loss did not screen
out. The 52-probe rerun further shows that controlled adapters can carry
amber or red gate debt even when they avoid the original 1/4 collapse.
This is consistent with the forgetting-scaling-law result of
[kalajdzievski-scaling-law, biderman-lora-forgets] which reports
forgetting as a power law in update steps and trainable parameters; our
specific contribution is the *gate-level disaggregation* — most gates
are unaffected in most arms, while the selector-relevant regression is
concentrated in an explicit low-frequency policy gate.

The practical rule that follows is: *enumerate the deployment gates and
audit them before promotion*. Our data are not strong enough to infer a
universal minimum training share $f^*$ for transliteration.

## 6.3 The repair frontier and negative ablations

Several arms of the ablation are *negative* — they expose Pareto
trade-offs rather than monotone improvements.

* **L_pivot_only** improves G1 BLEU symmetry but does not move G2 vs
  stock; pivot data alone has no effect on script-state discipline.
* **L_pivot_filtered** with a length-similarity heuristic shrinks the
  pivot pool by 78% and matches L_pivot_only on G1 — the heuristic
  filter does not pay for itself in this case study, suggesting a
  better filter (e.g., round-trip semantic similarity via mBERT
  cosine) is required.
* **L_multilingual** combining KO+RU+EN, KO+VI+EN, KO+ZH+EN data
  matches single-triple G1 BLEU but drops G3 (8/14 vs. 9/14) — the
  additional triples introduce mild schema-discipline interference.
* **L_policy_{00,01,03,05,10}** at 1500 steps all pass G2 = 4/4
  regardless of transliteration share; the policy-frequency cliff is
  not visible at the short horizon we tested. Long-horizon policy
  sweeps remain future work.

We report these arms because they constrain the conclusion: the
transliteration regression is *not* a single-knob (data-share) effect
visible at any training duration, and our controlled retrainings do not
support a deterministic interaction law.

## 6.4 Limitations (honest)

* **N=1 family**: this paper supports Tier 1 (existence) only. Tier 2
  requires $N \ge 10$ households (Phase 4 future work).
* **Single base model**: the selector subset uses Gemma 4 E2B as the base.
  Cross-base-model replication on Llama 3.2 / Qwen 2.5 is Phase 1 of the
  follow-up program.
* **Pivot filter is a heuristic**: length-similarity is a coarse proxy
  for round-trip semantic equivalence; a learned filter is overdue.
* **Auto-judge metrics are surface**: G2 measures dominant Unicode block
  but does not check phonetic accuracy; G3 measures JSON parse but does
  not measure semantic correctness of the structured payload. The
  expanded G2-52 result should therefore be read as script-state
  triage, not transliteration-quality certification.
* **Step-axis grid is sparse**: we have step-axis evaluation at
  {1500, 4000, 4500, 4512, 5000, 5130}; the regression onset between
  1500 and 4000 is not resolved.
* **Probe set v1 is KO-anchored**: the 30 v1 probes were authored from
  a KO-L1 reference frame; localizations to other triples are released
  as a forkable template in `tools/fae_protocol/`.

## 6.5 Scope of the analogy

The broader observable-vs-state analogy is useful for motivation, but it
is not evidence in this paper. The empirical claim here is NLP-specific:
a trilingual LoRA audit found one loss-attractive trajectory that failed
a deployment gate and was not reproduced in controlled retraining.
Appendix C is retained only as optional context.

## 6.6 Forgetting power-law fit (Proposition 4)

Following Kalajdzievski (2024)'s scaling-laws-for-forgetting framing,
we fit a per-mix power law

$$P_{\text{pass}}(t) \approx P_{\text{pass}}(0) - \alpha \cdot (t / 1000)^{\beta}$$

to the dense step grids of §5.4 and §5.6, where $t$ is training step,
$P_{\text{pass}}$ is the audit score on a gate (G2 / 4 or G3 / 14), and
$(\alpha, \beta)$ are mix-dependent. Fits use bounded least squares
with $\alpha \in [0, P_0]$ and $\beta \in [0.05, 2.0]$.

| Mix | Gate | $\alpha$ | $\beta$ | RMSE |
|---|---|---|---|---|
| L_step_dense_p0 (16K, 0%) | G2 | 0.878 | 0.104 | 0.49 |
| L_step_dense_p1_5 (16K, 1.5%) | G2 | **1.621** | 0.138 | 0.68 |
| L_v1_recreate (v1 mix) | G2 | **0.000** | 0.050 | 0.00 |
| V1_no_cards | G2 | 0.933 | 0.355 | 0.30 |
| V1_no_scenarios | G2 | 0.582 | 0.050 | 0.31 |
| V1_no_triples | G2 | 0.000 | 0.050 | 0.00 |
| L_step_dense_p0 | G3 | 6.224 | 0.078 | 1.46 |
| L_step_dense_p1_5 | G3 | 5.949 | 0.162 | 0.90 |
| L_v1_recreate | G3 | 5.911 | 0.050 | 0.92 |
| V1_no_cards | G3 | 4.282 | 0.094 | 1.41 |
| V1_no_scenarios | G3 | 6.992 | 0.234 | 0.98 |
| V1_no_triples | G3 | 5.109 | 0.448 | 1.44 |

Three observations:

1. **G2 forgetting is mix-specific.** $\alpha_{G2}$ varies from 0.000
   (L_v1_recreate, V1_no_triples — no detectable G2 forgetting at
   any step) to 1.621 (L_step_dense_p1_5 — 1.5% transliteration
   share, the *strongest* G2 forgetting). The mix that contains the
   intended protective policy (transliteration) but lacks the cards
   + scenarios fits the *largest* forgetting coefficient — consistent
   with §5.4: a small protective injection without the right
   surrounding mass is not enough.
2. **L_v1_recreate fits $\alpha_{G2} = 0$ exactly.** The lora_v1 mix,
   when retrained from scratch, exhibits *no* G2 forgetting at any
   measured step. This is direct quantitative reinforcement of the
   stochastic-endpoint interpretation of §5.6: under the per-mix
   forgetting law, the lora_v1 mix should *not* produce a 1/4 G2
   collapse. The collapse is therefore not a mix-level expectation
   but a sampling outlier on the loss-landscape side.
3. **G3 forgetting is universal.** $\alpha_{G3} \in [4.3, 7.0]$ on
   all six mixes. JSON-parse discipline degrades regardless of
   transliteration share or composition. This supports Proposition 2
   (gates are independent / not recoverable through a shared knob)
   and identifies G3 as a target for a *separate* recovery strategy —
   schema-guided decoding or constrained generation, not data-mix
   tuning.

The fits are reported with their RMSE as a transparency measure. We
do not use them for prediction outside the measured step range.

## 6.7 What this work is and is not

It *is*: a trilingual LoRA audit case study, with a reusable gate
template, a 16-adapter selector subset from a dependent 176-artifact
audit atlas, and a conservative protocol for niche-population adapter
evaluation released under CC-BY 4.0.

It *is not*: a new model architecture, a new fine-tuning algorithm, a
generic multilingual LoRA evaluation suite, a clinical study of family-
language-acquisition outcomes, or a population-level claim. We make no
N>1 statistical claim.
