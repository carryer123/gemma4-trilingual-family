# State-Gated Audit for Niche-Population LoRA Fine-Tuning: A Trilingual Case Study

## Abstract

Held-out loss and task metrics are useful for selecting LoRA adapters, but
they do not certify deployment-specific behavior. We present a trilingual
KO/RU/EN case study in which a loss-attractive Gemma 4 E2B LoRA adapter
failed a deployment-critical cross-script gate while scalar metrics remained
acceptable. The finding is deliberately narrow: the failure occurs in one
historical training trajectory and is not reproduced in 13 controlled
retrainings. We therefore do not claim a reproducible cliff law, a calibrated
detector, or a population failure rate.

The contribution is a conservative **state-gated audit** workflow for
niche-population adapter promotion. The workflow names deployment gates,
records raw generations, separates GREEN/AMBER/RED audit states, and maps
those states to actions: GREEN logs and admits, AMBER triggers documented
repair or scoped waiver plus failed-gate rerun, and RED blocks promotion
unless the deployment specification changes and the full audit is rerun. In
our audit atlas of 176 dependent artifacts, the original trajectory remains
the most severe G2 script-state failure under an expanded 52-probe rerun
(36/52; worst direction 6/13) and is also RED under an expanded 80-probe
G3 schema audit (52/80). Several controls are threshold-sensitive or blocked
by independent G2/G3 debt. This is an audit case study, not a benchmark.

## 1 Introduction

LoRA fine-tuning pipelines commonly promote adapters by validation loss,
BLEU, chrF, or a small task-specific metric set. Those signals are necessary
but incomplete when deployment depends on narrow behavioral requirements:
script direction, schema validity, tool-call arguments, refusal language, or
age/register constraints. A scalar metric can look acceptable while a named
deployment state regresses.

This paper studies that risk in one trilingual KO/RU/EN adapter audit. The
scope is intentionally small. We do not introduce a new model architecture or
a general multilingual benchmark. We ask a narrower engineering question:
when a niche deployment has non-negotiable behavioral states, what should the
adapter promotion pipeline record and do before deployment?

We propose **state-gated audit**. Candidate adapters are still trained and
screened with ordinary scalar metrics, but promotion additionally requires a
versioned gate suite. Gates are reported as audit states rather than as a
single score:

$$
\operatorname{audit}(L)=\{\operatorname{loss}(L), G_1(L), \dots, G_8(L),
\operatorname{raw\ outputs}, \operatorname{action}\}.
$$

The empirical case motivating the protocol is a single historical adapter,
`lora_v1`. It remains attractive under held-out loss (`eval_loss=0.531`) and
task metrics, but its discovery G2 script-state smoke test falls to 1/4. This
is not a reproducible law. A same-mix same-hyperparameter retrain, five seed
retrainings, and seven capacity arms all fail to reproduce the 1/4 outcome.
The honest conclusion is therefore selector disagreement plus negative
mechanism evidence.

## 2 Related Work and Positioning

This work sits closest to adapter selection, behavioral evaluation, and
structured-output reliability. LoRA and other PEFT methods make it cheap to
train many candidate adapters, but that convenience shifts the deployment
problem from "can we fine-tune?" to "which fine-tuned artifact is safe to
promote?" Standard selection signals such as held-out cross-entropy, BLEU, and
chrF summarize broad task behavior. They do not name deployment states such as
script discipline, exact JSON structure, tool-call validity, refusal language,
or age/register constraints. The paper therefore treats scalar metrics as
useful first-stage filters, not as deployment certificates.

Behavioral evaluation work has long argued that aggregate scores can hide
subgroup or task-state failures. Our case study is narrower: it does not build
a general multilingual benchmark. Instead, it asks how a small team should
document promotion decisions when a deployment has explicit non-negotiable
states. The audit is operational. It records raw generations, scorer versions,
gate states, and the action triggered by each state. This differs from
leaderboard-style evaluation because the primary output is not a rank; it is a
pipeline decision: eligible, inspect/repair, or block.

The structured-output side connects to JSON validity, function calling, and
constrained decoding. In this paper G3 is not a semantic task score. It is an
interface-discipline gate: the model must emit parseable JSON with required
keys, correct types, allowed enum values, and no forbidden extra keys. A model
can be semantically helpful yet fail G3 if a downstream parser cannot consume
the output. Conversely, passing G3 does not certify semantic correctness. This
claim boundary is central to the paper's framing.

The human-tier motivation is a small-N deployment specification, not a
population study. The case starts from a trilingual family tutoring setting
because it provides concrete gate requirements: KO/RU/EN script transfer,
schema-constrained cards, age/register constraints, and refusal language. The
paper does not use the household observation to estimate prevalence. It uses it
to define a deployment state vector that can be audited automatically for the
adapter artifacts studied here.

## 3 Audit Protocol

The audit uses eight deployment gates. The 30-probe discovery set maps to
seven released categories: translation (6), grammar (4), phonetic/script
transfer (4), family scenario (4), function call (4), age band (4), and safety
(4). The paper groups these categories into eight deployment states because
persona-bridge and L1-aware grammar are separate rubric dimensions inside the
human-rated portion. We report this mapping explicitly to avoid treating the
30 probes as independent iid samples.

| Gate | Deployment state | Evidence in this paper |
|---|---|---|
| G1 | translation/task behavior | 6 discovery probes + held-out task metrics |
| G2 | cross-script state discipline | 4 discovery probes; 52-probe rerun for 16 key adapters |
| G3 | JSON/schema validity | 14 discovery checks; 80-probe schema rerun for 16 key adapters |
| G4 | function-call validity | 4 discovery prompts; reported as diagnostic |
| G5 | L1-aware grammar explanation | human-rated rubric dimension |
| G6 | age-banded vocabulary/register | human-rated rubric dimension |
| G7 | persona-bridge consistency | human-rated rubric dimension |
| G8 | safety/refusal behavior | 4 discovery prompts |

Only G2 and G3 carry the main empirical load. G2 is a Unicode-block
script-state check, not a phonetic transliteration-quality metric. The expanded
G2 audit uses 52 prompts: four directions (KO→Cyrillic, RU→Hangul, KO→Latin,
RU→Latin), 13 lexical surfaces each. A response passes a prompt when the target
script ratio is at least 85% and no other tracked script exceeds 10%.

The expanded G3 audit uses 80 automatic schema prompts across four groups:
object cards, intent routing, age/register rewrites, and tool-call JSON. A
response must parse as JSON and satisfy required-key, type, enum, and
no-extra-key constraints where declared. G3 checks schema discipline, not
semantic correctness.

For G2-52 we report threshold sensitivity rather than a single calibrated
cutoff:

| Band | Rule |
|---|---|
| GREEN | total ≥50/52 and every direction ≥12/13 |
| AMBER | total ≥48/52 and every direction ≥10/13 |
| RED | below AMBER floor |

The bands trigger actions. GREEN is eligible for deployment with raw outputs
and scorer versions logged. AMBER is held for raw-output review, error
labeling, targeted repair or scoped waiver, and rerun of failed gates. RED
blocks promotion. AMBER and RED are not silent overrides: AMBER requires
documented repair or scoped waiver plus failed-gate rerun; RED cannot be waived
unless the deployment specification changes and the full audit is rerun.

The G3-80 bands mirror this action logic:

| Band | Rule |
|---|---|
| GREEN | total >=72/80 and every 20-probe group >=18/20 |
| AMBER | total >=64/80 and every 20-probe group >=15/20 |
| RED | below AMBER floor |

These thresholds are engineering triage rules. They are deliberately reported
with sensitivity and caveats rather than as calibrated precision/recall
cutoffs. The deployment owner may choose stricter or looser thresholds, but the
paper requires that the threshold version, raw outputs, and resulting action
state be logged.

## 4 Experimental Setup

We audit Gemma 4 E2B/E4B LoRA adapters trained on KO/RU/EN mixtures built from
direct translation data, English-pivot triples, synthetic object cards,
family-scenario dialogs, function-call examples, and targeted script-transfer
pairs. The audit atlas contains **176 evaluated artifacts**: 1 stock baseline,
36 final adapters, and 139 intermediate checkpoints. These artifacts are
dependent; many are checkpoints from the same run. We use the atlas to
document what happened, not to estimate prevalence.

The key trajectory is `lora_v1`: Gemma 4 E2B, LoRA r=32, alpha=64, bf16,
AdamW-8bit, cosine learning rate 2e-4, no explicit script-transfer injection.
Controlled retrainings include a same-mix same-hyperparameter dense retrain,
five seed resamples, and seven LoRA capacity arms.

The empirical audit uses three nested artifact sets:

| Set | Size | Purpose |
|---|---:|---|
| Discovery audit atlas | 176 artifacts | document historical G2/G3 outcomes and negative retraining results |
| G2-52 rerun subset | 16 adapters | test whether the original G2 failure survives a larger script-state gate |
| G3-80 rerun subset | 16 adapters | test whether schema debt persists under a larger structured-output gate |

The 176 artifacts are not iid samples. They include intermediate checkpoints
from the same run, dense step grids, and related ablations. We therefore never
convert the atlas into a population prevalence estimate. Its role is audit
traceability: every artifact that could affect the story is visible.

## 5 Case Observation

The stock E2B baseline passes the discovery G2 smoke set at 4/4 and G3 at
10/14. The historical `lora_v1` final adapter remains loss-attractive
(`eval_loss=0.531`) but falls to G2=1/4 and G3=7/14. Its step-4000 checkpoint
shows the same G2=1/4 outcome. These two artifacts are adjacent checkpoints of
one training trajectory, so the independent-run count is one.

Adding 300 script-transfer examples in a later run (`lora_v2`) repairs G2 on
the discovery probes (4/4) and reaches 52/52 on G2-52, but it remains AMBER on
G3-80 (73/80; worst group 16/20). We therefore do not claim that data injection
solves the adapter; it repairs one audit state while leaving independent schema
debt.

The raw G2 examples show why this matters. For KO to Cyrillic prompts,
`lora_v1` often echoes Hangul instead of emitting Cyrillic. For RU to Hangul,
it sometimes translates rather than transliterates. These outputs are fluent
and can look superficially useful, which is why scalar task metrics do not
capture the deployment violation. The expanded G2-52 rerun confirms that the
observation is not a four-prompt artifact: `lora_v1` remains RED at 36/52, with
the worst direction scoring 6/13.

G3-80 adds a second independent debt signal. `lora_v1` scores 52/80, with its
tool-call group falling to 3/20. `lora_v2` repairs G2 but remains AMBER on
G3-80. This prevents the paper from telling an overly simple repair story. The
targeted script-transfer injection fixes the script-state gate in one run; it
does not make the adapter generally deployment-ready.

## 6 Controlled Non-Reproduction

We tested whether the G2=1/4 outcome follows from training duration, data mix,
seed, or LoRA capacity. It does not reproduce in the controlled set.

| Controlled retraining | n | G2=1/4 outcomes |
|---|---:|---:|
| same-mix same-hp dense retrain | 1 | 0 |
| seed sweep | 5 | 0 |
| r/alpha capacity sweep | 7 | 0 |
| total | 13 | 0 |

For 0/13, the one-sided 95% Clopper-Pearson upper bound is
$1-0.05^{1/13}\approx0.21$. The point estimate is zero, but the interval admits
a moderate seed-stochastic phenomenon. We therefore do not claim the failure is
rare. We claim only that the deterministic mechanisms we tested are not
supported by the controlled retrainings.

The same-mix retrain also lands far from the original adapter in LoRA-weight
space: across 353 matched modules, the median relative Frobenius distance is
1.29. This is a diagnostic consistent with different stochastic endpoints, not
causal proof.

The negative result is not a footnote; it is part of the claim. If the original
trajectory cannot be reproduced as a deterministic law, the paper should not
claim a deterministic law. The remaining contribution is still useful but more
modest: scalar metrics did not certify the deployment state of a candidate
adapter, and an explicit gate suite produced an actionable audit state before
promotion.

## 7 Promotion-Decision Audit Trace

We trace four promotion rules: loss-only, task-metric, random final checkpoint,
and state-gated audit. This is a decision trace, not a selector benchmark.

On `lora_v1`, scalar rules would keep the adapter under consideration: held-out
loss is acceptable, task metrics remain competitive, and the final checkpoint
exists. State-gated audit blocks it because G2 is RED.

| Variant | G2-52 | G2 band | G3-80 | G3 band | Audit action |
|---|---:|---|---:|---|---|
| `stock` | 51/52 | GREEN | 78/80 | GREEN | eligible baseline; log outputs |
| `lora_v1` | 36/52 | RED | 52/80 | RED | block promotion; rollback or retrain |
| `lora_v2` | 52/52 | GREEN | 73/80 | AMBER | hold; repair/rerun G3 |
| `L_v1_recreate` | 49/52 | AMBER | 72/80 | AMBER | inspect raw outputs; repair/waiver; rerun failed gates |
| `v1ra_r64_a128` | 44/52 | RED | 63/80 | RED | block; not a boundary waiver case |

Threshold sensitivity confirms the narrow claim:

| G2 rule | G2-pass variants | G2+G3-80 GREEN variants | Stable G2 failures |
|---|---:|---:|---|
| total ≥48/52 and each direction ≥10/13 | 14/16 | 4/16 | `lora_v1`, `v1ra_r64_a128` |
| total ≥50/52 and each direction ≥12/13 | 11/16 | 4/16 | `lora_v1`, `v1ra_r64_a128` |
| total =52/52 and each direction =13/13 | 5/16 | 1/16 | `lora_v1`, `v1ra_r64_a128` |

Thus `lora_v1` is not an artifact of the current 50/52 cutoff. The threshold
mainly changes how boundary controls are routed to review.

The full G3-80 rerun strengthens the schema side of the audit. It shows that
schema debt is not identical to the G2 script-state failure:

| Variant | G3-80 | Worst group | G3 band |
|---|---:|---:|---|
| `stock` | 78/80 | 18/20 `router` | GREEN |
| `lora_v1` | 52/80 | 3/20 `tool_call` | RED |
| `lora_v2` | 73/80 | 16/20 `router` | AMBER |
| `L_v1_recreate` | 72/80 | 16/20 `router` | AMBER |
| `v1seed_7777` | 45/80 | 2/20 `router` | RED |
| `v1ra_r64_a128` | 63/80 | 12/20 `tool_call` | RED |

The combined audit trace is therefore more informative than any single gate.
Some adapters are G2-clean but blocked by G3. Some are boundary cases on both
gates. A few pass both expanded automatic gates. The protocol does not claim
that all rejected adapters are unusable; it claims that automatic promotion is
not justified until the failed gate is repaired, waived by a changed deployment
specification, and rerun.

| Adapter | G2 state | G3 state | Pipeline action |
|---|---|---|---|
| `stock` | GREEN | GREEN | eligible baseline; log audit artifacts |
| `lora_v1` | RED | RED | block promotion; retrain/repair then rerun failed gate |
| `lora_v2` | GREEN | AMBER | inspect schema failures; repair or constrained decoding; rerun G3 |
| `L_v1_recreate` | AMBER | AMBER | inspect raw outputs; targeted repair or scoped waiver; rerun failed gates |
| `v1ra_r64_a128` | RED | RED | block promotion; not a boundary waiver case |

## 8 Discussion and Limitations

Three claims survive the audit.

First, loss does not certify deployment state in this case study. A
loss-attractive adapter can fail an explicit gate.

Second, gates are non-redundant. `lora_v2` repairs G2 but remains AMBER on
G3-80; schema discipline requires a separate recovery strategy such as
constrained decoding or schema-guided generation.

Third, mechanism claims must be weaker than audit claims. We observed one
training trajectory that scalar metrics would not flag, but we did not
reproduce the original 1/4 G2 outcome under controlled retraining.

Limitations are substantial. The central failure is one independent training
trajectory. The atlas is dependent and cannot estimate population rates. G2-52
checks script state, not phonetic accuracy. G3-80 checks schema shape, not
semantic correctness. The human-tier motivation is N=1 and supports only
existence-level claims. The paper should be read as a niche-population adapter
audit case study, not as a general multilingual LoRA benchmark.

## 9 Conclusion

This case study argues for a modest practice: when fine-tuning adapters for a
niche deployment, record explicit behavioral gates before promotion and map
audit states to pipeline actions. In our KO/RU/EN LoRA audit, one
loss-attractive trajectory fails a cross-script state gate and is not
reproduced in 13 controlled retrainings. That negative result is part of the
claim boundary. The useful contribution is not a new failure law, but a
conservative audit workflow that makes hidden behavioral debt visible before
adapter deployment.
