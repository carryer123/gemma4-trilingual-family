---
title: Trilingual Family Tutor (Gemma 4)
emoji: 🏡
colorFrom: indigo
colorTo: pink
sdk: gradio
sdk_version: 4.39.0
app_file: app.py
pinned: false
license: apache-2.0
short_description: KO+RU+EN family co-learning on Gemma 4 E2B + LoRA
---

# Trilingual Family Tutor — KO + RU + EN

Gemma 4 E2B (Apache 2.0) fine-tuned with a r=32 LoRA adapter for a real
multicultural household with two parental L1s (Korean and Russian), an English
bridge between the parents, and a 21-month-old Korean-L1 child.

## What this demo shows

Five tabs, each one a category from the **Family-as-Evaluator (FaE) protocol**
released alongside the [companion paper](https://arxiv.org/abs/[id]):

1. **Translation** — KO ↔ RU ↔ EN, any direction
2. **Trilingual object card** — one Korean object → JSON learning card with
   3-language word + 4-direction phonetic + L1 contrast notes + per-role
   parent / child cards
3. **Family scenario** — daily-life situation + age band + parent KO level +
   bridge → JSON multi-turn dialog where every family member practices
4. **L1-aware grammar** — explain a target-language grammar concept in the
   learner's L1, with concrete contrast examples
5. **Cross-script transliteration** — KO ↔ {Cyrillic, Hangul, Latin}

## Why this exists

170,000+ marriage-immigrant women in Korea today live in households with three
or more languages. No mainstream language-tutoring product handles two
parents, a pre-literate child, and a bridge language — they all assume one
literate, monolingual user. We built one for our own family and released it
under Apache 2.0.

## Resources

- [GitHub repository](https://github.com/[author]/gemma4-trilingual-family) (Apache 2.0)
- [arXiv preprint](https://arxiv.org/abs/[id])
- [FaE protocol specification](https://github.com/[author]/gemma4-trilingual-family/blob/main/tools/fae_protocol/SPEC.md) (CC-BY 4.0)
- [Hackathon write-up](https://github.com/[author]/gemma4-trilingual-family/blob/main/HACKATHON_SUBMISSION.md)
- [Demo video](https://youtube.com/watch?v=[id])

## Authors

- **Byoungsang Lee** (이병상) — SKKU School of Advanced Materials Science and Engineering, MoonTechnology
  — first author, system / model / paper
- **Prof. Jung Heon Lee** (이정헌) — SKKU School of Advanced Materials Science and Engineering, SKKU Department of MetaBioHealth
  — corresponding author, supervision
  — jhlee7@skku.edu

ORCID: Byoungsang Lee 0000-0001-6874-0935 · Jung Heon Lee 0000-0003-4790-3525

## License

- Code: Apache 2.0
- LoRA adapter weights: Apache 2.0
- Trilingual dataset (KO+RU+EN triples): CC-BY 4.0 (inherits Tatoeba)
- FaE protocol specification: CC-BY 4.0

## Build context — the experimental program

This demo runs **LoRA-v2**, the second of two LoRA fine-tunes we trained.

* LoRA-v1 (18,043 examples, no transliteration data) regressed on
  cross-script transliteration accuracy from 100% to 25% — invisible to
  BLEU, JSON-parse rate, and perplexity. Caught only by the
  Family-as-Evaluator audit (Appendix D of the paper).
* LoRA-v2 (20,513 examples, +300 explicit transliteration pairs) restored
  100% transliteration accuracy while keeping the wins of v1 (zero empty
  responses, family-context realism, L1-aware refusals).
* This is the [policy-frequency hypothesis (PF-1)](https://github.com/[author]/gemma4-trilingual-family/blob/main/paper/sections/06_discussion.md#63-what-lora-actually-learned-vs-what-we-intended)
  in action.

You are looking at v2. Try the cross-script transliteration tab — it should
produce *script-correct* output, not *translation*.
