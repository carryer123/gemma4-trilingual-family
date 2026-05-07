# 6. Discussion and Limitations

## 6.1 Why a single-family case study is honest, not weak

We have repeatedly framed the Family-as-Evaluator protocol as a *case
study*: N=1 multicultural household, 30 stratified probes, three
evaluators with explicit roles (mother RU L1, father KO L1, child age
21 months as a non-verbal proxy). We anticipate three reviewer concerns
and address each.

**(C1) "N=1 has no statistical power."** True for any claim that requires
between-family generalization. We make no such claim in v1. Our claim is
narrower and stronger: *for at least one real multicultural household,
the deployed system on Gemma 4 E2B + LoRA introduces specific failure
modes that are invisible to BLEU and JSON-parse metrics.* That claim
is falsifiable — if no failure mode is found, the family-evaluator
returns clean ratings. We found three such modes (transliteration
regression, schema-label hallucination on `func_recommend_next`, and a
persona-bridge collapse on bilingual scenario probes), and we report
them with the prompt, the model output, and the rubric (Appendix D).

**(C2) "Auto-judge already finds these — why do you need humans?"** The
auto-judge in §5.2 caught the script-direction error because the *input*
explicitly demanded a target script. It did not catch (a) the
*"아무개"* hallucination in `func_recommend_next` (auto-judge passes the
JSON parse and key checks; only a human notices "아무개" is not an
animal), (b) the breakfast scenario where the LoRA-v1 output is *more*
plausible than stock but in a way only a Korean-L1 parent of a 21-month-
old can certify ("맘마 좀" is exactly what our toddler says), and
(c) the L1-aware refusal in Russian that is more useful than English to
a Russian-L1 user. These are positive signals that the model has
internalized our family context — but only the family can grade them.

**(C3) "The 'family' itself authors the paper, so evaluation is biased
toward the system."** Acknowledged. We mitigate by (a) publishing the
30-probe set verbatim with the rubric so any third-party multicultural
household can replicate, (b) reporting raw side-by-side outputs in
Appendix D so readers can re-grade, (c) committing to a five-family
panel via the Sejong Multicultural Family Centers in November 2026
(Section 7), with a pre-registered protocol that mirrors v1.

## 6.2 The bridge-pivot is a double-edged sword

The 50× expansion from 247 to 12,408 KO+RU+EN triples is the headline
quantitative result of §3.2.2. It is also the single largest source of
the *pivot hallucination* failure mode (§4.1). We did not filter for
round-trip semantic equivalence in v1. The KO and RU sentences in a
triple share an English midpoint, and English midpoints are
notoriously polysemous. A v2 plan (Section 7) is to use Gemma 4 26B as
a round-trip judge and prune triples whose KO→EN→RU back-translation
distance exceeds a learned threshold.

We expect this to remove 30–50% of triples (rough guess from spot
checks). The cost in quantity is acceptable because the bridge-pivot's
real value is *L1-aware lexical coverage*, not raw count.

## 6.3 What LoRA actually learned vs. what we intended

The auto-judge result (§5.2) and the failure-mode catalog (Appendix D)
together produce an unflattering but useful diagnosis: LoRA-v1 over-
fitted to the dominant data policy ("translate") at the cost of less-
represented policies ("transliterate", "obey enum schema in
function_call_hints", "respect already-learned-set in
recommend_next_word"). v2 adds 300 transliteration examples and we
quantify the recovery in §5.4.

We elevate this from anecdote to a testable claim, the
**policy-frequency hypothesis (PF-1)**: for any target policy *T* in
tension with a dominant training policy, LoRA regresses on *T*
relative to stock until *T*'s share of the training set exceeds a
critical fraction *f\**. Above *f\**, *T*-accuracy rises monotonically
and saturates. The transliteration sweep in §5.4 is the empirical
test of PF-1.

If PF-1 is confirmed, the practical rule is: when LoRA-fine-tuning an
LLM for a multilingual or multimodal niche population, *enumerate the
intended policies and budget every one of them at f\* or above*.
This is a stronger statement than the commonly-cited "more diverse data
is better" — it predicts the *direction* of regression below *f\** and
the *plateau* above it.

The rule generalizes the known instruction-tuning principle
[self-instruct] that *the lowest-frequency policy in your training data
is the lowest-quality policy in your model* by quantifying the regime
boundary. Multicultural-family co-learning has many such low-frequency
policies (transliteration, age-banding, persona-bridge selection,
schema-enum discipline), and FaE (§4) surfaces them efficiently as
candidates for the policy budget.

## 6.4 The premium tier is methodologically separate

The moon1 SoulX-FlashHead avatar tier (§3.1, Tier 2) is *not* part of
our family-as-evaluator quantitative results. It is included in this
paper because it is part of the deployed system and because the
talking-head + voice-clone +L1-aware accent persona is the headline
demo of the hackathon submission [hackathon]. It is *not* claimed as a
generalizable contribution. Reviewers may treat it as system-engineering
context. The MTP-drafter speedup (§5.4) is a reportable result on this
tier, but it stands on Google's MTP release [mtp-blog] and our
contribution is replication, not novelty.

## 6.5 Ethical considerations

**Child voice data.** The 21-month-old participant in our case study is
the child of two of the authors. No voice data leaves the device in
the phone tier. The premium tier streams video back from moon1 over a
Cloudflared tunnel that is private to the household. We do not retain
audio inputs after the LLM response is generated. No child voice data
appears in the released dataset.

**Parental coercion / co-learning power asymmetry.** We are aware that
"family co-learning" framings can subtly pressure the partner with
weaker target-language proficiency (in our case, the mother learning
KO). The UX explicitly avoids leaderboards, streaks, and any mechanism
that compares household members against each other. Future user-study
work (Section 7) should include a coercion-perception screening item.

**Bias in generated content.** The 26B-distilled object cards and family
scenarios reflect the cultural assumptions of the model's training data,
which may reproduce Korean-centric narratives even when the prompt is
RU- or EN-anchored. We saw this in early scenario distillations
(grandparent always referred to as 할아버지 even when the mother is RU
L1; for an RU-grandfather the term should be дедушка). v2 includes 100
explicit cross-cultural-appropriate scenario rewrites; v3 will sample
families across multiple structures.

**License of bridge-pivot data.** Tatoeba is CC-BY [tatoeba]. The
synthetic distillations are derived works of Gemma 4 26B (Apache 2.0).
We release the trilingual triple file under CC-BY following Tatoeba's
attribution requirement.

## 6.6 What this work is and is not

It *is*: an open-source on-device trilingual family-tutoring system
built around a publicly-released large model, plus a methodological
proposal (Family-as-Evaluator) for making the failure modes of such
systems visible.

It *is not*: a new model architecture, a new fine-tuning algorithm,
a generalizable dataset for arbitrary multicultural pairs, a clinical
study of family-language acquisition outcomes, or a population-level
claim about multicultural households.

We hope the *form* of the contribution (small N, rigorously documented;
open code and dataset; explicit failure-mode catalog) is useful to
practitioners who deploy LLMs for niche populations where automated
metrics under-specify the task.
