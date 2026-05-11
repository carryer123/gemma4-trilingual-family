# Appendix F: Human-Tier Audit Protocol Specification (v1)

This appendix is a copy-paste-ready specification of the human-tier audit protocol
introduced in §4. It is also released as a stand-alone artifact at
`tools/fae_protocol/SPEC.md` in the repository under CC-BY 4.0.

## F.1 Pre-registration form

Fill in before running. Save as YAML under `tools/fae_protocol/preregistrations/`.

```yaml
human_tier_audit_preregistration:
  date: 2026-MM-DD
  language_triple:
    L1_A: ru          # ISO-639-1 of L1 of evaluator A
    L1_B: ko          # ISO-639-1 of L1 of evaluator B
    bridge: [en]      # bridge languages used in the household
  household:
    n_l1_a_speakers: 1
    n_l1_b_speakers: 1
    children:
      - {age_months: 21, l1: ko, observe_only: true}
  models_compared:
    - {id: gemma-4-E2B-it, variant: stock}
    - {id: gemma-4-E2B-it, variant: LoRA-v2,  adapter_path: lora_out/lora_v2/adapter}
  evaluators:
    A: {role: L1_A, name_pseudonym: P1, native_language: ru, target_language: ko, bridge: en}
    B: {role: L1_B, name_pseudonym: P2, native_language: ko, target_language: ru, bridge: en}
    C: {role: child_observer, n_minutes: 5, recording: parental_handwritten_notes}
  probe_set:
    file: human_tier_audit_probes_v1.jsonl
    sha256: <fill at submission time>
    n_probes: 30
  stop_criterion: all_probes_scored_by_both_adults
  claim_tier: 1   # existence
  ethics_scope: own_household_only_no_irb_needed
```

## F.2 Human-tier audit instantiation

The case-study human-tier instantiation is one way to score the
human-tier gates G5, G6, and part of G7. It is reported as a Tier-1
case-study protocol, not as population evidence or a reusable population
panel.

1. **Probe set.** A stratified probe set versioned with SHA-256,
   released CC-BY 4.0 in `tools/fae_protocol/`. The current release
   includes the v1 discovery set and the v2 52-probe transliteration
   set.
2. **Evaluator roles.** Adult evaluators declare their L1/L2
   memberships and rate only probes their L1 can adjudicate. A child
   observer track may record non-verbal proxy variables (attention
   duration, smile/laugh count, repetition-after-model count), but this
   track is reported descriptively and is never aggregated into a gate
   decision.
3. **Scoring.** Each human-rated probe receives a 5-point Likert score
   with mandatory free-text justification on every score $\le 3$.
4. **Failure-mode tagging.** Every score $\le 3$ is annotated with one
   or more tags from the taxonomy in §4.1; new tags are open-coded and
   added to a local-extension list.
5. **Inter-evaluator agreement.** For N>1 evaluations, Cohen's
   $\kappa$ on tag presence per probe is reported alongside means and
   SDs. The N=1 case in this paper does not support reliability claims.
6. **Pre-registration.** A YAML pre-registration form pins the probe-set
   hash, evaluator pseudonyms, model variants, and targeted claim tier.

## F.3 Probe-set construction rules

A v-N probe set must satisfy:

* **k** ≥ 24 probes (we use 30)
* **Stratification quotas** (rounded to nearest integer for k ≠ 30):

```
translation         20% (6 / 30)
grammar             13% (4 / 30)
phonetic_cross_script 13% (4 / 30)
family_scenario     13% (4 / 30)
function_call       13% (4 / 30)
age_band            13% (4 / 30) — 1 per band {0-2, 2-4, 4-6, 6-8}
safety_refusal      13% (4 / 30)
```

* **Reuse rule**: if a probe is reused across language triples, change
  ONLY the language-specific surface (e.g., the Korean object name) and
  keep the rubric identical. Surface-changed probes share the same probe
  id with a `-{lang_triple}` suffix.
* **Versioning**: probe sets are versioned with semver (v1.0.0, v1.1.0,
  ...) and tagged with their SHA-256 in the pre-registration form.

## F.4 Scoring CSV schema

`scores.csv`:

```
probe_id,evaluator_id,model_id,score,failure_tags,free_text,timestamp_iso
trans_ko_ru_1,A,gemma-4-E2B-it::stock,5,,,2026-05-09T19:20:00+09:00
trans_ko_ru_1,A,gemma-4-E2B-it::LoRA-v2,5,,,2026-05-09T19:20:08+09:00
trans_ko_ru_1,B,gemma-4-E2B-it::stock,5,,,2026-05-09T19:20:15+09:00
phonetic_ru_to_han,A,gemma-4-E2B-it::stock,4,,,...
phonetic_ru_to_han,A,gemma-4-E2B-it::LoRA-v1,1,cross_script_translit_direction;source_lang_echo,"Output is in Hangul but it's a translation, not a transliteration. The model said 고마워 ('thank you') instead of 스파시바.",...
```

`failure_tags` is a `;`-separated list from the v1 taxonomy:

```
cross_script_translit_direction
schema_label_hallucination
persona_bridge_collapse
age_band_leakage
pivot_hallucination
politeness_register_mismatch
phonetic_over_anglicization
l1_aware_contrast_hallucination
source_lang_echo                 # source-language echo (under cross_script_translit_direction)
empty_response                   # blank or whitespace-only
schema_invalid_json              # not parseable as JSON when JSON expected
```

New tags are added to the YAML pre-registration's `local_tag_extensions:` field.

## F.5 Reporting standard

A human-tier audit report includes, in order:

1. **Cover page**: pre-registration YAML, with SHA-256 of probe set and
   commit hash of the model checkpoints.
2. **Per-model summary table**:
   * mean ± SD per category, overall
   * failure-mode incidence rate per tag, overall
   * Cohen's κ inter-evaluator
   * empty-response count
3. **Disagreement gallery**: every probe with |score_A − score_B| ≥ 2,
   shown verbatim with both evaluators' free-text.
4. **Failure-mode catalog**: at least one verbatim example per
   tag with non-zero incidence; raw model output preserved.
5. **Statistical claim**: explicit Tier (1, 2, or 3) and supporting
   power statement.
6. **Reproducibility appendix**: model files, adapter files, sampling
   parameters, exact prompt format.

## F.6 Tier promotion rules

To upgrade a Tier 1 result to Tier 2, a human-tier evaluation must satisfy:

* N ≥ 10 households for the same language triple
* Household stratification along at least one demographic dimension
  (e.g., maternal Korean proficiency level for KO↔RU+EN)
* Inter-evaluator κ ≥ 0.6 averaged across households for the most
  prevalent tag
* All N households use the same v-X probe set
* The same n+5 hold-out probe families used in v1 must continue to
  reveal Tier-1 failure modes; no new probe families appearing only in
  newly-added households should dominate the conclusions

To upgrade Tier 2 to Tier 3, a power calculation against the desired
prevalence p and confidence c must justify the chosen N.

## F.7 What this protocol explicitly is not

* **It is not a ranked benchmark.** Probes are intentionally not
  ranked; the *catalog* of failure modes is the primary output, not a
  scalar.
* **It is not an IRB-substitute.** For any N>1 deployment, local ethics
  review applies.
* **It is not adversarial-robust.** Honest evaluators are assumed.
* **It is not exclusive.** Human-tier audit is meant to *complement* automated
  metrics like BLEU/COMET/JSON-parse-rate, not to replace them.

## F.8 Citation

```bibtex
@misc{anonymous2026audit,
  title  = {Human-Tier Audit Protocol for Niche-Population LLM Evaluation},
  author = {Anonymous Authors},
  year   = {2026},
  note   = {Appendix F of "State-Gated Audit for Niche-Population LoRA Fine-Tuning."},
  howpublished = {Anonymous supplementary material}
}
```
