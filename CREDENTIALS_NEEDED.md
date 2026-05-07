# 🔑 사용자가 한 번 해주면 모든 게 풀리는 한 가지

Gemma 4 모델은 HuggingFace 게이트(라이센스 수락 + 토큰)가 걸려 있어요.
다음 **두 단계** 만 해주시면 베이스라인 → LoRA → 데모까지 자동 진행됩니다.

## 단계 1 — Gemma 4 라이센스 수락 (브라우저 1분)

본인 HuggingFace 계정으로 아래 페이지 접속해서 "Acknowledge license" 클릭:

- https://huggingface.co/google/gemma-4-E2B-it
- https://huggingface.co/google/gemma-4-E4B-it
- https://huggingface.co/google/gemma-4-26b-it
- https://huggingface.co/google/gemma-4-26b-it-mtp-drafter
- https://huggingface.co/google/gemma-4-E2B-it-mtp-drafter

(기존에 Gemma 3 라이센스 수락한 적 있으면 자동 승인되는 경우 많음)

## 단계 2 — HF 토큰 환경변수 설정

토큰 생성: https://huggingface.co/settings/tokens → "Create new token" → **Read 권한** 만 → 복사.

이 채팅창에 토큰 붙여넣기 OR 직접 export:

```bash
echo 'export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxx' >> /scratch/hpc198a01/젬마4해커톤/.envrc
```

토큰 알려주시면 제가 `.envrc` 에 저장하고 모든 다운로드 자동 재시작합니다.

---

## 우회 경로 (토큰 없어도 진행 중)

**Ollama 경로** (라이센스 게이트 없음, 백그라운드 다운로드 중):
- `gemma4:e2b` / `gemma4:e4b` / `gemma4:26b` 다 ungated
- 다만 GGUF 양자화 버전이라 LoRA 직접 학습은 어려움 (추론 베이스라인은 OK)

**Kaggle 직접 다운로드** (대회 페이지에서 모델 제공):
- https://www.kaggle.com/models/google/gemma-4
- 본인 Kaggle 계정으로 약관 수락 → kaggle CLI 로 다운로드
- `pip install kaggle` + `~/.kaggle/kaggle.json` 배치

**둘 중 어느 경로든 한 번만 풀어주시면** LoRA 학습부터 데모까지 자동 진행.

---

## 진행 중인 것 (토큰 없이 가능)

- ✅ venv 셋업 + 패키지 설치 (거의 완료)
- ✅ Function calling 학습 데이터 498건 생성
- ✅ Object cards 프롬프트 1296건
- ✅ Family scenarios 프롬프트 1176건
- 🔄 Tatoeba KO/RU/EN 페어 다운로드 (~1GB, 진행 중)
- 🔄 Ollama 1.2GB 바이너리 다운로드 (백그라운드)

## 막혀 있는 것 (토큰 필요)

- ⛔ Gemma 4 E2B / 26B 가중치 다운로드
- ⛔ MTP 드래프터 다운로드
- ⛔ LoRA 학습 (모델 없으면 시작 불가)
- ⛔ baseline trilingual 평가
- ⛔ 합성 데이터 26B distill

토큰만 풀리면 위 5개 모두 자동.
