# 8. Conclusion

We argued that niche-population LoRA adapters should pass an explicit
deployment audit before promotion, not validation loss alone. In a KO + RU +
EN case study, one loss-attractive trajectory failed an explicit
cross-script gate, and the audit routed it to RED rather than deployment.

The empirical result is intentionally modest. One original training
trajectory (`lora_v1`) regressed on cross-script state discipline while
remaining attractive under loss and task metrics. Thirteen
controlled retrainings of the same configuration family did not
reproduce the 1/4 G2 collapse, so we do not claim a deterministic
training-duration, data-frequency, or capacity mechanism. The correct
reading is a negative finding about mechanism plus a selector
disagreement: loss-only selection would promote the run, while
state-gated audit rejects it on a deployment-critical behavioral
state. The expanded 52-probe rerun preserves `lora_v1` as a red-band
failure but also reveals amber/red uncertainty in other controls, so
the audit atlas is evidence for conservative triage, not an estimate of
a population cliff rate or calibrated selector accuracy.

The methodological point is simple: scalar improvement does not
certify hidden state. For adapter deployment, the states that matter
should be named before promotion, measured with explicit gates, and tied
to explicit actions: GREEN logs and admits, AMBER triggers review,
repair or waiver plus failed-gate rerun, and RED blocks promotion.
Claim tiers then separate existence, predictability, and prevalence.

The useful next result is not agreement with our N=1 trajectory, but a
clearer estimate of when state-gated audit blocks genuinely unsafe adapters,
when it sends good adapters to unnecessary review, and how often scalar-only
promotion misses deployment-critical state regressions.
