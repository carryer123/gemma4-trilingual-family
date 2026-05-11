# iOS handoff (Mac + Xcode + iPhone 15 Pro)

목표: Android와 동일한 .task 파일을 iPhone 15 Pro 위에서도 그대로 돌리는 SwiftUI 앱.

## 1. Xcode 신규 프로젝트 만들기 (한 번만)

1. Xcode → File → New → Project → **iOS / App**
2. Product Name: `TrilingualFamily`
3. Interface: **SwiftUI**, Language: **Swift**, Storage: **None**
4. Bundle Identifier: `com.moontech.trilingual` (Android와 동일)
5. Save 위치: `~/work/TrilingualFamilyIOS/` 권장
6. Minimum Deployment: **iOS 16.0**

## 2. 우리 Swift 파일 drag-in

Finder에서 다음 디렉토리 통째로 Xcode 프로젝트 navigator에 드래그 (Copy items if needed ✅, target = TrilingualFamily):

```
prototype/ios/TrilingualFamily/
    TrilingualFamilyApp.swift   ← 기본 생성된 동명 파일을 이걸로 대체
    ContentView.swift           ← 기본 생성된 동명 파일을 이걸로 대체
    Llm/
        LlmBackend.swift
        MediaPipeBackend.swift
        PromptBuilder.swift
        TrilingualCard.swift
    Resources/
        Info.plist              ← Xcode가 만든 Info.plist에 키만 병합 (camera/mic/speech)
```

## 3. MediaPipe Genai 의존성 추가 (CocoaPods)

```bash
cd ~/work/TrilingualFamilyIOS
gem install cocoapods           # 처음 한 번
cp /path/to/prototype/ios/Podfile .   # 또는 직접 작성
pod install
open TrilingualFamily.xcworkspace     # ⚠️ .xcodeproj 아닌 .xcworkspace 열기
```

또는 SPM이 편하면: Xcode → File → Add Package Dependencies →
`https://github.com/google-ai-edge/mediapipe-ios-genai` (만약 SPM 미러가 있다면).
공식 권장은 CocoaPods.

## 4. 모델 파일 추가

HPC에서 변환된 `.task` 파일을 노트북으로 가져오기:

```bash
mkdir -p ~/work/TrilingualFamilyIOS/Models
rsync -avhP hpc198a01@neuron.ksc.re.kr:/scratch/hpc198a01/젬마4해커톤/prototype/android/app/src/main/assets/gemma-4-E2B-it-merged.task ~/work/TrilingualFamilyIOS/Models/
```

Xcode에서:
- 파일 navigator에 `Models/gemma-4-E2B-it-merged.task` 드래그
- ✅ Copy items if needed
- ✅ Add to target: TrilingualFamily
- File Inspector → **"Don't compress"** 확인 (큰 파일 압축하면 mmap 안 됨)

## 5. Build Settings 한 번만 손보기

- **Signing & Capabilities** → Team: 본인 Apple ID
- **iPhone Distribution**은 굳이 안 해도 됨 — 본인 Apple ID로 sideload 가능
- **Build Settings** → "Other Linker Flags" → `-ObjC` 추가 (MediaPipe iOS 권장)
- **General** → "Frameworks, Libraries, and Embedded Content" → MediaPipeTasksGenAI/C가 Embed & Sign 되어 있는지 확인

## 6. iPhone 15 Pro 직접 빌드

1. iPhone USB 연결, iPhone 화면에서 "신뢰" 누르기
2. Xcode 상단 디바이스 선택기 → 본인 iPhone 15 Pro
3. ▶ Run
4. 첫 실행: 8GB RAM 중 ~2GB 모델 + ~1GB Swift 런타임 → 다른 앱 다 죽이고 켜는 게 안전
5. "model: ready" 뜰 때까지 5-15초 (첫 mmap)
6. "object name" → "apple" → generate card → 트리플 카드 떠야 함

## 7. 막히는 신호

| 증상 | 원인 후보 |
|---|---|
| `pod install`에서 MediaPipeTasksGenAI 못 찾음 | `pod repo update` 후 재시도 |
| 빌드 시 "module 'MediaPipeTasksGenAI' not found" | `.xcworkspace` 대신 `.xcodeproj` 열었음 |
| 앱 켜자마자 crash, console에 "killed" | RAM 부족. Background apps 정리 후 재시도 |
| 모델 로드 실패: "task not bundled" | Xcode에서 .task가 target membership에 안 들어감. File Inspector 확인 |
| 응답이 깨진 한글/키릴 | 모델 .task가 Android 것과 동일한 빌드인지 확인 (sha256 비교) |

## 8. 영상 촬영 동선 (D-3, 5/15)

| Shot | 폰 |
|---|---|
| 5, 9, 10 | 갤럭시 (Android) |
| 7, 8 (FR/KO/EN cameo) | 갤럭시 또는 iPhone (둘 다 OK) |
| **6, 11** | **iPhone 15 Pro** (다국적 가정 = 두 OS) |
| 18 closing | 두 폰 동시 노출 |

영상 narrate에 한 줄 추가 가치:
> "Same offline model, both ecosystems — because real multilingual families don't all use the same phone."
