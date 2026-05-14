# 오늘 밤 사용자 TODO (D-9, 5/9) — Android + iOS 양 플랫폼

## 1. HPC에서 기동 (모델 변환은 시간 오래 걸리니 먼저)

생산되는 단일 산출물: `gemma-4-E2B-it-merged.task` (Android + iOS 동일 파일).

```bash
cd /PATH/REDACTED

# (a) 참고 .litertlm 다운로드 — 백그라운드, ~10GB (sanity 비교용)
nohup bash scripts/download_base_model.sh \
    > /PATH/REDACTED +%Y%m%d_%H%M).log 2>&1 &

# (b) 변환 의존성 설치 (HPC venv)
source ../../venv/bin/activate
pip install -U ai-edge-torch ai-edge-litert ai-edge-quantizer 'mediapipe>=0.10.27' peft

# (c) merge + export 시작 — 4-8h, GPU 1개
nohup python3 scripts/merge_lora_and_export.py \
    > /PATH/REDACTED +%Y%m%d_%H%M).log 2>&1 &

# 진행 확인
tail -f /PATH/REDACTED
```

자고 일어나면 끝나있는 정도가 목표. 실패하면 MODEL_SETUP.md의 fallback 표.

## 2. 로컬 노트북에서

### (a) Android Studio 설치 (없으면)
- https://developer.android.com/studio (LTS 채널)
- JDK 17은 Android Studio 자체 번들 사용 OK
- SDK Platform 35, Build-Tools 35.0.0 설치
- 실단기 USB 디버깅 활성화

### (b) 프로젝트 가져오기
```bash
# 노트북 작업 위치에서
mkdir -p ~/work && cd ~/work
rsync -avhP --info=progress2 --partial --append-verify \
    --exclude='app/src/main/assets/*.litertlm' \
    REDACTED@neuron.ksc.re.kr:/PATH/REDACTED \
    ./TrilingualFamily/

# (모델 .litertlm은 무거우니 별도로 변환 끝나고 나서 받기)
```

### (c) Android Studio에서
1. `File → Open` → `~/work/TrilingualFamily`
2. Gradle sync 실행 (처음엔 deps 받느라 5-10분)
3. 빨간 줄이 뜨면 알려주기 — `:app` 모듈 deps 충돌 가능성
4. 모델 .litertlm 도착 전엔 "model load error" 뜨는 게 정상. UI는 떠야 함.

### (d) sync 통과하면 빈 emulator로 한 번 빌드
- Run → 'app' → Pixel 7+ AVD (API 35)
- "Trilingual Family" 화면이 뜨고 model status가 'error: ...' 정도면 골격 OK

## 3. Mac에서 (iOS 형제 프로젝트)
자세한 단계는 `prototype/ios/HANDOFF_IOS.md`. 요약:

```bash
# Mac에서
cd ~/work
rsync -avhP REDACTED@neuron.ksc.re.kr:/PATH/REDACTED ./TrilingualFamilyIOS/

# Xcode → File → New → iOS App → name "TrilingualFamily", SwiftUI, iOS 16+
# 그 다음 우리 Swift 파일들을 navigator에 drag-in
# Podfile 복사 → pod install → .xcworkspace 열기
```

## 4. 내일 (D-8)
- 변환된 `.task`를 두 곳에 배치:
  - Android: `app/src/main/assets/gemma-4-E2B-it-merged.task`
  - iOS: `~/work/TrilingualFamilyIOS/Models/` 후 Xcode drag-in
- 갤럭시 + iPhone 15 Pro 둘 다에서 첫 카드 생성 시도 (sha256 같은 모델인지 확인)
- TaskList #4 (CameraX/AVFoundation), #5 (TTS/Speech) 시작

## 막히면 알려야 할 신호
- 변환 로그에 `ai_edge_torch.generative.utilities.converter` import 실패 → API 위치 변경 가능성
- 변환 로그에 `mediapipe.tasks.python.genai.bundler` import 실패 → mediapipe 버전 < 0.10.27, `pip install -U mediapipe` 다시
- 변환 산출물이 5GB 넘게 나옴 → int4 quantization 안 먹음
- Gradle sync에서 `tasks-genai:0.10.27` 못 찾음 → google() repo 위치 확인
- iOS `pod install`에서 `MediaPipeTasksGenAI` not found → `pod repo update` 후 재시도
