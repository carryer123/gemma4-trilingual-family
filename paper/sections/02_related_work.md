# 2. Related Work

## 2.1 Multilingual on-device LLMs

The trajectory from Gemma 1 [gemma1] through Gemma 3 [gemma3] to Gemma 4
[gemma4] tracks roughly two orthogonal axes: how *small* the smallest
useful variant is, and how *multimodal* it has become. Gemma 3n introduced
the Effective-Parameters family (E2B, E4B) targeting mobile inference, but
community reports surfaced quality regressions for non-English languages,
particularly Russian and Spanish, when the "n" mobile variant was used
[gemma3n-discussion]. Gemma 4 inherits the E2B / E4B taxonomy but reports
substantially larger multilingual training data (140+ languages
pre-training, 35+ languages out-of-the-box [gemma4-card]) and adds native
**audio** input on E2B / E4B. Our baseline measurements (Section 5) confirm
the regression is largely fixed: KO↔RU translation, KO grammar, and Russian
explanation of Korean particles are all coherent on stock Gemma 4 E2B.

The MTP drafter release [mtp-blog] is significant for our use case: a
76M-parameter draft model achieves up to 3× speculative-decoding speedup
on the 26B target while sharing the target's KV cache and activations. We
use this drafter on the moon1 server tier to keep the live-avatar latency
budget below 300ms.

## 2.2 Bridge-language pivot for low-resource pairs

Pivot translation via a high-resource bridge (typically English) is a
standard recipe in low-resource MT [pivot-mt]. It has been extended to
unsupervised cross-lingual alignment [unsupervised-mt], multilingual
embedding [labse], and to bootstrap parallel corpora for related language
pairs [bridge-corpus]. The KO-RU pair is genuinely low-resource in
publicly-aligned data: Tatoeba [tatoeba] yields only 247 directly-linked
KO-RU sentences, against 11K KO-EN and 810K RU-EN. Pivoting expands our
KO-RU coverage to 12,408 trilingual triples (50×). Critically, prior
bridge-pivot work primarily evaluates *translation accuracy on test sets*;
we evaluate the *downstream usefulness* of pivot triples for fine-tuning
a multimodal family-tutor LLM, including failure modes (Section 4) that
do not appear in BLEU-style evaluation.

## 2.3 Family / group / co-learning HCI

A non-trivial body of work studies *family* technology design [family-hci],
intergenerational learning, and parent-child co-engagement with screen
media. The language-tutoring sub-genre, however, is dominated by *single-
learner* assumptions. Duolingo and Babbel structure progress around an
individual streak; even shared-account products treat each session as
isolated. Park & Lee 2023 [coco-learning-2023] piloted a cohabitation-
language-app with two simultaneous learners but did not handle pre-literate
participants. Our system explicitly treats household members with
asymmetric L1s and asymmetric literacy as a *single co-learning unit* and
designs UX, data, and metrics around that.

## 2.4 Talking-head avatars

Real-time text-to-portrait video generation has matured rapidly:
SadTalker [sadtalker], EMO [emo], LatentSync [latentsync], and the
SoulX-FlashHead lineage [soulx-fh]. Of these, SoulX-FlashHead Lite is
distill-trained to render at ~3× the speed of larger talking-head DiTs
on a single RTX 3090, which is what lets us host a *premium* avatar tier
on a single server. The complementary work in 3D Gaussian Splatting
real-time avatars [gaussian-avatars] is approximately one hardware
generation away from on-device deployment for our use case; we considered
it and rejected it (Section 3) per direct experimentation by one of the
authors.

## 2.5 LLM evaluation: beyond automatic metrics

The limitation of BLEU [bleu] for capturing meaning has been argued for
two decades. More recent benchmarks rely on COMET [comet], BLEURT [bleurt],
or LLM-as-judge protocols [llm-as-judge]. Each has known blind spots.
LLM-as-judge in particular can systematically reproduce the biases of the
judge model. For a niche population (multicultural household, pre-literate
child, RU-L1 mother), these proxies fail. Our Family-as-Evaluator (Section 4)
is small-N (N=1 family) by design, in the same spirit as a *case study*
in HCI: we trade statistical power for ground-truth fidelity, and propose
a future-work pathway (Section 7) to scale through partner
Multicultural Family Centers network [family-centers].

## 2.6 Inheritance from Paper 1 (DFT-AI)

The methodological stance of *demanding parity audits beyond observable
metrics* is inherited directly from our group's Paper 1 [bnml-paper1] on
DFT-AI scientific engines. There, observable benchmarks (lattice constant,
band gap, DOS) appeared to pass while wavefunction state-parity audits
revealed hidden cancellations between independently-broken
convention/normalization paths. The audit recovered Si USPP wavefunction
state parity. Here, the analogue is that BLEU and JSON-schema parse rate
appear to pass while a 30-probe family audit reveals transliteration-
direction errors, schema-label hallucinations, persona-bridge collapses,
and age-band leakage (Section 4). The cross-domain message is the same:
*observable success ≠ real success; instrument for the parity that
matters before claiming progress*.
