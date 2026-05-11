# 1. Introduction

LoRA fine-tuning pipelines usually promote adapters by held-out loss,
BLEU, chrF, or a small set of task-specific metrics. These signals are
necessary, but they do not certify the behavioral states a deployment may
depend on. In a trilingual KO/RU/EN niche-population setting, those states
include script direction, JSON/schema validity, function-call arguments,
L1-aware explanations, age/register constraints, persona consistency, and
safety refusals.

This paper is a case study, not a general benchmark. We study a family of
Gemma 4 LoRA adapters and ask what an adapter promotion pipeline should record
before deployment when the target use case has non-negotiable behavioral
requirements. The motivating observation is one historical training trajectory:
`lora_v1` remains attractive under held-out loss (`eval_loss=0.531`) but fails
a discovery cross-script gate at G2=1/4. The failure is not reproduced in 13
controlled retrainings. That negative result is central to the paper rather
than a footnote.

We therefore frame the contribution as **state-gated audit**. The audit
keeps scalar metrics, but it adds versioned deployment gates, raw-generation
records, and GREEN/AMBER/RED actions:

* **GREEN**: eligible for deployment, with audit version and raw outputs logged.
* **AMBER**: held for raw-output review, documented repair or scoped waiver,
  and rerun of failed gates.
* **RED**: blocked from promotion unless retraining, rollback, or a changed
  deployment specification is followed by a full audit rerun.

The empirical evidence is bounded. We maintain an audit atlas of 176 evaluated
artifacts, but those artifacts are dependent: many are intermediate checkpoints
from the same training runs. We use the atlas to document claim boundaries,
not to estimate prevalence. A stricter 52-probe rerun of the G2 script-state
gate confirms that `lora_v1` is not merely a 4-probe artifact (36/52; worst
direction 6/13), while also showing that several controls are
threshold-sensitive or blocked by an independent G3 JSON/schema gate.

The contributions are deliberately modest:

* **C1.** A trilingual LoRA audit case study showing one loss-attractive
  trajectory that fails an explicit deployment gate.
* **C2.** A state-gated audit workflow that maps gate states to promotion
  actions rather than treating gates as ranked scores.
* **C3.** A negative mechanism result: the G2=1/4 outcome is not reproduced in
  13 controlled retrainings, so the paper does not claim a deterministic cliff
  law or a population rate.
* **C4.** Reproducibility artifacts: raw generations, G2-52 scores, threshold
  sensitivity, foreground rechecks for the key adapters, and the probe/scoring
  specification.

The rest of the paper keeps the system details and family motivation in the
background. The load-bearing claim is narrower: scalar adapter selection can
miss a deployment-state failure, and an explicit audit workflow makes that
failure actionable before promotion.
