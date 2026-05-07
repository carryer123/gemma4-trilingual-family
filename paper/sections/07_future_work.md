# 7. Future Work and the Sejong Pipeline

The current paper is the v1 of a multi-stage program. We outline the
concrete next four milestones, each tied to a delivery date and a
funded program.

## 7.1 Milestone M1: LoRA-v2 + transliteration fix (this week)

LoRA-v2 retrains on `train_v2.jsonl` (20,513 examples), adding the 300
explicit transliteration pairs (§3.2 + Appendix B). Target metrics
(carried into Section 5 of arXiv v2):

* Transliteration script-correct: from 1/4 (LoRA-v1) → ≥ 4/4 (predicted)
* JSON parse: from 7/14 (LoRA-v1) → ≥ 12/14 (predicted)
* Empty responses: hold at 0/30
* No regression on translation BLEU (Flores-200 KO↔RU and KO↔EN held-out)

Delivery: arXiv v2 by 2026-05-18 (hackathon submission deadline).

## 7.2 Milestone M2: Sejong Family Center N=20 panel (Aug-Nov 2026)

A 2026 Sejong Regional Specialized Content Development support
program (세종 지역특화콘텐츠개발지원사업) proposal was filed on
2026-04-09 with this exact product as the deliverable, providing the
funding pipeline for the N=20 family-center scaling described below. The 11-month program runs 2026-05 to 2026-12
and includes mid-term review in August and final review in November.
Total budget 111.2M KRW (100M public + 11.2M company-matched).

The work plan submitted to Sejong includes a *family-center pilot* with
the Sejong Multicultural Family Center (다문화가족지원센터). We commit
to recruiting **N=20 multicultural households**, stratified by maternal
L1 (Russian, Vietnamese, Mandarin Chinese, Thai, Uzbek, Mongolian,
Filipino), each with at least one child aged 0–8. Each household runs
the 30-probe Family-as-Evaluator protocol once per month for three
months. This produces ~1,800 ratings (20 households × 30 probes ×
3 months), which is more than enough statistical power for
between-language-pair comparisons and within-household longitudinal
trends.

Delivery: arXiv v3 by 2026-12, with the full panel as Section 5 update.
Submission target: ACL Findings 2027 spring or CHI 2027 (whichever has
the closer deadline at the time).

## 7.3 Milestone M3: A multilingual generalization beyond KO+RU+EN

The training pipeline (Section 3.2) is L1-agnostic. The bridge-pivot
expansion works for any target ↔ bridge ↔ second-source triple. We
plan three additional language sets, each covering a Korean
multicultural-family demographic:

| Triple | Bridge | Estimated Tatoeba pairs after pivot |
|---|---|---|
| KO + Vietnamese + EN | EN | ≈ 8,500 (estimated from VI-EN counts) |
| KO + Mandarin Chinese + EN | EN | ≈ 12,000 |
| KO + Mongolian + RU/EN dual | RU+EN | ≈ 4,000 |

The Mongolian case is doubly bridged (RU and EN share many
Mongolian-bilingual speakers in Korea); we plan to test whether dual-
bridge augmentation improves over single-bridge.

## 7.4 Milestone M4: Voice-modality evaluation and on-device latency

We have not yet evaluated Gemma 4 E2B's native audio-input modality
under a child-speech distribution shift. Children's speech, especially
21-month-old utterances, is acoustically very different from adult
speech that ASR is typically trained on, including Gemma 4's audio
encoder. We plan a small (N=4 children, 100 utterances each) child-
speech eval set, hand-transcribed, with the family centers. This will
inform whether E2B's native audio is sufficient or whether a child-
fine-tuned audio LoRA is needed.

In parallel, we will benchmark the on-device latency budget on a real
phone (Pixel 9 Pro / Galaxy S25 with Snapdragon 8 Elite NPU). The A100
inference numbers in §5 are upper bounds; phone NPU inference will be
≈3–5× slower in raw tokens/s but with substantially lower memory
pressure thanks to MediaPipe's int4 weight quantization.

## 7.5 The Sejong → arXiv → Findings → Journal ladder

The intended publication ladder (separate from the hackathon
submission, which is unaffected by review timing):

| Version | Target | Date | New material |
|---|---|---|---|
| arXiv v1 | preprint + hackathon | 2026-05-17 | base paper |
| arXiv v2 | LoResMT or MRL workshop | 2026-06 | LoRA-v2, human eval N=1 final |
| arXiv v3 | ACL Findings or CHI | 2026-12 | Sejong N=20 panel + 3 more language triples + child speech eval |
| arXiv v4 | Computer Speech & Language journal | 2027 spring | 6-month longitudinal, IRB clear, full statistical analysis |

Each level requires substantially new material (≥ 30%) per ACL and
journal extension policies, satisfied by the milestones above.

## 7.6 IP and content extension (deployment context)

The Sejong proposal (referenced above) extends the system to character
IP — Sejong-i (세종이), Tomi (또미), Mallangi (말랑이) — plus webtoons,
workbooks, sticker books, and Hangul play kits. These are out of scope
of the LLM paper but coexist with it: the LLM generates the dialog,
the IP renders the visual world, and the print products (in
collaboration with 미래엔 세종공장 [mirae-en]) make the service
tangible to households without smartphones. We treat this as
deployment context, not a scientific claim.

## 7.7 Long-term: from one family to a public infrastructure

The strategic question is whether the *Family-as-Evaluator* methodology
itself, separate from the trilingual app, can become a reusable
evaluation infrastructure. Multicultural family centers exist in every
Korean city. A small standardized 30-probe rubric per language triple,
graded by recruited households monthly, would constitute the first
systematic public-good evaluation set for niche-population LLMs.
We will discuss this with the Sejong Multicultural Family Center
and the Korea Institute for Healthy Family (한국건강가정진흥원) during
the Sejong program's mid-term review.
