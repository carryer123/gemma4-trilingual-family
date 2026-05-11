# Paper Outline — Trilingual L1-Aware Family Co-Learning with On-Device Gemma 4

**Target venue**: arXiv (cs.CL or cs.HC) — submission target **2026-05-17 (대회 마감 1일 전)**
**Co-submission**: Kaggle Gemma 4 Good Hackathon
**Estimated length**: 8-10 pages + appendix

---

## Inheritance from Paper 1 (NMI BNML)

Paper 1 의 핵심 narrative 차용:

| Paper 1 (DFT) | This paper (LLM) |
|---|---|
| Observable benchmark = state-parity 보장 X | BLEU/perplexity = real co-learning quality 보장 X |
| Convention 오류가 상쇄돼 통과 (hidden failure) | Pivot 으로 만든 triple 의 의미 일치 ≠ 표면 매칭 (hidden failure) |
| Agentic forensic workflow 로 발견 | Family-as-evaluator (와이프 RU L1 + 아기 1세 9개월) 로 발견 |
| Si USPP wavefunction state parity 복구 | L1-aware LoRA 로 진짜 co-learning 복구 |
| State-of-the-art 가 아니라 "어떻게 믿을 수 있게 만드는가" | 같은 메시지 |

→ "Beyond surface metrics, towards trustable on-device family AI."

---

## Title (후보)

1. **"Beyond BLEU: Family-as-Evaluator for Trilingual L1-Aware On-Device Tutoring"**
2. **"Pivot Hallucination: Why English-Bridged Trilingual Augmentation Needs State-Parity Audit"**
3. **"From 247 to 12,408: Bridge-Pivot Data Augmentation for KO-RU Family Co-Learning, and Its Hidden Failure Modes"**

데모 가족 narrative 살리려면 1번이 강함. 학술적 contribution 우선이면 2번. 데이터 기여 우선 3번.

**잠정 채택: 1번**

---

## Abstract (drafting)

> Multicultural families (e.g., parent–parent and parent–child speaking different
> first languages) are a fast-growing population worldwide, yet existing language
> learning apps treat each user as a monolingual learner. We present a trilingual
> KO+RU+EN co-learning framework built around Gemma 4 E2B running entirely on a
> mobile device, augmented with a moon1-hosted SoulX-FlashHead avatar premium tier.
> The core technical contributions are: (1) a 50× data augmentation from 247
> direct KO-RU pairs to 12,408 trilingual triples via English-pivoted alignment;
> (2) a 76M MTP-drafter accelerated 26B distillation pipeline that produces 1,500
> trilingual object cards and 1,500 family-co-learning scenarios with strict JSON
> schema enforcement; (3) Family-as-Evaluator, a small but stratified evaluation
> set scored by an actual KO-L1 / RU-L1 / EN-bridge multicultural household
> with a 21-month-old child, exposing failure modes invisible to BLEU and
> perplexity (e.g., transliteration-direction errors, schema-label hallucination,
> bridge-leakage). We release the dataset, the LoRA adapter for E2B, and the
> on-device app under Apache 2.0.

---

## Sections

### 1. Introduction

- 다문화가정 통계 (한국 17만 결혼이주여성, 글로벌 285M international migrants)
- 기존 앱 한계: 1인용 가정, L1-blind, 글 못 읽는 아기 미지원
- 왜 trilingual? 부부 공통어 EN 이 *bridge* 로서 학습 다리이자 데이터 다리
- 우리 기여 4가지

### 2. Related Work

- LLM family/group tutoring (제한적)
- Bridge-pivot translation augmentation (NLLB-200, Flores-200)
- On-device multilingual LLM (Gemma 3n 의 RU 약점, Gemma 4 의 회복)
- L1-aware language tutoring (대부분 영어 기반)
- Avatar talking head (SoulX, LatentSync, Hallo-Live)

### 3. Method

#### 3.1 System Architecture
- Phone-only 메인: Gemma 4 E2B (2B effective, Apache 2.0, MTP-accelerated)
  - Camera → image → trilingual card
  - Audio (RU/KO/EN) → ASR (E2B native) → trilingual response
  - Function calling: score_pronunciation, recommend_next_word, explain_in_l1, switch_age_mode, daily_mission
  - OS TTS for output (free, offline)
- Premium sidecar: moon1 (RTX 3090) Gemma 4 26B + 76M drafter + SoulX-FlashHead
  - Live avatar persona (RU-L1-aware KO teacher with deliberate accent)
  - cloudflared HTTPS tunnel

#### 3.2 Dataset
- Trilingual core (~14K)
  - Tatoeba KO-RU 247
  - Tatoeba KO-EN 11,385
  - Tatoeba RU-EN 810,219
  - **English-pivot triples**: 12,408 (50× augmentation)
- Synthetic (~3K, 26B distill)
  - Object cards 1,500: trilingual word + 4-direction phonetic + L1 contrast + family card per role
  - Family scenarios 1,500: 50 daily situations × 4 ages × 3 KO levels × 2 bridges
- Function calls 500 (template-expanded seed)
- Total ~17K + scenario expansion

#### 3.3 LoRA Fine-tuning
- E2B-it base, r=32 LoRA, ~2% trainable
- 2 epochs, lr=2e-4 cosine, bf16, A100×1 ~1hr/epoch
- Schema-constrained JSON via vLLM guided decoding at eval time

#### 3.4 MTP Drafter Integration
- 76M drafter sharing KV/activations with target
- llama.cpp + Ollama benchmark (token/s vs solo)

### 4. Family-as-Evaluator

가장 학술적 기여 영역:

- **Why automatic metrics fail**:
  - BLEU: 표면 토큰 일치, 가족 학습 적합성 측정 불가
  - Perplexity: 자연성 측정, 교육성 X
  - GPT-4 judge: bias 있고 가족 컨텍스트 모름
- **Our protocol**:
  - 30 stratified probes (translation, grammar, scenario, function call, contrast)
  - 3 evaluators with explicit role:
    - Wife (RU L1, EN bridge, learning KO) → 자연스러움 + L1 적합성
    - Husband (KO L1, learning RU) → 같은 양방향
    - Child (1세 9개월 KO L1) → 발화 반응 + attention span
  - 5점 척도 + free-text comments
- **Hidden failure modes uncovered**:
  - Pivot hallucination: KO triple 의 일부가 EN-RU 매칭 우연
  - Schema label leak: explanation_in 필드를 라벨 대신 텍스트로 채움 (E2B에서 관찰)
  - Cross-script transliteration direction error: ru_in_hangul 이 키릴로 출력 (E2B)
  - Persona-bridge collapse: bridge=EN 으로 요청해도 RU 로 답하는 경우
  - Age-band leakage: 0-2세 모드에서 추상 어휘 등장
- **Quantitative**: human-eval ratings vs BLEU 상관계수, ablation by feature

### 5. Experiments

#### 5.1 Translation quality
- Flores-200 KO↔RU/EN/RU-EN BLEU/COMET, baseline E2B vs LoRA

#### 5.2 Family scenario quality (Family-as-Evaluator)
- 30 probes × 3 evaluators × 5점 = 450 ratings
- E2B vs E4B vs 26B vs E2B+LoRA

#### 5.3 Function-call adherence
- Schema parse rate, argument validity, on held-out 100

#### 5.4 Latency
- E2B on phone (estimated via A100 → mobile NPU mapping)
- 26B + drafter on RTX 3090 (실측)

#### 5.5 Ablation: Bridge pivot vs direct only
- LoRA on (Tatoeba KO-RU 247) only vs (with 12,408 EN-pivot triples)

### 6. Discussion / Limitations

- N=1 가족 evaluator 한계 → 후속에 family panel 5개 (한국 다문화가족지원센터 협업; Section 7 future work)
- 1세 9개월 아기 reaction 측정의 statistical power 제약
- Apache 2.0 / Gemma 4 Terms 준수 confirmation
- Privacy: 가족 음성 데이터 로컬 only, 외부 공개 X

### 7. Future Work

- 세종 지역특화콘텐츠개발지원사업 11월 최종으로 family panel 5개 + B2G 시범
- Apple Vision Pro / Meta Quest XR 확장 (세종 제안서의 VR 모듈)
- OSMU IP (캐릭터 세종이/또미/말랑이) 까지

### 8. Conclusion

가족이 진짜 사용자이고 평가자일 때, on-device LLM 의 진짜 quality 가 드러난다.
Apache 2.0 + 무료 + 오프라인 = 다문화가정 누구나 접근 가능.

### Appendix A — Dataset details
### Appendix B — LoRA hyperparameters
### Appendix C — Family-as-Evaluator probe set + raw scores
### Appendix D — Failure case gallery (hidden mode catalog)
### Appendix E — Reproducibility (commit hash, env, seeds)

---

## Repro / artifact release

- GitHub repo (Apache 2.0): code + LoRA adapter + Family-as-Evaluator probe set + scoring rubric
- HuggingFace dataset card: trilingual_ko_ru_en_v1
- Demo video (5분, 가족 사용 + 프리미엄 모드)

---

## 일정 (5/6 → 5/17 arxiv)

| 일자 | paper 작업 |
|---|---|
| 5/6 | outline 확정 ✅ (이 문서), 초기 결과 figure 1 (베이스라인 결과) |
| 5/7 | Section 3 (Method) 1차 draft + dataset table |
| 5/8 | Section 4 (Family-as-Evaluator) protocol 확정, 와이프와 30개 probe 평가 1차 |
| 5/9 | Section 5 실험 (LoRA-v1 학습 후) — table 1, 2 |
| 5/10 | Bridge pivot ablation 실행 + table 작성 |
| 5/11 | Section 1, 2, 6, 7 draft |
| 5/12 | 모든 figure 마감 (system arch / data flow / metric vs human ablation / failure case gallery) |
| 5/13 | Full paper assembly + bibliography |
| 5/14 | 자체 readthrough + 와이프 검수 (RU 부분) |
| 5/15 | External review (Codex CLI 또는 Claude로 paper-reviewer agent) |
| 5/16 | 최종 수정 + arxiv preprint 준비 |
| 5/17 | **arXiv 제출** + 해커톤 비디오 컷 마감 |
| 5/18 | **해커톤 제출** (논문 link 포함) |

---

## 기여자 (arXiv v1)

- **Byoungsang Lee** (SKKU AdvMat + MoonTechnology) — first author, system/model/paper
- **Yunchul Kim** (SKKU AdvMat)
- **Youmin Shim** (SKKU AdvMat)
- **Chaewon Kwak** (SKKU AdvMat)
- **Prof. Jung Heon Lee** (SKKU AdvMat + SKKU MetaBioHealth) — corresponding author, supervision

## 향후 저자 추가 가능 (arXiv v2/v3)
- 와이프 (RU L1 evaluator + RU 검수) — N=20 가족 평가 협력 시 contributor 추가
- 세종 다문화가족지원센터 협력자
- MoonTechnology / SKKU 추가 엔지니어 (LoRA-v3 + Android prod 작업 시)

→ arXiv 는 v1→v2 사이 저자 추가 명시적 허용. 저널 투고 시 cover letter 에 author change 사유 기재.
