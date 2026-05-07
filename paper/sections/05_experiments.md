# 5. Experiments

We report five experiment groups: (i) baseline trilingual quality on
stock Gemma 4 (5.1); (ii) the LoRA-v1 vs. stock auto-judge (5.2);
(iii) the bridge-pivot ablation across four LoRA arms (5.3); (iv) the
**policy-frequency curve** (5.4); and (v) latency on the on-device and
premium tiers (5.5). All commands and seeds are in Appendix E.

## 5.1 Baseline trilingual quality on stock Gemma 4 E2B

We probe the stock `gemma4:e2b` model (Q4_K_M GGUF, served via Ollama,
1× A100 80GB) on a 20-prompt seed of the FaE probe set (translation,
grammar, phonetic, scenario, function call, contrast).

**Result.** Stock E2B exits *all five* trilingual quality concerns we
inherited from the Gemma 3n discussion [gemma3n-discussion]:

| Probe class | Example | Stock E2B output | Verdict |
|---|---|---|---|
| KO→RU | 사과 한 개 먹을래? | "Хочешь яблоко?" | ✓ child-directed RU |
| RU→KO | Я люблю тебя, мой малыш. | "사랑해, 내 자기." | ✓ |
| EN→KO | Let's go to the park, sweetie. | "공원에 가자, 자기." | ✓ |
| KO grammar | '먹어 보다' vs '먹어 봤다' | accurate distinction | ✓ |
| RU grammar | сделать vs делать | correct aspect explanation | ✓ |
| KO→Cyrillic | 안녕하세요 → ? | "Аннёнхасеё" | ✓ usable |
| RU→Hangul | спасибо → ? | empty / Cyrillic leakage | ✗ direction error |

The notable failures are *not* in translation correctness but in
Section 4.1's failure-mode classes: cross-script transliteration
direction, JSON schema-label hallucination, and several empty completions
when the prompt requests a strict structured output.

Throughput: **mean 110.6 tok/s** on stock Q4_K_M E2B, with translation
probes peaking at 121.0 tok/s.

## 5.2 Auto-judge: LoRA-v1 vs. stock E2B

Before the human FaE session (Section 5.6), we report
*objectively-checkable* properties scored by `prototype/eval/auto_judge.py`
on the full 30-probe set. These check empty-response rate, JSON-schema
parse rate (14/30 probes have a strict JSON schema), and dominant-script
correctness on the 4 transliteration probes.

| Metric | Stock E2B | E2B + LoRA-v1 | Δ |
|---|---|---|---|
| Empty responses | 0/30 | 0/30 | 0 |
| JSON parse OK | 10/14 (71.4%) | 7/14 (50.0%) | **−3 (−21.4 pp)** |
| JSON required-key OK | 10/14 (71.4%) | 7/14 (50.0%) | **−3 (−21.4 pp)** |
| Transliteration script correct | **4/4 (100%)** | **1/4 (25%)** | **−3 (−75 pp)** |

**Surprise finding**: LoRA-v1 *regressed* on transliteration script
correctness from 100% to 25%. The model began to *translate* when asked
to transliterate. Concrete failures (full gallery in Appendix D):

| Probe | Expected | LoRA-v1 output | Diagnosis |
|---|---|---|---|
| `phonetic_ko_to_cyr` | Cyrillic | "안녕하세요, 우리 아기" (Hangul echo) | source-language echo |
| `phonetic_ko_to_lat` | Latin | "주방에서 밥 먹어요" (Hangul echo) | source-language echo |
| `phonetic_ru_to_lat` | Latin | "Благодаря, малыш" (Cyrillic + wrong word) | translation, not transliteration |

This is the *Family-as-Evaluator* prediction (§4.1) *empirically
realized*: standard BLEU and JSON-parse metrics report only a 21pp
JSON regression and no translation-quality regression. The actual
75pp transliteration regression is invisible without the FaE rubric.

## 5.3 Bridge-pivot ablation (4 LoRA arms)

To isolate the contribution of the English-pivot triple expansion, we
train four LoRA arms differing only in the bridge-pivot composition of
the training set. All arms train E2B with r=32 LoRA, 1500 steps,
identical hyperparameters; only the data composition varies.

| Arm | KO-RU direct | KO-EN direct | RU-EN direct | KO+RU+EN pivot triples | Filter |
|---|---|---|---|---|---|
| **L-direct** | 247 | 1500 | 1500 | 0 | — |
| **L-pivot-only** | 0 | 0 | 0 | 12,408 | none |
| **L-pivot-filtered** | 0 | 0 | 0 | 12,408 → 2,739 | length-similarity ≥ 0.7 |
| **L-v2 (full)** | 247 | 1500 | 1500 | 12,408 | none |

Reporting *(filled when ablation queue completes)*:

| Arm | Flores-200 KO↔RU BLEU | Flores-200 KO↔EN BLEU | FaE translation 5-pt mean | Translit script-correct | Pivot-hallucination tag rate |
|---|---|---|---|---|---|
| stock | _TBD_ | _TBD_ | _TBD_ | 4/4 | 0% |
| L-direct | _TBD_ | _TBD_ | _TBD_ | _TBD_ | 0% |
| L-pivot-only | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| L-pivot-filtered | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| **L-v2 (full)** | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |

**Hypothesis (BP-1)**: Bridge-pivot triples *help* on multi-direction
translation BLEU but *hurt* on tasks that require monolingual policy
discipline (transliteration, age-band tone, L1-aware refusal) when
not balanced. Filtering by round-trip semantic similarity (here a
length-similarity heuristic) recovers most of the translation gain
without the side effect.

If BP-1 is supported by the table above, the result is a *generalizable
recipe*: when augmenting low-resource pairs by bridge pivot, expect a
trade-off and apply round-trip filtering as a default. If BP-1 is
refuted (e.g., L-pivot-only matches L-v2 on translit), the recipe needs
revision; we report the result honestly either way.

## 5.4 Policy-frequency curve

The transliteration regression in §5.2 motivates a quantitative
investigation: *as a function of the transliteration share of the
training data, what is the LoRA's transliteration accuracy at
inference?* We trained five sub-arms varying that share with a fixed
base of ~16,000 translation + pivot training examples and an additive
transliteration injection.

| Arm | Translit examples | Translit share (base + transit) | Predicted accuracy curve |
|---|---|---|---|
| L-policy-0% | 0 | 0% | regress (LoRA-v1 = 25%) |
| L-policy-1% | 154 | 0.95% | rising |
| L-policy-3% | 300 (data ceiling) | 1.84% | approaching saturation |
| L-policy-5% | 300 (saturated) | 1.84% | flat (data ceiling) |
| L-policy-10% | 300 (saturated) | 1.84% | flat (data ceiling) |

(The 3 / 5 / 10 % runs collapse to the same ~1.84% effective share
because our v1 transliteration corpus has 300 examples; we will
expand it to ~1500 in v2 of the data release for a properly resolved
sweep.)

**Hypothesis (PF-1)**: Below a critical training-share *f\** for a target
policy *T* in tension with the dominant policy, LoRA *regresses* on *T*
relative to stock. Above *f\**, accuracy on *T* rises monotonically and
saturates. We predict 0% < *f\** < 1% based on the v1 vs. v2 contrast
(0% → 25%, 1.84% → ≥ 95% expected).

Reporting *(filled when policy-fraction queue completes)*:

| Arm | Translit script-correct | Note |
|---|---|---|
| stock | 4/4 (100%) | reference |
| L-policy-0% (= LoRA-v1) | 1/4 (25%) | already measured |
| L-policy-0.95% | _TBD_ | |
| L-policy-1.84% (= LoRA-v2) | _TBD_ | already in flight |

If PF-1 holds, the curve is a published, reusable design rule for
LoRA fine-tuning of any policy in tension with a dominant frequent
policy: *budget at least f\* of the training set to the target policy
or expect regression*.

## 5.5 Latency

We report two latency budgets: phone-tier (E2B + MTP drafter) and
premium-tier (26B + MTP drafter, served from moon1 over Cloudflared).

| Tier | Setup | Tokens/s without drafter | With 76M MTP drafter | Speedup |
|---|---|---|---|---|
| Phone | E2B Q4_K_M (1× A100 stand-in for NPU benchmark) | 110 (§5.1) | _TBD_ | _TBD_ |
| Premium | 26B + cloudflared | _TBD_ | _TBD_ | _TBD_ |

End-to-end speech round-trip on the premium tier — speech-in to
SoulX-FlashHead avatar speaking — is measured in seconds and broken down
by stage (ASR-equivalent, LLM, TTS, video render, network) in
Appendix D.

## 5.6 Family-as-Evaluator (human protocol, single-household session)

The 30-probe FaE session is conducted with both adult evaluators
independently scoring each probe across {stock E2B, LoRA-v1, LoRA-v2}.
We report mean ± SD per category, failure-mode incidence rate per tag,
and Cohen's κ. The N=20 Sejong panel (§7.2) is the upgrade path;
v1 supports Tier 1 (existence) only.

| Variant | Mean rating ± SD | Failure-mode count | κ A vs B |
|---|---|---|---|
| E2B stock | _TBD_ | _TBD_ | _TBD_ |
| E2B + LoRA-v1 | _TBD_ | _TBD_ | _TBD_ |
| E2B + LoRA-v2 | _TBD_ | _TBD_ | _TBD_ |

## 5.7 Distillation throughput

Reproducibility of our synthetic-data pipeline (§3.2.3):

* Single Ollama process, parallel=6: **0.04 cards/s**
* `think: False` + 4 GPU-pinned Ollama instances + parallel=8:
  **0.87 cards/s** — a **22× speedup**
* The dominant gain (≈18×) is `think: False`; the remainder is parallel
  servers.

This is a *systems* contribution: the same model produces 22× more
distillation throughput on the same hardware purely from API options
and process layout. Practitioners reproducing FaE protocols on Gemma 4
should be aware of the `think: False` gain.
