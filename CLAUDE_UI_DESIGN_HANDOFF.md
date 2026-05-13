# Claude UI Design Handoff

## 목적

현재 앱은 Gemma GGUF를 iPad에서 로컬로 실행하는 `llama.cpp` SwiftUI 예제 기반이다.  
엔진과 모델 로딩은 이미 동작하므로, Claude는 **디자인/UX만 개선**하면 된다.

## 반드시 유지할 것

- `LlamaState.complete(text:)` 호출 구조
- `LoadCustomButton(llamaState:)` 로컬 GGUF 파일 로딩
- `DrawerView`의 모델 로딩 기능
- `gemma4_e2b_policy.Q4_K_M.gguf`를 앱 번들에 넣지 않고 Files 앱에서 불러오는 방식
- iPad 오프라인 실행 메시지

## 현재 문제

- 원래는 `llama.cpp` 기본 채팅 예제라 해커톤 앱처럼 보이지 않았다.
- 지금 `ContentView.swift`는 최소한 “다문화 생활 안전 도우미” 컨셉을 보여주도록 바꿨지만, 디자인 품질은 Claude가 새로 잡는 것이 낫다.
- 앱 컨셉이 심사자에게 첫 화면에서 보여야 한다.

## 앱 컨셉

앱 이름 후보:

- Gemma Care
- LocalBridge
- Momi
- 다온 AI

핵심 문장:

> 네트워크 없이 iPad 안에서 동작하는 다문화 생활 안전·행정 보조 AI

대상 사용자:

- 한국어가 익숙하지 않은 이주민
- 다문화 가정 학부모
- 주민센터/학교/병원/노동상담 현장 담당자
- 개인정보를 서버로 보내기 어려운 상담 상황

## 주요 사용 시나리오

1. 어려운 한국어 안내문을 쉬운 말로 바꿔줌
2. 병원 방문 전 증상 설명 문장을 만들어줌
3. 비자/체류 관련 준비 서류를 정리함
4. 임금 체불/근로계약 문제에서 확인할 항목을 정리함
5. 학교 가정통신문을 보호자가 이해하기 쉽게 요약함
6. 긴급 상황에서 지금 할 일을 우선순위로 정리함

## 추천 화면 구조

### 1. 홈

- 큰 제목: "어려운 한국어를 쉬운 도움으로"
- 서브카피: "비자, 병원, 학교, 노동 문제를 iPad 안에서 안전하게 정리합니다."
- 상태 배지: "Offline on-device"
- 모델 로딩 상태: "Gemma model loaded / not loaded"

### 2. 언어 선택

지원 언어 버튼:

- 한국어
- English
- 中文
- Tiếng Việt
- ภาษาไทย
- Монгол
- Русский
- O'zbek

### 3. 도움 카드

카드는 2열 또는 iPad 가로 기준 3열.

- 쉬운 한국어
- 병원 안내
- 비자·체류
- 노동 상담
- 학교 안내문
- 긴급 상황

각 카드에는 짧은 설명과 아이콘 필요.

### 4. 입력

- 큰 텍스트 박스
- "예시 넣기" 버튼
- "쉬운 답변 만들기" CTA

### 5. 답변

출력 형식이 잘 보이도록 카드화:

- 한 줄 요약
- 지금 할 일
- 준비할 것
- 주의할 점
- 문의할 기관

현재 모델 출력은 plain text라, 우선 `messageLog`를 그대로 보여줘도 된다.
나중에 JSON 출력으로 바꾸면 카드별 파싱 가능.

## 디자인 톤

피해야 할 것:

- 개발자 콘솔 같은 화면
- 기본 SwiftUI 회색 리스트 느낌
- 너무 많은 텍스트
- 의료/법률 앱처럼 과하게 딱딱한 분위기

권장:

- 밝고 신뢰감 있는 공공서비스 톤
- 큰 버튼
- 큰 글씨
- 고대비
- iPad 가로 화면 최적화
- 상담 키오스크처럼 한눈에 이해되는 구조

색상 후보:

- 배경: 따뜻한 아이보리 또는 아주 연한 블루
- 메인: 딥 블루 / 코발트
- 보조: 민트 / 그린
- 위험 안내: 오렌지 / 레드 소량

## 기술 주의

- SwiftUI만 수정
- `LlamaState.swift`는 가능하면 건드리지 말 것
- 모델 로딩/추론 로직은 건드리지 말 것
- 앱이 무거워지지 않게 이미지/애니메이션 최소화
- iOS 16.0 호환 유지

## 현재 검증 상태

아래 명령으로 빌드 성공 확인됨.

```bash
cd "/Users/lee/Library/CloudStorage/Dropbox/Scapple/2026_연구노트/해커톤/Gemma4Good_iPad/vendor/llama.cpp"
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcodebuild \
  -project examples/llama.swiftui/llama.swiftui.xcodeproj \
  -scheme llama.swiftui \
  -configuration Debug \
  -destination 'generic/platform=iOS Simulator' \
  build
```

결과:

```text
** BUILD SUCCEEDED **
```

## Claude에게 줄 한 줄 지시

`ContentView.swift`만 중심으로, Gemma 로컬 모델 로딩과 LlamaState 호출은 유지하면서 iPad용 다문화 생활 안전 도우미 앱처럼 보이도록 SwiftUI 디자인을 개선해줘. 모델 엔진, GGUF 로딩, LlamaState.swift는 건드리지 말고 빌드 성공까지 확인해줘.
