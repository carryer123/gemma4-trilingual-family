# 3. Method

## 3.1 System architecture

The system has two tiers, deployed under a single mobile UI (Figure 1):

**Tier 1 (Phone-only, primary).** Gemma 4 E2B running on the device under
the Apache 2.0 license. The phone exposes:

* **Camera path**: image → object recognition (ML Kit fallback) → prompt
  the LLM with the recognized object → strict-JSON trilingual *learning
  card* (KO + RU + EN word, four-direction phonetic, parent-tier and
  child-tier learning text, L1 contrast notes, and recommended next
  words). The card is rendered as visual cards, played as audio in all
  three languages via the Android TTS engine, and never leaves the device.
* **Voice path**: 16-kHz audio capture → Gemma 4's native audio input
  encoder → speaker-language detection → trilingual response card. The
  audio path explicitly avoids running an external ASR model: native
  audio-in is one of the four reasons we chose Gemma 4 (Section 2.1).
* **Function-calling**: native Gemma 4 JSON tool-calling for
  `score_pronunciation`, `recommend_next_word`, `explain_in_l1`,
  `switch_age_mode`, `daily_mission`, and `flag_unsafe_input` (the
  full schema is in Appendix A).

The phone tier is *single-failure-tolerant*: with no network, no cloud
access, and no logged-in account, every learning interaction listed above
still works.

**Tier 2 (Premium sidecar, opt-in).** A moon1 server with one RTX 3090
running Gemma 4 26B + the 76M MTP drafter [mtp-blog]. When the user toggles
*Premium*, the phone forwards the user message to the moon1 endpoint via
a Cloudflared HTTPS tunnel; moon1 responds with text, then renders the
text through SoulX-FlashHead Lite [soulx-fh] using a per-persona LoRA
(e.g., "Russian-L1-aware Korean teacher with a deliberate Russian accent")
and an ElevenLabs- or Cartesia-cloned voice; the resulting MP4 chunks
stream back to the phone over the same tunnel. We measure the moon1
end-to-end latency budget against the SoulX render rate to keep the
talking-head experience felt as a real-time conversation (Section 5).

## 3.2 Dataset construction

The dataset has three layers.

### 3.2.1 Translation pairs (Tatoeba)

Tatoeba [tatoeba] is the only fully open, CC-BY licensed sentence-pair
corpus that covers all three languages we need. For each language pair
we select all linked sentences in both directions and deduplicate at the
sentence-id level. Statistics:

| Pair | Pairs |
|---|---|
| KO ↔ RU (direct) | 247 |
| KO ↔ EN (direct) | 11,385 |
| RU ↔ EN (direct) | 810,219 |

The KO-RU direct count is too low to support trilingual fine-tuning.

### 3.2.2 English-pivot trilingual triples

We construct a KO + RU + EN trilingual triple by matching, for each
shared English sentence, all KO translations and all RU translations.
After deduplication and a 3-to-3 cap per English sentence, this yields
**12,408 triples** — a 50× expansion over the direct KO-RU count. Each
triple is then expanded into six directional pairs (KO→RU, RU→KO, KO→EN,
EN→KO, RU→EN, EN→RU) at training time, so the LoRA sees roughly 75K
translation steps from the pivot layer alone.

We acknowledge two known risks of pivot construction:

1. **Pivot drift**: a triple's KO and RU sentences may not be true
   paraphrases — they share an English midpoint that admits multiple
   meanings. We do not filter for round-trip semantic similarity in v1
   (a v2 plan in Section 7).
2. **Register asymmetry**: KO formal speech often pivots through
   register-neutral English to RU informal, and vice versa, producing
   stylistically inconsistent triples. We address this only via the
   synthetic-data layer (3.2.3).

Both risks contribute to *pivot hallucination* (Section 4), which is one
of the failure modes that Family-as-Evaluator surfaces.

### 3.2.3 Synthetic learning artifacts (Gemma 4 distillation)

We distill the larger Gemma 4 variants (E4B and 26B) into the JSON-
schema-constrained learning artifacts that the app's UI consumes:

* **Object cards**: 1,500 prompts, one per (object, age band, bridge
  language) tuple drawn from a 144-object household-vocabulary list spanning
  9 categories (house, food, animals, body, nature, transport, school,
  emotions, actions). Each card is a single JSON document with the schema
  in Appendix A, including 4-direction phonetics (KO→Cyrillic, RU→Hangul,
  KO→Latin, RU→Latin), age-banded child cards, parent learning cards
  with bridge-language explanations, and an L1-contrast field.
* **Family scenarios**: 1,500 multi-turn dialog scripts spanning 50 daily
  situations × 4 age bands × 3 maternal-Korean levels × 2 bridge-language
  options. Each script encodes simultaneous learning targets for father
  (RU), mother (KO), and child (any), grounded in a realistic situational
  setup (breakfast, park, doctor, bedtime, etc.).
* **Function-call seeds**: 500 hand-curated → template-expanded prompts
  pinning the model to emit valid tool-call JSON with the precise argument
  schemas used by the app.

Distillation runs on a 4× A100 80GB cluster with four parallel Ollama
servers (one per GPU) hosting Gemma 4 E4B in GGUF format. We initially
observed 0.04 cards/s; switching off Gemma 4's *thinking* trace (`think:
False` in the Ollama API) and round-robin-ing parallel requests across
the four servers raised throughput to **0.87 cards/s** — a 22× speedup
without changing the model. We discuss the systems implications in
Section 5 and Appendix E.

### 3.2.4 Schema-constrained validation

Every distilled artifact is validated against its JSON schema before being
admitted to the training set. Failed parses are routed to a
*\*\_failed.jsonl* file for either retry under a larger model or, if
deemed structurally non-recoverable, manual inspection. The early
distillation phase produced a 1.0% structural failure rate at E4B with
`format=json` enabled.

## 3.3 LoRA fine-tuning

We fine-tune Gemma 4 E2B with LoRA, not full-parameter, for three reasons:
the on-device deployment target (an additive adapter ≪ 500 MB is what
ships to the phone), the tight 12-day window (a single A100 LoRA run is
~2 hours), and the explicit Unsloth $10K special prize tied to LoRA-style
fine-tunes [unsloth-prize]. We use Unsloth 2026.5.2 [unsloth] with the
public, non-gated `unsloth/gemma-4-E2B-it` mirror as the base:

* **Adapter**: r = 32, α = 64, dropout = 0.05; targets q/k/v/o + gate/up/down
* **Data path**: chat template applied via `apply_chat_template` with
  `add_generation_prompt=False` so the assistant turn is in-context for
  loss
* **Optimizer**: 8-bit AdamW, lr 2e-4, cosine schedule, 3% warmup
* **Batch**: device 2 × accumulation 4 = 8, sequence length 2048, bf16
* **Schedule**: 2 epochs over 18,043 examples ≈ 4,510 steps;
  ~2 hours wall-clock on one A100 80GB

We export both the PEFT adapter (for HF/Unsloth inference) and a Q4_K_M
GGUF (for Ollama / llama.cpp / on-device deployment). A smoke run with
200 examples and 50 steps confirmed end-to-end correctness with loss
descending 1.535 → 0.247 in ~3 minutes.

## 3.4 MTP drafter integration

For the moon1 premium tier we follow Google's Multi-Token Prediction
recipe [mtp-blog]: the 76M parameter `gemma-4-26b-it-mtp-drafter` shares
the target model's KV cache and activation pipeline. In llama.cpp the
invocation is

    llama-cli -m gemma-4-26b-it.gguf \
        --draft-model gemma-4-26b-it-mtp-drafter.gguf \
        --draft-max 8 --draft-min 1 --draft-min-p 0.5

with the speculative-decoding KPI being end-to-end token throughput vs.
the same prompt without `--draft-model`, reported in Section 5.4.

## 3.5 On-device deployment path

The phone-side runtime is MediaPipe LLM Inference [mediapipe-llm], which
accepts the `.task` artifact form of Gemma 4 E2B. We use the conversion
tools in MediaPipe GenAI [mediapipe-genai-conv] to quantize the
LoRA-adapted model to int4 weights and to bundle the LoRA adapter as a
runtime hot-swap (`LlmInferenceSession.LlmInferenceSessionOptions.set
LoraOptions(...)`). The Android prototype skeleton, dependencies, and
permission manifest are listed in Appendix B.
