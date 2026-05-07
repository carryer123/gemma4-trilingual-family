# Kaggle Gemma 4 Good Hackathon — Submission Package

**Title**: Beyond BLEU — Trilingual L1-Aware On-Device Family Tutoring with Gemma 4

**Track**: Education (with Digital Equity dual-tag)

**Team**: Byoungsang Lee (SKKU AdvMat + MoonTechnology) and Prof. Jung Heon Lee (SKKU AdvMat + SKKU MetaBioHealth) — single-family case study

**Final submission deadline**: 2026-05-18 23:59 UTC

---

## The 5 required components

### 1. Working demo

**Phone tier** (mobile demo, primary):
- Android APK link: [TBD GitHub release]
- Built on MediaPipe LLM Inference + Gemma 4 E2B int4
- Camera → trilingual learning card; voice → trilingual response
- Function calling: pronunciation score / next-word recommendation /
  L1-aware grammar explanation / age-mode switch / safety flag
- Runs entirely offline, Apache 2.0, no token cost ever

**Premium tier** (live avatar, optional):
- moon1.local (RTX 3090) hosting Gemma 4 26B + 76M MTP drafter
- SoulX-FlashHead Lite avatar with L1-aware accent persona
- ElevenLabs-cloned Russian-accented Korean teacher voice
- Streamed to phone via Cloudflared HTTPS tunnel

### 2. Public code repository

**GitHub**: `gemma4-trilingual-family` (Apache 2.0)
- Full LoRA training pipeline (Unsloth + PEFT + TRL)
- Bridge-pivot dataset construction (Tatoeba → 12,408 KO+RU+EN triples)
- Distillation pipeline (Gemma 4 E4B/26B via 4× Ollama instances)
- Family-as-Evaluator probe set (30 probes)
- Auto-judge harness for LoRA vs. stock comparison
- Android skeleton + moon1 wire (FastAPI) stub

### 3. Technical write-up

`paper/main.md` — full 30-page technical paper, also at arXiv:[TBD].
Sections covered:
1. Introduction (multicultural family demographic, our family case study)
2. Related work (Gemma 4, bridge-pivot MT, family HCI, talking-head)
3. **Method** (system arch, dataset, LoRA, MTP)
4. **Family-as-Evaluator** (the methodological contribution)
5. Experiments (LoRA-v1 vs. stock auto-judge — incl. transliteration regression finding)
6. Discussion (N=1 case-study honesty, ethical considerations)
7. Future work (Sejong Multicultural Family Center N=20 panel, late 2026)
8. Conclusion

Plus appendices A (dataset), B (hyperparameters), C (probes), D (failure gallery), E (reproducibility).

### 4. Demo video (5 minutes)

Storyboard:
- **0:00–0:30** Intro — our trilingual family at the breakfast table.
  Father speaks Korean to baby, English to wife. Wife speaks Russian
  to baby, English to husband. Single shot. Caption: *"Three languages,
  one home. No app handles this."*
- **0:30–2:00** Phone tier core. Wife points camera at apple. Phone
  shows trilingual card (사과 / яблоко / apple) + Cyrillic transliteration
  of "사과" + age-banded child card. Wife taps "RU bridge" — explanation
  switches to Russian. Wife taps "EN bridge" — explanation switches to
  English (because she speaks English with husband). Father tries the
  same with кошка (Russian for cat) — phone shows Hangul transliteration
  he can pronounce.
- **2:00–3:00** Voice path. Wife speaks Russian — phone responds
  trilingually. Baby speaks one toddler word — phone responds with
  developmental encouragement. Father uses
  `recommend_next_word` — three concrete next-vocabulary suggestions.
- **3:00–4:30** Premium toggle. Avatar of an *RU-L1 Korean teacher*
  appears (deliberate Russian accent in Korean speech). Wife has a
  short live conversation in Korean with the teacher. The teacher
  switches to English when wife requests. The avatar's lip-sync, facial
  micro-motion, and L1-aware accent are visible.
- **4:30–5:00** Generalization. Map of Korea overlaying multicultural
  family statistics (~170K marriage-immigrant women). Closing line:
  *"Russian, Vietnamese, Mandarin, Mongolian — same code path. Apache
  2.0. Free. Offline. Family-evaluated."*

### 5. Cover image / media gallery assets

- 6 still images: family at table, phone showing trilingual card,
  premium avatar, dataset-pivot diagram, training loss curve, failure
  gallery snippet
- 3 short clips (10 s each) for social/marketing reuse

---

## Why this should win or get a track prize

### Education track
- **Real social need**: 170,000+ multicultural marriage-immigrant women
  in Korea alone; globally 285M international migrants — none served
  by single-learner products.
- **Glass-floor accessibility**: Apache 2.0 + offline E2B + free OS TTS
  = $0 / month per family. The Sejong Family Center pilot pipeline
  (paper §7.2) brings this to public-good infrastructure.
- **Pre-literate inclusion**: 0–2 age band fully supported via
  audio + image, no reading required.

### Digital Equity track (dual tag)
- Multicultural-family digital divide is a top-ranked policy priority
  in Korea (한국건강가정진흥원 reports). Our software is *the* first
  trilingual co-learning tool addressing it.
- Apache 2.0 release means any city's family-center can adopt without
  procurement.

### Technical track
- **Bridge-pivot 50× data augmentation** (247 → 12,408 triples) with
  rigorous license traceability (Tatoeba CC-BY).
- **22× distillation throughput speedup** discovered empirically
  (`think:False` + 4-GPU round-robin) — a free systems lesson for any
  Ollama-based pipeline.
- **76M MTP drafter** integration with the SoulX live-avatar tier.
- **Family-as-Evaluator** rubric — a transferable methodology for
  niche-population LLM evaluation.

### Unsloth $10K special prize
- Every fine-tune (v1 + v2) is **Unsloth-only**, including the
  patch-around-datasets-version diagnosis (Appendix B.7) — exactly the
  kind of practical Unsloth use the prize seems aimed at.
- `unsloth/gemma-4-E2B-it` mirror as the base = explicit Unsloth
  ecosystem reliance.

### Surprise finding (judge-friendly)
- Our LoRA-v1 *regressed* on transliteration script-direction (100% →
  25%) while improving on family-context realism. We caught it,
  diagnosed it, and fixed it in LoRA-v2 with 300 explicit transliteration
  examples — and we documented all of this transparently. Judges
  rewarding intellectual honesty over claimed-monotonic-improvement
  should appreciate this.

---

## Submission checklist (5/16–5/18)

- [ ] arXiv preprint submitted by 2026-05-17 12:00 UTC
- [ ] GitHub repo public (Apache 2.0) by 2026-05-17 18:00 UTC
- [ ] HuggingFace dataset card live by 2026-05-17 18:00 UTC
- [ ] HuggingFace LoRA adapter live (v2) by 2026-05-17 22:00 UTC
- [ ] Demo APK signed and uploaded by 2026-05-18 06:00 UTC
- [ ] 5-minute demo video uploaded (YouTube or similar) by 2026-05-18 12:00 UTC
- [ ] Kaggle submission form filled by 2026-05-18 20:00 UTC

---

## Contact

First author: Byoungsang Lee (SKKU School of Advanced Materials Science and Engineering, MoonTechnology) — carryer12345@gmail.com
Corresponding author: Prof. Jung Heon Lee (SKKU School of Advanced Materials Science and Engineering, SKKU Department of MetaBioHealth) — jhlee7@skku.edu
