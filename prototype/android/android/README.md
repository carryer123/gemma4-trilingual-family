# Android prototype — Gemma 4 E2B 폰 단독 코어

## 골격 (Kotlin + Jetpack Compose + MediaPipe LLM Inference)

### Dependencies (build.gradle.kts module)

```kotlin
dependencies {
    // Gemma 4 on-device via MediaPipe LLM Inference API
    implementation("com.google.mediapipe:tasks-genai:0.10.24")
    // CameraX for object recognition
    implementation("androidx.camera:camera-core:1.4.0")
    implementation("androidx.camera:camera-camera2:1.4.0")
    implementation("androidx.camera:camera-lifecycle:1.4.0")
    implementation("androidx.camera:camera-view:1.4.0")
    // ML Kit for image labeling fallback
    implementation("com.google.mlkit:image-labeling:17.0.9")
    // Jetpack Compose
    implementation("androidx.compose.material3:material3:1.3.1")
    // Audio recording
    implementation("androidx.media3:media3-common:1.5.0")
    // OS TTS (Android built-in)
    // android.speech.tts.TextToSpeech — no extra dep
}
```

### Permissions (AndroidManifest.xml)

```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.INTERNET" /> <!-- premium mode -->
<uses-feature android:name="android.hardware.camera" android:required="true" />
```

### Model deployment

```kotlin
// app/src/main/assets/gemma-4-e2b-it-int4.task   (~3GB after quantization)
// Or download on first launch:
// https://www.kaggle.com/models/google/gemma-4 (Mobile / MediaPipe variant)

val options = LlmInference.LlmInferenceOptions.builder()
    .setModelPath("/data/local/tmp/llm/gemma-4-e2b-it.task")
    .setMaxTopK(64)
    .setMaxTokens(2048)
    .setNumResponses(1)
    .build()

val llmInference = LlmInference.createFromOptions(context, options)
```

### Screen flow

```
LaunchScreen
  → Family setup (langs in household, child age band, parent KO level)
LearningScreen
  ├─ Camera toggle [object → trilingual card]
  ├─ Voice toggle  [audio → multilingual response]
  ├─ Text mode (parent learning)
  ├─ Age band selector (0-2 / 2-4 / 4-6 / 6-8)
  └─ Bridge language selector (RU or EN)
```

### Inference call (sketch)

```kotlin
fun translateAndCard(objectName: String, ageBand: String, bridge: String): TrilingualCard {
    val systemPrompt = """
        You are the trilingual (KO/RU/EN) family tutor.
        Mother bridge language: $bridge. Child age: $ageBand.
        Output a JSON learning card for the object. JSON only.
    """.trimIndent()
    val userPrompt = "Object: $objectName"
    val response = llmInference.generateResponse("$systemPrompt\n\n$userPrompt")
    return parseTrilingualCard(response)  // Json schema validation
}
```

### OS TTS playback (3 langs)

```kotlin
val tts = TextToSpeech(context) { status -> ... }
fun speak(text: String, lang: String) {
    val locale = when (lang) {
        "ko" -> Locale.KOREAN
        "ru" -> Locale("ru", "RU")
        "en" -> Locale.US
        else -> Locale.US
    }
    tts.language = locale
    tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "card-${System.currentTimeMillis()}")
}
```

### LoRA hotswap (advanced)

MediaPipe Genai supports loading our LoRA adapters at runtime if exported as
.bin (use `convert_lora_to_mediapipe.py` from MediaPipe Genai conversion tools).

```kotlin
val loraOptions = LoraOptions.builder()
    .setLoraPath("/data/local/tmp/llm/lora_v1.bin")
    .build()
val sessionOptions = LlmInferenceSession.LlmInferenceSessionOptions.builder()
    .setLoraOptions(loraOptions)
    .build()
val session = LlmInferenceSession.createFromOptions(llmInference, sessionOptions)
```

## TODO

- [ ] Android Studio 프로젝트 골격 생성 (Empty Compose Activity)
- [ ] 카메라 캡처 + ML Kit 라벨러 → object name 추출 흐름
- [ ] LlmInference 통합 + JSON 카드 파싱
- [ ] TTS 3언어 큐
- [ ] 음성 입력 (AudioRecord → Gemma 4 audio modality 또는 onboard ASR)
- [ ] LoRA 어댑터 로드
- [ ] 어린이 콘텐츠 가드레일

## 빌드 노트

- minSdk 31 (Android 12 — MediaPipe Genai 권장)
- targetSdk 35
- 권장 단말: Snapdragon 8 Gen 3+ / Tensor G3+ / iPhone 15+ (NPU 가속)
- 모델 task 파일은 첫 실행 시 다운로드 또는 `adb push` 로 사전 배포
