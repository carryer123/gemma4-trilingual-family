# Paper Upgrade Plan — Plan A (FaE Protocol) + Plan B (Pivot Ablation + Policy-Frequency Theory)

**Decided 2026-05-07**. Target arXiv v1 still 2026-05-17.
**Goal**: turn this from "hackathon companion paper" (1.5/5 academic) into
"workshop-ready with main-conf upgrade path" (3.5/5 by 5/17, 4.5/5 by Sejong N=20).

---

## Plan A — Formalize Family-as-Evaluator (FaE) as a generalizable protocol

### What changes

* **From** "we describe how our family rated probes"
* **To** "we specify a protocol any practitioner can apply to any
  multicultural household × any language triple × any age band, with
  statistical guarantees and a standard rubric."

### Concrete additions

1. **Protocol specification** — formal rubric-design rules:
   - Probe-set size *k* (we pick k=30 with category quotas)
   - Stratification dimensions (translation × grammar × phonetic × scenario × function-call × age × safety)
   - Evaluator role assignment (≥ 2 native L1 adults + 1 child observation)
   - Scoring scale (5-point Likert + free-text + failure-tag)
   - Statistical reporting (mean ± SD, Cohen's κ, failure-mode incidence rate)
   - Pre-registration template (which language triple, which baseline, what rubric, what stop)
2. **Open-source rubric template** — repo deliverable: `tools/fae_protocol/`
   with probe-set generator, scoring CSV, report-rendering script.
3. **N=1 case study (us) as Proof-of-Concept** — explicitly framed as
   a *single instantiation* of the protocol. The N=20 Sejong panel
   (Section 7) is the *validation* of the protocol's reliability.
4. **Reliability theory** — for any single-family case study, what claim
   strength is justified? We define three claim tiers:
   - Tier 1: *existence* claim (this failure mode exists in at least one household)
   - Tier 2: *predictability* claim (the failure mode is reliably reproducible)
   - Tier 3: *prevalence* claim (the failure mode affects >X% of multicultural households)
   N=1 supports Tier 1 only. N=10 supports Tier 2. N>>10 with sampling
   supports Tier 3.

### Paper section impact

* §4 rewrite: from "we used a protocol" → "here is the protocol; we used it on N=1"
* New §4.5: pre-registration of the N=20 Sejong panel
* New Appendix F: protocol specification (3 pages, copy-paste-ready)

---

## Plan B — Bridge-pivot ablation + policy-frequency theory

### What changes

* **From** "we used pivot, here's the model"
* **To** "we trained 5 LoRA variants varying the pivot mix and the
  transliteration policy fraction; we predict and confirm the policy-
  frequency phenomenon."

### Variants to train (5 total)

| ID | Training data composition | Purpose |
|---|---|---|
| **L0 stock** | (no fine-tune) | baseline reference |
| **L1 v1** | 18K (existing) — translation 95%, no transliteration | baseline LoRA we already have |
| **L1 v2** | 20.5K — translation 90% + transliteration 1.5% | hot-fix that's currently training |
| **L-direct** | 247 KO-RU + 11K KO-EN + 810K RU-EN (no pivot) | bridge-pivot ablation arm |
| **L-pivot-only** | only 12,408 KO+RU+EN triples × 6 dir = ~74K (no Tatoeba direct) | isolate pivot effect |
| **L-pivot-filtered** | 12,408 triples filtered to round-trip-similar (≈ 50–70%) | quality-vs-quantity |
| **L-policy-X (X=0/1/3/5/10%)** | translation + X% transliteration (sweep on policy fraction) | policy-frequency curve |

### Policy-frequency theory (the testable claim)

**Hypothesis (PF-1)**: For a target task T with training-data fraction *f*,
the model's correctness on T after LoRA monotonically increases with *f*
up to a saturation. Below a critical *f* (estimated ≈ 1%), LoRA *regresses*
T relative to stock because the dominant training-policy "wins."

**How we test it**: train L-policy-{0, 1, 3, 5, 10}% with transliteration
as T. Measure transliteration auto-judge accuracy on the same 4-probe
script-correctness set.

**Predicted curve**:
```
acc(T)  ↑
        │       ╭──────  (saturation ≈ stock)
        │      ╱
        │     ╱
        │    ╱
        │   ╱
   stock├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ (4/4 = 100%)
        │ ╳
   v1   │  ╳   (1/4 = 25%, X=0%)
        │
        └─────────────────────→ f (transliteration share %)
              0   1   3   5   10
```

If we see this curve, **policy-frequency phenomenon is empirically
demonstrated**, generalizing beyond our specific case.

### Bridge-pivot ablation (the orthogonal test)

**Hypothesis (BP-1)**: Bridge-pivot triples *help* on multi-direction
translation BLEU but *hurt* on tasks that require monolingual policy
(transliteration, age-band tone, L1-aware refusal) when not balanced.

**How we test it**: compare {L-direct, L-pivot-only, L-pivot-filtered,
L1-v2} on:
* Flores-200 KO↔RU and KO↔EN BLEU (translation only)
* Family-as-Evaluator transliteration sub-score
* Family-as-Evaluator family-scenario realism (qualitative + 5-point)

**Predicted finding**: pivot helps translation BLEU but the
*unfiltered* pivot pulls schema-label and transliteration scores down;
filtered pivot recovers most of the translation gain without the side
effect.

### Paper section impact

* §5 rewrite: 4-variant + policy-fraction ablation table
* New §5.X: policy-frequency curve (Fig. 4) and BP-1 confirmation/refutation
* New Appendix G: per-variant training logs and per-probe scores

---

## Multilingual generalization (light, for arXiv v1; deep for v3)

To support the "this is general, not our family-only" claim:

* Pull Tatoeba KO-VI, KO-ZH (Korean ↔ Vietnamese, Korean ↔ Mandarin)
* Build KO+VI+EN and KO+ZH+EN trilingual triples via English pivot
* Train one extra LoRA on KO+VI+EN data (or sample size matching v1)
* Run a 6-probe transliteration mini-eval on the new pair (no human
  evaluator yet — that's v3 territory)

This is enough to claim the *bridge-pivot pipeline* generalizes; the
*Family-as-Evaluator* generalization waits for Sejong N=20.

---

## Concrete schedule (D-10 → 0)

| Date | Track A (FaE protocol) | Track B (ablation) | Multilingual | Paper |
|---|---|---|---|---|
| 5/7 (now) | **plan write** ✓ | data file ladder for ablation | Tatoeba VI + ZH pulls | this doc |
| 5/8 | rubric template + protocol spec (Appx F) | LoRA-direct-only train (~2hr) | KO+VI+EN, KO+ZH+EN triples | §4 rewrite |
| 5/9 | 5-point Likert spreadsheet for human eval | LoRA-pivot-only train (~2hr) | KO+VI+EN distill 200 cards | §5 ablation skeleton |
| 5/10 | round-trip filter implementation | LoRA-pivot-filtered train (~2hr) | KO+VI+EN LoRA train (~2hr) | §6 policy-frequency theory |
| 5/11 | wife+husband 30-probe session #1 | L-policy-{1,3,5}% LoRA mini-runs (300 step each) | — | §5 results |
| 5/12 | tag failures, compute κ | full ablation auto-judge sweep | KO+VI+EN auto-judge | §5/6 final numbers |
| 5/13 | finalize §4 protocol spec | finalize §5/6 with curves | finalize multilingual subsection | §3 method update |
| 5/14 | full pass review | full pass review | full pass review | §1/2/8 polish |
| 5/15 | preflight figures | reproducibility appendix | — | Pandoc → LaTeX |
| 5/16 | — | — | — | arXiv format compile + bib check |
| 5/17 | — | — | — | **arXiv v1 submit** |
| 5/18 | — | — | — | **Kaggle submit** |

---

## What this gets us by 5/17

- **Plan A**: a real protocol specification that any other research group can adopt. Citable artifact even at N=1.
- **Plan B**: a *quantitative*, *predictive* result (policy-frequency curve) that turns "we noticed a regression" into "we predicted and confirmed an LLM-fine-tuning law."
- **Multilingual demonstration**: pipeline runs on KO+VI+EN at minimum, supporting the generality claim.

This moves the paper from **"engineering hackathon companion"** to
**"workshop-ready empirical/methodological contribution"**. ACL Findings
upgrade still needs Sejong N=20 (Section 7), but the protocol + the
policy-frequency curve are real ML contributions a workshop reviewer
will recognize.
