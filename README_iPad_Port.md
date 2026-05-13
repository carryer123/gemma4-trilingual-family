# Gemma 4 Good iPad Port

## 결론

현재 모델은 GGUF입니다.

```text
/Users/lee/Downloads/gguf_models/gemma4_e2b_policy.Q4_K_M.gguf
size: 3.416 GB
sha256: 2ea9dffb0af54e88d15a17bec5ea0c4bcd4a37d88045a0f158771555907b3575
```

iPad 이식은 `llama.cpp`의 iOS SwiftUI 예제를 쓰는 것이 가장 빠릅니다. Core ML / MLC로 다시 변환하는 방식은 시간이 더 걸리고, 이미 받은 GGUF를 바로 쓰기 어렵습니다.

## 현재 준비된 것

```text
Gemma4Good_iPad/
├── README_iPad_Port.md
├── MODEL_MANIFEST.md
├── prompts/
│   └── system_prompt_ko.txt
├── scripts/
│   ├── prepare_ipad_model.sh
│   └── open_llama_swiftui.sh
└── vendor/
    └── llama.cpp/
        └── examples/llama.swiftui/
```

`llama.cpp` 공식 iOS 예제를 받아두었고, `Load Local GGUF From Files` 버튼이 보이도록 패치했습니다.

## 이 맥의 한계

현재 이 맥은 full Xcode가 아니라 Command Line Tools만 설치되어 있습니다.

```text
xcode-select: /Library/Developer/CommandLineTools
xcodebuild: full Xcode 필요
```

따라서 여기서 iPad 실기기 빌드까지는 못 하고, Xcode 설치된 맥에서 아래 순서로 진행해야 합니다.

## iPad 실행 순서

1. Xcode 설치

App Store 또는 Apple Developer에서 full Xcode를 설치합니다.

2. llama.cpp XCFramework 빌드

```bash
cd "/Users/lee/Library/CloudStorage/Dropbox/Scapple/2026_연구노트/해커톤/Gemma4Good_iPad/vendor/llama.cpp"
./build-xcframework.sh
```

3. Xcode 프로젝트 열기

```bash
open "/Users/lee/Library/CloudStorage/Dropbox/Scapple/2026_연구노트/해커톤/Gemma4Good_iPad/vendor/llama.cpp/examples/llama.swiftui/llama.swiftui.xcodeproj"
```

4. iPad 연결 후 Run

Xcode 상단에서 iPad 실기기를 선택하고 Run 합니다.

5. 모델을 iPad로 복사

3.4GB 모델을 앱 번들에 넣지 말고 iPad의 Files 앱으로 넣는 것이 안전합니다.

추천 경로:

```text
Files 앱 > On My iPad > llama.swiftui > gemma4_e2b_policy.Q4_K_M.gguf
```

Finder에서 iPad 파일 공유가 보이면 `llama.swiftui` 앱 Documents로 복사해도 됩니다.

6. 앱에서 모델 로드

앱 실행 후:

```text
View Models > Load Local GGUF From Files > gemma4_e2b_policy.Q4_K_M.gguf 선택
```

## 권장 iPad 조건

이 모델은 Q4_K_M 3.4GB입니다. 실제 실행에는 모델 파일보다 더 많은 메모리가 필요합니다.

권장:

```text
iPad Pro M1/M2/M4, RAM 8GB 이상
context: 2048 이하부터 시작
batch: 낮게
temperature: 0.2~0.7
```

RAM이 부족하면 앱이 바로 종료될 수 있습니다. 이 경우 Q3_K_M 또는 더 작은 quant를 다시 받아야 합니다.

## 해커톤 관점 권장 구조

데모는 “완전 오프라인 iPad 정책/안전 보조 모델”로 잡는 것이 좋습니다.

핵심 메시지:

```text
1. 네트워크 없이 iPad 로컬에서 동작
2. 개인정보/민감 질의가 서버로 나가지 않음
3. Gemma 기반 정책 판단 또는 안전 보조 추론
4. 현장/교육/상담/검수 등 저지연 모바일 사용 가능
```

앱 완성도보다 “왜 iPad 로컬이어야 하는가”를 강조해야 합니다.

