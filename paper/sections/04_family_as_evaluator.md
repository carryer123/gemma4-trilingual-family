# 4. Behavioral Gate Suite and Audit Protocol

This section documents the audit protocol used in the case study. The released
discovery set contains 30 probes across seven categories; the submission
additionally reports a 52-probe automatic G2 script-state rerun and an
80-probe automatic G3 schema rerun for the 16 paper-critical adapters.
The probe set is a deployment audit, not a
ranking task: probes are versioned, raw generations are retained, and failures
route adapters to GREEN/AMBER/RED actions.

## 4.1 Failure-mode classes

We catalog failure-mode classes that ordinary scalar metrics can miss.

| Failure mode tag | Gate | Example | Why scalar metrics miss it |
|---|---|---|---|
| `cross_script_direction` | G2 | "Convert 안녕하세요 to Cyrillic" → Hangul echo | loss/BLEU need not contain the script policy |
| `wrong_task_translation` | G2 | transliteration prompt answered as translation | output is fluent but wrong task |
| `schema_invalid_json` | G3 | non-JSON under JSON-only instruction | downstream parser fails |
| `schema_enum_violation` | G3 | enum value outside allowed set | JSON parses but routing breaks |
| `tool_argument_error` | G4 | missing required argument | tool call cannot execute |
| `persona_bridge_collapse` | G7 | requested RU explanation answered in EN | task metric unaffected |
| `age_band_leakage` | G6 | child mode emits abstract grammar terminology | perplexity unchanged |
| `safety_refusal_drift` | G8 | refusal language mismatches user language | safety gate is deployment-specific |

## 4.2 Probe and scorer mapping

| Evidence source | Count | Scoring |
|---|---:|---|
| Discovery set | 30 | mixed automatic + rubric scoring |
| G2 extended script-state set | 52 | Unicode-block script-state scorer |
| G3 extended schema set | 80 | JSON parse + required-key/type/enum scorer |

The 30-probe discovery set has the following category counts:
translation 6, grammar 4, phonetic/script-transfer 4, family scenario 4,
function call 4, age band 4, and safety 4. Because some deployment states are
rubric dimensions inside the same raw prompt categories, the paper reports
gate states separately from JSONL category names.

The 52-probe G2 rerun checks script state only; it does not certify phonetic
adequacy or semantic transliteration quality. The 80-probe G3 rerun checks
schema discipline across object-card, intent-router, age/register, and
tool-call JSON prompts; it does not certify semantic correctness.

## 4.3 Human-tier scope

The human-tier motivation is N=1. It supplies a deployment specification and
rubric examples, not population evidence. Any N>1 evaluation requires local
ethics review, declared evaluator roles, inter-evaluator agreement, and a
pre-registered claim tier.

## 4.4 Claim tiers

* **Tier 1 (existence)**: a failure mode is observed in at least one
  deployment setting. Supported by this paper only at case-study level.
* **Tier 2 (predictability)**: the failure mode is reproduced across
  independent deployment settings or training runs with declared agreement.
* **Tier 3 (prevalence)**: a powered population study estimates frequency.

The present paper is Tier 1 for human-tier evidence and negative-mechanism
evidence for the `lora_v1` G2 observation.

## 4.5 What the audit is not

* It is not a ranked evaluation task; the primary output is an action state.
* It is not a calibrated detector; no precision/recall claim is made.
* It is not an IRB substitute; any human panel beyond the authors'
  own-household motivation needs local review.
* It is not a claim that G2/G3 failures are common in LoRA fine-tuning.

## 4.6 Release

The protocol specification, probe sets, failure taxonomy, pre-registration
template, scoring schema, and automatic G2/G3 scorers are released under
CC-BY 4.0. Adopters should fork the template, localize the probe surfaces, and
report gate states with raw outputs and claim tiers.
