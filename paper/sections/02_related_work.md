# 2. Related Work

## 2.1 Multilingual on-device LLMs

The trajectory from Gemma 1 [gemma1] through Gemma 3 [gemma3] to Gemma 4
[gemma4] tracks two axes relevant to this work: small deployable variants
and broad multilingual/multimodal coverage. Community reports on earlier
mobile-oriented Gemma variants surfaced non-English regressions
[gemma3n-discussion], which motivates treating multilingual behavior as a
deployment state to be audited rather than assuming it follows from model
family membership. Our baseline measurements in §5 show that stock Gemma
4 E2B is strong on the tested KO/RU/EN prompts; the gate-failing case
appears after LoRA selection, not in the base model.

## 2.2 Bridge-language pivoting

Pivot translation via a high-resource bridge is a standard recipe in
low-resource MT [pivot-mt]. It has been extended to unsupervised
cross-lingual alignment [unsupervised-mt] and multilingual embedding
[labse]. The KO-RU pair is low-resource in publicly aligned data:
Tatoeba [tatoeba] yields only 247 directly linked KO-RU sentences,
against 11K KO-EN and 810K RU-EN. Pivoting expands our KO-RU coverage to
12,408 trilingual triples. Prior bridge-pivot work primarily evaluates
translation accuracy; we evaluate whether adapters trained on these
mixes remain admissible under deployment gates.

## 2.3 Case-study evaluation

Family-technology research has long argued that household systems should
be evaluated in the social setting where they are used [family-hci].
Language-tutoring products, however, are usually evaluated as
single-learner systems. Our contribution is not a population HCI study:
the household setting supplies a concrete deployment specification, and
the protocol explicitly limits N=1 evidence to Tier 1 existence claims.

## 2.4 Automatic metrics and judges

BLEU [bleu], COMET [comet], BLEURT [bleurt], and LLM-as-judge protocols
[llm-as-judge] are useful, but each can miss state violations that are
not represented in the test distribution or judge rubric. In our setting
the relevant failures include source-script echo, JSON enum drift,
persona-bridge collapse, and age-band register mismatch. State-gated
promotion complements automatic metrics by making these deployment
constraints explicit before adapter promotion.

## 2.5 Deployment-specific evaluation

The broader tutoring product context is intentionally out of scope for the
paper's empirical claims. We use the deployment setting only to define which
adapter states must be audited before promotion.
