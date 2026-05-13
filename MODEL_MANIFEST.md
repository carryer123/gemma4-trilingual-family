# Model Manifest

## Local Model

```text
name: gemma4_e2b_policy.Q4_K_M.gguf
path: /Users/lee/Downloads/gguf_models/gemma4_e2b_policy.Q4_K_M.gguf
format: GGUF
quantization: Q4_K_M
size_bytes: 3416118112
size_gb: 3.416
sha256: 2ea9dffb0af54e88d15a17bec5ea0c4bcd4a37d88045a0f158771555907b3575
```

## Runtime Target

```text
runtime: llama.cpp
platform: iOS / iPadOS
project: vendor/llama.cpp/examples/llama.swiftui/llama.swiftui.xcodeproj
load method: Files app / security-scoped GGUF picker
bundle model: no
```

## Memory Notes

Q4_K_M 3.4GB 모델은 iPad에서 로드 시 추가 KV cache와 runtime memory를 씁니다.

초기 테스트 설정:

```text
context length: 1024 or 2048
prompt length: short
generation length: 256 tokens
```

문제가 생기면:

```text
1. context를 1024로 낮춤
2. 더 작은 quant 모델 사용
3. iPad Pro 8GB 이상에서 테스트
```
