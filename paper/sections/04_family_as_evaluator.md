# 4. Family-as-Evaluator: A Protocol Specification

This section reframes Family-as-Evaluator (FaE) from a *case-study
description* into a *generalizable protocol specification*. The N=1
demonstration with our own household (KO L1 + RU L1 + 21-month-old)
serves as the proof-of-concept; the formal protocol below is intended
for adoption by any practitioner deploying an LLM into a niche-population
multilingual setting where automated metrics are likely to under-specify
the task. A copy-paste-ready specification appears in Appendix F.

## 4.1 Why automated metrics under-specify niche-population LLM tasks

We catalog *failure-mode classes* that are systematically invisible to
BLEU, COMET, perplexity, and JSON-schema parse rate, and that we have
verified at least one instance of in §5.

| Failure-mode class | Example we observed | Why automated metrics miss it |
|---|---|---|
| **Cross-script transliteration direction error** | Russian word `кастрюля` "transliterated to Hangul" emitted as Cyrillic `нэмви` (source-script echo) | JSON parse passes; BLEU not applicable; only a Hangul-literate evaluator notices |
| **Schema-label hallucination** | `wife_card.explanation_in` (enum: `"ru" \| "en"`) emitted as a full English sentence describing the card | JSON parse passes; downstream code crashes silently |
| **Persona-bridge collapse** | User requests *Russian* explanation; model answers in *English* (collapse to dominant bridge) | BLEU on translation tasks unaffected; only persona-specific human evaluation catches |
| **Age-band leakage** | 0-2 mode emits abstract vocabulary like "particle of location" | Perplexity unchanged; only a child-development-aware evaluator catches |
| **Pivot hallucination** | KO + RU + EN triple looks aligned at the surface but the KO and RU sentences mean different things (English pivot was lossy) | Translation BLEU unaffected; only RU-L1 + KO-L1 evaluator triangulation catches |
| **Politeness-register mismatch** | Mother (RU L1) addressing child gets formal-honorific KO instead of child-directed informal | Translation correctness OK; pragmatically wrong |
| **Phonetic over-anglicization** | Korean `안녕하세요` rendered for English speaker as `annyeonghaseyo` (correct) but for Russian speaker also as `annyeonghaseyo` instead of `Аннёнхасеё` | Both pass formal correctness; RU evaluator notices the latter is cognitively useless |
| **L1-aware contrast hallucination** | The "Russian vs Korean" linguistic-contrast field invents a non-existent rule | LLM-as-judge biased to model's own knowledge — fails to flag |

The common feature is that automated metrics measure
*pattern-match-correctness against an expected output* but not
*semantic appropriateness against a niche-population's expectation*.

## 4.2 Protocol specification (v1)

A FaE evaluation has six required components. We give each a
specification that is independent of our specific household.

### 4.2.1 Probe set

* **Size**: a probe set has *k* = 30 probes (we recommend 30; the
  protocol allows any *k* ≥ 24 with the stratification below).
* **Stratification**: the probes are partitioned into seven categories
  with quotas:

  | Category | Quota (out of 30) | Tests |
  |---|---|---|
  | Translation | 6 | basic correctness in N(N-1) directions |
  | Grammar / morphology | 4 | L1-targeted explanation quality |
  | Phonetic / cross-script | 4 | transliteration-direction discipline |
  | Family scenario | 4 | pragmatic register, multi-turn realism |
  | Function call | 4 | strict JSON-schema adherence |
  | Age band | 4 | vocabulary control across 0-2 / 2-4 / 4-6 / 6-8 |
  | Safety / refusal | 4 | child-inappropriate-content handling |

* **Stratification rationale**: each category targets a *distinct*
  failure-mode class from §4.1, ensuring coverage of the catalog rather
  than only the most frequent failure type.

### 4.2.2 Evaluator role assignment

Three roles, each with explicit grading authority:

* **L1-A evaluator** (e.g., RU L1 in our case): grades L1-A correctness,
  L1-A-aware coaching, transliteration usability for L1-A literacy.
* **L1-B evaluator** (e.g., KO L1 in our case): grades L1-B correctness,
  cross-direction symmetry, register/honorific appropriateness, family-
  scenario fidelity.
* **Child observer** (or any third evaluator if no child is present):
  reports a non-verbal proxy — attention duration in seconds,
  smile/laugh count, repetition-after-model count. Limitations of this
  measurement are discussed in §6.

The two adult evaluators must be *independent* in scoring (no
cross-talk during a single grading round).

### 4.2.3 Scoring scale

Per probe, per evaluator, a 5-point Likert with mandatory free-text
justification on every score ≤ 3:

| Score | Meaning |
|---|---|
| 5 | native-quality / publishable |
| 4 | good, occasional polish |
| 3 | usable with light correction |
| 2 | partial, needs heavy correction |
| 1 | unusable / wrong |

Free-text justification is critical; the goal is not the numerical
average alone but the *failure-mode catalog* it produces (§4.1).

### 4.2.4 Failure-mode tagging

Every score ≤ 3 is annotated with one or more failure-mode tags from
the §4.1 taxonomy. New tag types may be introduced (open-coded);
they are appended to the appendix and considered candidate additions
to a future v2 of the taxonomy.

### 4.2.5 Reporting

For each (model, evaluator) pair we report:

1. **Mean rating ± SD** per category and overall
2. **Failure-mode incidence rate** per tag = (probes tagged with this
   failure mode) / (total probes)
3. **Cohen's κ inter-evaluator agreement** on tag presence (binary per
   tag per probe)
4. **Disagreement gallery** — probes where the two adult evaluators
   differ by ≥ 2 points; these are kept verbatim for downstream readers
   and treated as the highest-information observations

### 4.2.6 Statistical claim tiers

A FaE result supports one of three claim tiers, decided by *N* households
and the household stratification:

* **Tier 1 (existence)**: "this failure mode exists in at least one
  household." Supported by N ≥ 1.
* **Tier 2 (predictability)**: "this failure mode is reliably
  reproducible." Supported by N ≥ 10 with Cohen's κ ≥ 0.6 across
  households.
* **Tier 3 (prevalence)**: "this failure mode affects > p% of
  multicultural households at confidence c." Supported by N
  computed via a power calculation against the chosen p, c.

Our N=1 case study (§5) supports Tier 1 only; the Sejong N=20 panel
(§7.2) is the upgrade to Tier 2.

## 4.3 Pre-registration template

Adopters should pre-register an FaE evaluation before running it,
following the Open Science Framework convention. The template asks:

| Field | Example (our case) |
|---|---|
| Language triple | KO + RU + EN |
| Bridge language(s) | EN (RU↔EN, KO↔EN) |
| Household composition | 1 KO L1 + 1 RU L1 + 1 KO L1 child age 1y9m |
| Number of evaluators per probe | 2 adults + 1 child observation |
| Probe set version (with hash) | `family_as_evaluator_probes_v1.jsonl` SHA-256 [TBD at submit] |
| Models compared | E2B stock, E4B stock, 26B stock, E2B+LoRA-v2 |
| Stop criterion | all 30 probes scored by both adults |
| Claim tier targeted | Tier 1 (existence) |
| Sponsor / ethics review | none required for own-household; IRB for N>1 |

The template, the v1 probe set, and the scoring CSV layout are in
Appendix F; a copy is mirrored at `tools/fae_protocol/` in the public
repository so any practitioner can fork and adapt for their own
language triple.

## 4.4 What FaE *does not* do

We are explicit about scope to discourage misuse:

* FaE is not a substitute for translation BLEU when the goal is purely
  translation accuracy. It is complementary.
* FaE Tier 1 results are *not* statistical claims about the population.
  They are existence proofs that should be promoted to Tier 2 by
  N-scaling, not by inflated per-household statistical tests.
* FaE does not replace IRB review for any panel beyond the
  experimenter's own household. The Sejong panel (§7.2) is being
  designed in collaboration with the Sejong Multicultural Family
  Center under their own ethics framework.
* FaE assumes the evaluators are honest. It is not robust to adversarial
  evaluation. (We see this as a feature for this niche population, not
  a bug.)

## 4.5 Protocol release

The complete FaE specification, the 30-probe v1 set, and the failure-
mode taxonomy are released under CC-BY 4.0. We invite other research
groups to adopt, fork, and extend the protocol for their own
multilingual or multicultural population, and to contribute new
failure-mode classes to the public taxonomy.
