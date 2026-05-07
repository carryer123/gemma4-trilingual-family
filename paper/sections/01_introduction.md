# 1. Introduction

> *“Hand me your son, please. Сладкий, мама очень тебя любит.”*
> — Real morning utterance, KO-RU-EN trilingual household, May 2026.

Multicultural marriages are no longer a marginal demographic. South Korea
records ~170,000 marriage-immigrant women as of 2024 [KOSTAT]; globally,
international migration crossed 285M people in the same year [UN DESA]. In a
typical international-marriage household, **three or more languages are alive
simultaneously**: the parent who immigrated retains an L1, the resident parent
keeps another, the couple often defaults to a third *bridge* language for
day-to-day adult conversation, and the child grows up code-switching among
all three with no formal instruction. The technology stack purpose-built for
this reality, however, does not exist. Today's leading mobile language-learning
products — Duolingo, Babbel, Rosetta Stone, Papago — assume a *monolingual,
literate, single-user* model: one learner, one source language, one target
language, written input. They do not handle:

1. **Co-learning**: two or more household members studying *each other's* languages
   in the same session, on the same device, at the same time.
2. **L1-aware coaching**: explanations that exploit the learner's actual L1
   (e.g., contrasting Korean particles -에 / -에서 against Russian locative
   prepositions, in Russian, for an RU-L1 learner).
3. **Pre-literate users**: a 21-month-old child cannot read Cyrillic, Hangul,
   or the Latin alphabet, yet is the most language-acquisition-active member
   of the household.
4. **Offline operation**: families with intermittent connectivity, or who
   prefer not to send home-life voice and image data to a cloud, are excluded
   by API-based products.

We argue that the recent release of **Gemma 4** (Google DeepMind, April 2026
[gemma4-blog]) represents a phase change for this problem. Specifically:
the *E2B* and *E4B* edge variants run entirely on a smartphone with 2–4 GB
RAM, support text + image + **audio** input natively, generate JSON-structured
outputs reliably, and are released under Apache 2.0. Combined with the
recently-released 76M-parameter **Multi-Token-Prediction (MTP) drafter**
[mtp-blog], which delivers ~3× speculative-decoding speedup with no quality
loss, the technical preconditions for "free, offline, on-device, multimodal,
multilingual, family-scale" AI tutoring are met for the first time.

The contributions of this paper are:

* **C1. Trilingual co-learning system** with on-device E2B as the primary
  inference path and a moon1-hosted 26B + SoulX-FlashHead avatar as a
  *premium sidecar*, accessible only when the household opts in. The
  architecture is single-failure-tolerant: the cloud sidecar can drop and
  the phone retains full functionality.
* **C2. Bridge-pivot data augmentation**. From 247 direct KO-RU pairs in
  Tatoeba [tatoeba] we construct 12,408 trilingual KO+RU+EN triples by
  pivoting through English alignments — a 50× expansion. We further generate
  ~3K synthetic learning artifacts (object cards, family scenarios) by
  distilling Gemma 4 26B with the MTP-accelerated pipeline running on
  4× A100 80GB.
* **C3. Family-as-Evaluator protocol**. We argue that BLEU and perplexity
  are systematically blind to the kinds of failures that matter in family
  tutoring (transliteration direction, schema-label hallucination, age-band
  leakage, persona-bridge collapse). We design and report a 30-probe
  evaluation set scored by an actual KO-L1 / RU-L1 / EN-bridge multicultural
  household with a 21-month-old child, surfacing failure modes invisible to
  automatic metrics.
* **C4. Open release**. Code (Apache 2.0), the trilingual KO+RU+EN dataset,
  the LoRA adapter, and the Family-as-Evaluator probe set are released with
  the paper. The mobile app is released as an APK and a public source
  repository.

Throughout the paper we adopt a stance inherited from Paper 1 of our group's
DFT-AI work [bnml-paper1]: *observable benchmark success is not parity with
real success*. There, the lesson was that wavefunction state-parity audits
revealed hidden cancellations in superficially-passing density-functional
benchmarks. Here, the analogue is that human-as-evaluator audits reveal
hidden hallucinations in superficially-passing translation and JSON-schema
benchmarks. The technical fix in both cases is the same: instrument for
the parity that matters, and demand it before claiming progress.

The rest of the paper is structured as follows. Section 2 surveys related
work in multilingual LLMs, talking-head avatars, and family-language-tutoring
HCI. Section 3 describes the system architecture, dataset construction, and
LoRA training. Section 4 introduces the Family-as-Evaluator protocol and the
failure-mode catalog it surfaces. Section 5 reports translation-quality
ablations, schema adherence, latency, and a bridge-pivot data-augmentation
ablation. Section 6 discusses limitations (N=1 family, IRB scope, voice-data
locality). Section 7 outlines future work tied to a regional content
program (Section 7).
