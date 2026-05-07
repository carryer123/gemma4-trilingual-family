# 젬마4 해커톤 — 다문화가정 부모-자녀 공동학습 앱

> **Kaggle Gemma 4 Good Hackathon · Education 트랙 · 마감 2026-05-18 (D-12)**

**팀**: 본인(KO L1) + 와이프(RU L1) + 아기(KO L1, 1세 9개월), **부부 공통어 EN** — 한 가정 안에 **KO+RU+EN 3언어 동시 사용** (국제결혼 가정 표준 패턴)
**상금**: $200,000 (General + Impact + Technical)
**평가**: Impact (가중치↑) / Technical execution / Clear use case
**제출물**: working demo + public code (Apache 2.0) + technical write-up + short video

---

## 핵심 컨셉

**"폰 하나, 가족 셋, 언어 셋, 무료, 오프라인."**
다문화가정 가족 전원이 한 화면에서 **trilingual L1-aware 공동학습**.

- 코드 스코프: **N×N 언어쌍 + 0-8세 전 연령**, 3+ 언어 동시 활성 가정 지원
- 데모: 본인 가족 (KO+RU+EN, 와이프+남편+아기 1세 9개월)
- 차별화 (Duolingo/Papago/Google 이 못하는 4가지 빈칸):
  1. **글 못 읽는 아기 + 글 읽는 부모 동시 학습**
  2. **양방향 L1-aware 페르소나** (RU 화자용 KO 선생님 등)
  3. **Trilingual** 한 세션 = 3언어 동시 (식탁 한 끼니에 KO+RU+EN 살아있음)
  4. **브릿지 언어 옵션** — 와이프가 KO 학습 시 설명을 EN 으로 받기 (남편과 평소 쓰는 언어)

---

## 아키텍처 (ADR-001 → `docs/아키텍처_결정_20260506.md`)

### 메인: 폰 단독 (Gemma 4 E2B on-device)

```
[사용자]                         [Gemma 4 E2B, 2GB RAM, Apache 2.0, 오프라인]
─────────                       ───────────────────────────────────────────
카메라 → 사물                →  image in     → KO+RU+EN 3언어 단어카드 + OS TTS
마이크 → 누가 말하든          →  audio in     → 화자 언어 자동 감지 → 가족 전원용 카드
                                              (RU+L1 음성에 맞춰 KO/EN 학습 카드 동시 생성)
부모 학습 (텍스트/음성)        →  L1 또는 EN(브릿지) 으로 설명 선택
아기 옹알이                   →  audio in     → 인식+발달 피드백+미션 (3언어)
                                Function calling → 발음점수 / 미션 / L1or브릿지 설명
```

**브릿지 언어**: 와이프(RU L1) 가 KO 배울 때, 설명을 RU 또는 EN(남편과 평소 쓰는 언어) 중 선택. 본인이 RU 배울 때도 동일.

**왜 on-device 메인?**
- 토큰비용 0 (Apache 2.0 + 로컬 추론)
- 다문화가정 누구나 무료 사용 → impact 점수 직격
- moon1/네트워크 죽어도 데모 살아있음
- E2B 가 음성 입력 + 이미지 입력 + Function calling 다 됨 (별도 Whisper 불필요)
- **MTP 드래프터 76M 짜리** 로 폰에서도 3× 가속 (라이브 음성 대화 < 200ms)

### 프리미엄 사이드카: moon1 (RTX 3090, 본인 기존 자산)

```
폰 → cloudflared tunnel → moon1
                            ├─ Gemma 4 26B (대화 품질 ↑, 256K 컨텍스트)
                            ├─ SoulX-FlashHead Lite + LoRA (선생님 페르소나)
                            ├─ ElevenLabs/Cartesia 보이스 클론 (L1 강세)
                            └─ 라이브 영상 스트림
```

**moon1 자산 (한 달 작업분)**:
- `/home/moon1/SoulX-FlashHead/gradio_app_streaming.py` (port 7864)
- 8개 LoRA ckpt (v1 베스트), 보이스 클론 3종
- cloudflared 터널 운영 중
- **한계 #4 (LLM 연결 X) 를 이번 프로젝트가 Gemma 4 26B 로 해결** ← 두 마리 토끼

---

## 폐기된 옵션

- **3D Gaussian Splatting** — 사용자 본인 GUAVA 한 달 삽질 후 "보간 어려움" 결론
- **온디바이스 디퓨전** — Gemma 4 이미지 출력 X, 학습 앱은 사전 일러스트+웹툰으로 충분
- **하이브리드 메인** — cloudflared 단일 실패 지점 + 토큰비용 + impact 약화

---

## 12일 일정 (D-12 → 0)

| 날짜 | 작업 |
|---|---|
| 5/6 (오늘) | research 정리 ✅ · **러시아어 품질 테스트** 🚨 |
| 5/7 | Android prototype: 카메라→Gemma4→TTS 흐름 |
| 5/8 | 음성 입력 + Function calling |
| 5/9 | UI: 0-2/2-4/4-6/6-8 연령 토글 + 양 언어 동시 카드 |
| 5/10 | moon1: Gemma 4 26B + SoulX 연결 |
| 5/11 | "러시아어 화자용 한국어 선생님" 페르소나 1종 |
| 5/12 | 폰 ↔ moon1 와이어 + 프리미엄 토글 UI |
| 5/13 | 안전 필터 (어린이 가드레일) + 콘텐츠 검토 |
| 5/14 | 가족 실사용 1시간 + 시나리오 리허설 |
| 5/15 | 데모 비디오 1차 컷 |
| 5/16 | Technical write-up + GitHub 공개 |
| 5/17 | 비디오 최종 + 폴리싱 |
| 5/18 | **제출** |

---

## 🚨 1번 리스크: Gemma 4 E2B 러시아어 품질

Gemma 3n 모바일 변종에서 영어→러시아어/스페인어 성능 저하 사례 보고됨. 오늘 테스트 결과에 따라:

| 결과 | 분기 |
|---|---|
| (A) OK | 그대로 진행 |
| (B) 부족 | E4B (4GB RAM) 로 올림 |
| (C) 여전히 부족 | moon1 26B 메인 + on-device fallback |
| (D) 최악 | 데모 언어쌍 변경 (한-영 / 한-베, 다문화 통계 1위 베트남) |

---

## 저자 / 소속

- **Byoungsang Lee** (이병상, carryer12345@gmail.com) — first author
  - SKKU School of Advanced Materials Science and Engineering
  - MoonTechnology
- **Prof. Jung Heon Lee** (이정헌, jhlee7@skku.edu) — corresponding author
  - SKKU School of Advanced Materials Science and Engineering
  - SKKU Department of MetaBioHealth

ORCID: Byoungsang Lee 0000-0001-6874-0935 · Jung Heon Lee 0000-0003-4790-3525

## 세종 지원사업 트랙과의 관계

- 세종 제안서 (`docs/세종_지역특화콘텐츠_제안서_2026-04-09.md`) = 같은 제품의 11월 최종 트랙 (별도 사업체 trial)
- 해커톤 제출본은 **세종 8월 중간평가 시제품의 압축 버전** 으로 활용 가능
- Apache 2.0 라이센스 → 세종 공공 사업화도 합법

---

## 폴더 구조

```
젬마4해커톤/
├── README.md                              # 이 파일
├── docs/
│   ├── 세종_지역특화콘텐츠_제안서_2026-04-09.md
│   └── 아키텍처_결정_20260506.md           # ADR-001
├── research/
│   ├── 대회규정_요약_20260506.md
│   └── Gemma4_스펙_요약_20260506.md
├── prototype/                              # Android + moon1 코드
└── assets/                                 # 데모 이미지, 페르소나
```
