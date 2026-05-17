# Model setup — on-device Gemma 4 E2B + LoRA-v2 (merged)

## Decision (2026-05-09, revised after iOS path confirmed)

| Question | Choice | Rationale |
|---|---|---|
| Runtime (both platforms) | **MediaPipe Genai LLM Inference** — Android `com.google.mediapipe:tasks-genai:0.10.27`, iOS pods `MediaPipeTasksGenAI` + `MediaPipeTasksGenAIC` | Cross-platform parity: single .task artifact loads on both. LiteRT-LM Swift bindings still "🚀 In Dev" on the official repo, so it can't be the iOS path inside this development window. |
| Model artifact | **`gemma-4-E2B-it-merged.task`** (we produce it) | Single file, both platforms, supports `setLoraPath()` if we ever want to split LoRA out. |
| LoRA strategy | **Merge LoRA-v2 into base, re-quantize, re-bundle** | Single deploy. We retain the option to ship base + lora_v2.bin separately later. |
| Reference artifact | [`litert-community/gemma-4-E2B-it-litert-lm`](https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm) | Reference weights for sanity comparison only; we do NOT ship these — they lack LoRA-v2. |
| Deprecation note | MediaPipe Genai is marked deprecated by Google in favor of LiteRT-LM. We pin to 0.10.27 and call this out in the paper README: "Pinned to MediaPipe Genai for cross-platform parity; LiteRT-LM Swift bindings ETA after this release window." | Stable now, forward-known. |

## Pipeline

```
HF safetensors base (Gemma 4 E2B)
        +                                          (HPC, ~4-8h on a single GPU)
LoRA-v2 adapter (lora_out/lora_v2/adapter)
        │
        ▼  peft.merge_and_unload()
Merged HF safetensors
        │
        ▼  ai-edge-torch convert + dynamic_int4_block32 PTQ
gemma4_e2b_int4.tflite
        │
        ▼  mediapipe.tasks.python.genai bundler  (+ tokenizer + chat template tokens)
gemma-4-E2B-it-merged.task   (~1.5–2.0 GB target, SAME file for Android + iOS)
        │
        ├──▶ Android: prototype/android/app/src/main/assets/
        │       APK ships it; MediaPipeBackend.initialize() copies asset → filesDir
        └──▶ iOS:     prototype/ios/Models/  (drag into Xcode, target membership = TrilingualFamily)
                IPA ships it; MediaPipeBackend (Swift) copies bundle → Application Support
```

## Run order (HPC)

```bash
cd /PATH/REDACTED

# 1. Pull reference artifacts from HF (small, runs in background)
bash scripts/download_base_model.sh

# 2. Install converter deps in the project venv
source ../../venv/bin/activate
pip install -U ai-edge-torch ai-edge-litert ai-edge-quantizer 'mediapipe>=0.10.27' peft
# (ai-edge-litert-lm is optional; only needed for the .litertlm side bundle)

# 3. Merge + export. Wall time 4-8h on a GPU. Run with nohup; output is large.
nohup python3 scripts/merge_lora_and_export.py \
    > /PATH/REDACTED +%Y%m%d_%H%M).log 2>&1 &

# 4. Verify size and integrity
ls -lh app/src/main/assets/gemma-4-E2B-it-merged.task
sha256sum app/src/main/assets/gemma-4-E2B-it-merged.task
```

## Sanity check (before APK build)

The merged .litertlm should respond to a probe prompt like:
- "Output JSON: object 'apple' in KO+RU+EN with l1_note in EN"

Pre-flight on HPC by loading the merged HF safetensors with transformers and running PromptBuilder.objectCard("apple", "0-2", "EN") — same prompt the app will send.

## Fallback plan if export fails

| Failure | Fallback |
|---|---|
| `ai_edge_torch.generative` API moved | Pin to 2026-05 release; fall back to manual `ai_edge_torch.convert` with custom KV cache wrapper. |
| Quantization OOM | Try `dynamic_int8` instead of `int4_block32`; ship 2-3GB model. |
| Bundler missing | Manually concatenate per LiteRT-LM bundle spec; or fall back to MediaPipe `.task` path with `setLoraPath()`. |
| Whole pipeline blocked | Ship reference `gemma-4-E2B-it.litertlm` (no LoRA-v2). LoRA-v2 results stay in paper, demo says "base + system prompt." |

## What is NOT in this pipeline

- Audio modality of Gemma 4 E2B — we use Android `SpeechRecognizer` for input, OS TTS for output. The Gemma 4 audio path is a follow-up.
