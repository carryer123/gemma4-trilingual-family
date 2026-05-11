# 3. State-Gated Audit: Method

We frame LoRA evaluation as an *audit-before-promotion* problem. Given
candidate adapters $\{L_i\}_{i=1}^N$ trained on a shared base model
$M_0$, the pipeline records scalar metrics and explicit deployment
gates before any adapter is promoted. Held-out loss is retained as a
scalar objective; behavioral gates are deployment checks whose main
output is an action state.

## 3.1 Definition (gate-failing scalar pass)

**Definition 3.1.** Let $L$ be a LoRA adapter applied to base model
$M_0$. Let $\mathcal{V}$ be a held-out validation set with loss
$\ell(L; \mathcal{V})$ and let $\{G_k(L)\}_{k=1}^{K}$ be a fixed set of
*behavioral gates*, each a binary admissibility predicate measured on
a labeled probe set with explicit tolerance $\tau_k$. The adapter $L$
is a **gate-failing scalar pass** if there exists a stock-baseline adapter $L_0$
(possibly $L_0 = \emptyset$, i.e. the unfine-tuned base) such that

$$\ell(L; \mathcal{V}) < \ell(L_0; \mathcal{V}) \quad\text{and}\quad
\exists k:\; G_k(L_0) = 1 \;\wedge\; G_k(L) = 0.$$

That is, $L$ wins on loss but loses at least one gate that the base
already passed. The adapter is **audit-admissible** if all required
deployment gates pass; otherwise the audit routes it to review, repair,
or blocking.

Definition 3.1 is intentionally modest: a primary scalar metric can
improve while an uncaptured deployment state regresses. In this paper we
study one LoRA instance of that pattern.

## 3.2 Gate suite and probe mapping

For the KO/RU/EN case study we specify eight deployment states. The
released 30-probe discovery set is not an iid sample; it maps to seven
probe categories and several rubric dimensions. We therefore report the
mapping explicitly rather than implying that every gate has an equally
large independent probe set.

| Gate | Deployment state | Discovery evidence |
|---|---|---|
| G1 | translation/task behavior | 6 translation probes + held-out task metrics |
| G2 | cross-script discipline | 4 discovery probes; 52-probe rerun for 16 key adapters |
| G3 | JSON/schema discipline | 14 structured checks in the discovery harness |
| G4 | function-call validity | 4 function-call prompts |
| G5 | L1-aware grammar explanation | rubric dimension over grammar prompts |
| G6 | age-banded vocabulary/register | 4 age-band prompts |
| G7 | persona-bridge consistency | rubric dimension over family-scenario prompts |
| G8 | safety/refusal behavior | 4 safety prompts |

G2 is the only gate expanded in this paper. For a script-transfer prompt
with target script $s$, the dominant-character class of the output must
equal $s$. The original discovery run used a 4-probe smoke set; the
promotion audit expands this to 52 probes (4 directions × 13 lexical
surfaces) spanning KO→Cyrillic, RU→Hangul, KO→Latin, and RU→Latin.
This gate does not certify phonetic transliteration quality; it checks
whether the adapter remains in the requested output script.

The strict promote rule is the conjunction

$$\operatorname{promote}(L)=G_1(L)\wedge G_2(L)\wedge G_3(L)\wedge G_4(L)
\wedge G_5(L)\wedge G_6(L)\wedge G_7(L)\wedge G_8(L).$$

For deployment we report the rule as **triage**, not as a calibrated
detector:

* **GREEN**: all strict gates pass; adapter is eligible for deployment,
  with the gate version, raw generations, and scorer outputs logged.
* **AMBER**: one or more gates are close to threshold; adapter is not
  deployed automatically. The pipeline inspects raw outputs for the
  failed gate, labels the error mode, either adds a small targeted
  repair slice (20 examples per failed automatic gate in this
  instantiation) or records a deployment waiver, and reruns only the
  failed gates.
* **RED**: a gate is materially below threshold; adapter is blocked
  from promotion. Recovery requires rollback to a previous adapter,
  retraining with targeted data, or changing the deployment requirement
  before the adapter can re-enter the audit.

AMBER and RED are not silent overrides. AMBER permits documented repair
or a scoped waiver followed by failed-gate rerun; RED cannot be waived
unless the deployment specification itself changes and the full audit is
rerun.

This turns the gate scores into actions rather than a score-only report:

| State | Promotion action | Required record |
|---|---|---|
| GREEN | eligible for deployment | gate suite version + raw outputs + scorer hashes |
| AMBER | hold for review/repair/waiver; rerun failed gates | error label + repair data or signed waiver |
| RED | block promotion; rollback or retrain | failed gate, failed probes, recovery plan |

For G2-52 specifically, green means total $\ge 50/52$ and every
direction $\ge 12/13$; amber means total $\ge 48/52$ and every
direction $\ge 10/13$; red is anything below the amber floor. G3 remains
strict binary in this version ($\ge 8/14$ for promotion). We report a
G2 threshold-sensitivity table in §5.8.2 because these bands are
deployment thresholds, not calibrated statistical cutoffs. We argue in
§6.2 that the gates are non-redundant: fixing G2 does not fix G3, and a
safety-refusal pass says nothing about cross-script discipline.
This non-redundancy is why we do not collapse the suite into a scalar.

## 3.3 Case-study scope

We instantiate the audit on Gemma 4 E2B/E4B LoRA adapters for a
KO/RU/EN trilingual setting. Product architecture, demo UI, latency,
and server-tier behavior are out of scope for this paper; the analysis
is restricted to offline adapter audit outcomes.

## 3.4 Dataset construction

The training data is parameterized over a tuple $(L_1, L_2, B)$ of two
target languages and a bridge language. For the experiments reported
in §5 we use $(L_1, L_2, B) = (\text{KO}, \text{RU}, \text{EN})$, but
all data scripts are language-agnostic; we additionally produce
KO+VI+EN and KO+ZH+EN extension triples to verify the pipeline runs
unchanged on alternative corridors.

The dataset has three layers:

* **Direct translation pairs (Tatoeba CC-BY)**: 247 KO-RU, 11,385 KO-EN,
  810,219 RU-EN.
* **English-pivot trilingual triples**: 12,408 (KO, RU, EN) triples
  constructed by aligning KO and RU on a shared English midpoint and
  unfolded into six directional translation pairs at training time.
* **Synthetic learning artifacts** distilled from Gemma 4 E4B with a
  4-port parallelized Ollama pipeline and `format=json` enforcement:
  1,294 trilingual object cards (vocabulary + 4-direction phonetics +
  L1 contrast + per-role family cards) and 1,006 multi-turn family-
  scenario dialogs.

We additionally generate 300 explicit script-transfer training pairs
(G2 policy) for the policy-frequency arm, and 498
function-call template-expanded examples (G4 policy).

## 3.5 LoRA fine-tuning

All adapters are r=32 LoRA over q/k/v/o/gate/up/down projections, trained
with Unsloth 2026.5.2 on `unsloth/gemma-4-E2B-it` (a non-gated public
mirror), batch 2 × accumulation 4, learning rate 2e-4 cosine, bf16, 8-bit
AdamW. Hyperparameters are identical across all 15 ablation arms; only
the training data composition and the maximum step count vary.
The `train/` and `data/ablation/` directories of the repository contain
the exact runner script, all 9 data composition specifications, and the
pre-registration of the policy-frequency sweep.

## 3.6 Evaluation harness

The auto-judge harness loads each adapter through Unsloth's
adapter-aware loader (which resolves the base via the
`adapter_config.json` `base_model_name_or_path` field) and runs under
deterministic decoding. `prototype/eval/analyze_all_variants.py`
reproduces the original 30-probe discovery audit (including the
4-probe G2 smoke set) and emits the cliff curve and variant×gate table.
`prototype/eval/eval_g2_extended.py` reruns the paper-critical adapters
on the 52-probe G2 promotion set and writes selector-ready summaries to
`paper/figures/g2_extended_scores.json`.
