# Gemma Family — State-Gated Trilingual Family Tutor

End-to-end pipeline for the **Gemma 4 Good Hackathon (Kaggle 2026)**: a multilingual family tutor built on Gemma 4 E2B that runs **fully on-device on an iPad** and is gated at every generation against the same deployment audit suite we published at **EMNLP 2026** (Lee et al., *"From False-Green Detection to Gate-Aware Repair: State-Gated Data Curricula for Multilingual LoRA Adapters"*).

The repository ships **two layers** of one project:

| Layer | Where | Purpose |
|---|---|---|
| **Training** — bridge-pivot data, distillation, LoRA fine-tuning, FaE protocol | `prototype/`, `tools/fae_protocol/` | Produce the `policy+family` LoRA adapter used in the app |
| **Deployment** — iPad SwiftUI app, runtime G1–G4 gates, audit capsule | `app/` | Run the adapter on-device, verify every output, export per-generation audit log |

Both layers are language-agnostic: data and code are parameterised over a `(L1, L2, bridge)` tuple, and the runtime gates only depend on the family's configured languages. Our reference deployment uses **KO/RU/EN** (Aria, age 2) and **KO/FR/EN** (Maxim, age 4) under One-Parent-One-Language protocols.

## Why this exists

Our household speaks three scripts every day — Korean (한국 아빠 ↔ child), Russian (mom + visiting grandmother + aunt + cousin ↔ child), English (between parents). A friend's household raises a four-year-old in Korean, French, and English under the same OPOL pattern. Cloud tutors either route languages incorrectly, send the child's voice off-device, or collapse to a single language when more than one family member is in the room.

We replace the cloud tutor with a 3.2 GB Gemma 4 LoRA adapter that runs on the iPad, plus a four-gate runtime audit lifted directly from the paper. Every generation is checked against the same gate suite the paper uses for deployment promotion. Nothing leaves the device.

---

## A · Training layer (`prototype/`, `tools/`)

* **Bridge-pivot data augmentation** (Tatoeba L1-EN + L2-EN → L1 + L2 + EN trilingual triples via English pivot, with optional length-similarity filtering).
* **Synthetic learning-artifact distillation** — trilingual object cards, family-scenario dialogs, function-call labels, and explicit cross-script transliteration pairs, generated via Gemma 4 E4B/26B served by parallel Ollama instances.
* **LoRA fine-tuning runner** (Unsloth + TRL) with smoke, full, and ablation scripts: 4-arm bridge-pivot ablation (`L_direct`, `L_pivot_only`, `L_pivot_filtered`, `L_multilingual`) and 5-arm policy-frequency sweep (`L_policy_{0,1,3,5,10}%`).
* **Family-as-Evaluator (FaE) protocol** — reusable v1 specification, 30-probe stratified set, 8-class failure-mode taxonomy, 3-tier statistical claim framework, YAML pre-registration template. Released CC-BY 4.0 in [`tools/fae_protocol/`](tools/fae_protocol/).
* **Auto-judge** + **multi-variant comparator** for objective metrics (empty-response rate, JSON-schema parse rate, cross-script transliteration accuracy).

### Reproducing the policy+family adapter

```bash
bash setup_env.sh && bash install_packages.sh

python prototype/data/01_download_tatoeba.py
python prototype/data/02_build_trilingual_triples.py
python prototype/data/02b_build_multilingual_triples.py
python prototype/data/03_synth_object_cards.py
python prototype/data/05_synth_family_scenarios.py
python prototype/data/06_synth_function_calls.py
python prototype/data/07_synth_transliteration.py

TARGET=object   PARALLEL=8 python prototype/data/04_run_synth_via_ollama.py
TARGET=scenario PARALLEL=8 python prototype/data/04_run_synth_via_ollama.py

python prototype/data/10_merge_train_jsonl.py

CUDA_VISIBLE_DEVICES=0 python prototype/train/lora_v2_full.py
CUDA_VISIBLE_DEVICES=0 python prototype/eval/eval_all_variants.py
python prototype/eval/analyze_all_variants.py

# 9-arm ablation
python prototype/data/11_build_ablation_sets.py
bash scripts/run_ablation_queue.sh
```

### Adding a new language triple

The pipeline is parameterised over `(L1, L2, bridge)`. To add EN + ES (no bridge) or DE + TR + EN:

1. Add the `(language_a, language_b)` pair to `PAIRS` in `prototype/data/01_download_tatoeba.py`.
2. Add the new triple's bridge-pivot spec to `prototype/data/02b_build_multilingual_triples.py`.
3. (Optional) Localise the FaE probe set — translate the *input texts* of the 30 probes in `tools/fae_protocol/probes_v1.jsonl`. Suffix the probe ids with `-{lang_triple}` to keep the reuse rule satisfied.

---

## B · Deployment layer (`app/`)

The app ships as a six-tab consumer family app branded **Trio**:

| Tab | What it does |
|---|---|
| **Today**     | Pick a moment (story / word card / song / say-it / family note / culture) and Gemma 4 writes it in all active languages. Each language card has an inline ▶︎ TTS button. |
| **Library**   | Every generated card is auto-saved; replay TTS, swipe to delete. Persisted via `LibraryStore`. |
| **Phrasebook**| 21 daily-routine phrases (morning / meal / bath / play / bedtime / praise / apology / greeting) preloaded in KO/EN/RU/FR with TTS — no model needed. |
| **Words**     | Single words from every generation auto-ingest into a per-language Word Wall, filterable. |
| **Camera**    | Photo → Apple `VNClassifyImageRequest` labels → tap any label → Gemma writes a 3-language word + one kid-friendly sentence + TTS. |
| **Family**    | UI language picker (KO/EN/RU/FR), Visitor mode (grandmother / aunt / dad-only / mom-only), per-family-language activation toggles, per-language voice picker (Premium / Enhanced / Compact), kids, model, history. |

| Component | File |
|---|---|
| iPad SwiftUI app (six tabs)          | `app/UI/ContentView.swift` |
| Engine wrapper                       | `app/llama.cpp.swift/LibLlama.swift` |
| Gemma 4 chat-template wrap           | `GemmaChat.wrap(_:)` in `ContentView.swift` |
| G1–G4 evaluator                      | `StateGates` enum in `ContentView.swift` |
| Soft block / partial-JSON parsers    | `parseLanguageBlocks`, `softParseCard` in `ContentView.swift` |
| Audit log + JSON export              | `AuditLogStore` in `ContentView.swift` |
| Persistent stores                    | `LibraryStore`, `WordStore` in `ContentView.swift` |
| Phrasebook curation                  | `Phrasebook` in `ContentView.swift` |
| Per-language TTS w/ voice picker     | `FamilyTTS`, `VoicePickerRow`, `bestVoice` in `ContentView.swift` |
| Vision label → trilingual translate  | `CameraLabeler` in `ContentView.swift` |
| UI localization (KO/EN/RU/FR)        | `Localization`, `LocKey` in `ContentView.swift` |

### Runtime gates

Each generation is parsed and scored against four gates and tagged Green/Amber/Red:

| Gate | Check | Implementation |
|---|---|---|
| G1 structure | Family-card JSON keys present | `JSONDecoder<FamilyCard>` |
| G1 age       | Sentence length budget by `AgePolicy.forAge(_:)` | `wordCount` + regex |
| G2 script    | Per-language script ratio ≥ 85 %, foreign ≤ 10 % | Unicode block buckets |
| G3 schema    | One JSON object, required keys, correct types | `JSONSerialization` |
| G4 routing   | No exclusively-inactive-language scripts > 5 % | active-set diff |

The on-screen dashboard renders all five scores plus a band capsule on every answer; rationale strings are surfaced inline. The full event stream is captured in `AuditLogStore` and exported as `audit_capsule.json` for parent review.

### Model

`gemma4_e2b_policy.Q4_K_M.gguf` (3.2 GB, Q4_K_M, **Seed 10 policy+family repair**, EMNLP §4L main-boost). Held-out: common loss **0.6673 ± 0.0001**, G3 schema **100 %**, G4 routing **100 %**, app-constrained band **GREEN**. No-policy ablation: loss 0.804, G3 0 %, G4 0 % — used in the app as a toggleable "negative control" to demonstrate that the gates are doing real work.

GGUF is not bundled. On launch the app scans the app-container `Documents/` and auto-loads any `.gguf`. The reproduction recipe in `scripts/` uses `xcrun devicectl device copy to` to push the model into the iPad container.

### Build

```bash
# 1. iOS llama.xcframework (~10 min, Xcode 16.5+).
cd vendor/llama.cpp && ./build-xcframework.sh

# 2. Open the SwiftUI sample and sign with a personal team.
open examples/llama.swiftui/llama.swiftui.xcodeproj
# Xcode → Signing & Capabilities → Team → your Apple ID

# 3. Connect an iPad in Developer Mode, then build and install on device.
xcodebuild -project examples/llama.swiftui/llama.swiftui.xcodeproj \
           -scheme llama.swiftui -configuration Debug \
           -destination 'platform=iOS,id=<UDID>' \
           -allowProvisioningUpdates build

# 4. Push the model into the app's Documents directory.
xcrun devicectl device copy to \
  --device <UDID> \
  --domain-type appDataContainer \
  --domain-identifier com.moontech.gemmafamily \
  --source path/to/gemma4_e2b_policy.Q4_K_M.gguf \
  --destination Documents/gemma4_e2b_policy.Q4_K_M.gguf
```

### Generation format

The original strict-JSON schema (`{"title":..., "body":{lang:str}}`) was dropped — it cost too many tokens on iPad, truncated mid-body, and made the family see raw `"title": "..."` text on failure. The current prompt asks Gemma 4 for **plain `=== <language> ===` blocks**, parsed by `parseLanguageBlocks`. If the model emits partial JSON (legacy / no-policy adapter), `softParseCard` extracts per-language body from the partial text, including unterminated trailing strings. The user never sees raw JSON.

### Multimodal status

- **Speech in** (parent): handled by the **iOS keyboard's built-in dictation key** — tap the prompt field, press 🎙 on the system keyboard, dictate in any installed locale. We dropped the custom `SFSpeechRecognizer` + `AVAudioEngine` pipeline because remote-debugged audio-session configs kept cycling through OSStatus -50 / kAFAssistantErrorDomain 216 / "No speech detected" depending on the device's exact config; the keyboard mic is what every consumer iPad app uses and bypasses the audio session entirely.
- **Speech out**: `AVSpeechSynthesizer` with quality-ranked voice selection (Siri-class → Premium → Enhanced → Compact). The Family tab exposes a per-language voice picker so the parent can lock in (for example) Kate Enhanced for English even when the request locale is `en-US`. Siri voices themselves require Apple's `com.apple.developer.speech.synthesis` entitlement (paid Developer Program); Personal Team sign-ins fall back to Premium, which uses the same neural engine.
- **Camera + vision**: shipped. `VNClassifyImageRequest` produces English labels; tapping a label sends just that single word to Gemma with a block-tag prompt, which writes the matching word + a sub-12-word kid-friendly sentence in each active language. Each output has its own ▶︎ TTS. Gemma 4's `mmproj` vision adapter is not in this build — the photo never leaves Vision/Gemma, both on-device.

---

## Family-as-Evaluator (FaE) protocol

`tools/fae_protocol/` is a stand-alone CC-BY 4.0 release of the FaE protocol — a 30-probe stratified evaluation set, an 8-class failure-mode taxonomy, three statistical claim tiers (existence / predictability / prevalence), a YAML pre-registration template, and a CSV scoring schema. Independent of the dataset and the model: any practitioner deploying an LLM into a multilingual, multi-script, or atypical-literacy population can adopt it. See [`tools/fae_protocol/SPEC.md`](tools/fae_protocol/SPEC.md).

---

## License

| Artifact | License |
|---|---|
| App and pipeline code | Apache 2.0 ([LICENSE](LICENSE)) |
| Trained LoRA adapter weights | Apache 2.0 (released separately on Hugging Face) |
| Multilingual datasets | CC-BY 4.0 (inherits from Tatoeba) |
| FaE protocol specification, probe set, taxonomy | CC-BY 4.0 |
| Engine | MIT (see `vendor/llama.cpp/LICENSE`) |
| Gemma 4 model weights | Google's Gemma Terms of Use |

## Citation

```bibtex
@inproceedings{lee2026stategated,
  title  = {State-Gated Promotion: Auditable Repair of Multilingual
            LoRA Adapters via Frozen Deployment Gates},
  author = {Lee, Byoungsang and Kim, Yunchul and Shim, Youmin and Kwak, Chaewon and Lee, Jung Heon},
  booktitle = {Proceedings of EMNLP},
  year   = {2026},
  note   = {under review}
}
```

---

## Paper PDF (current draft)

| File | Size | Description |
|---|---|---|
| [`paper/state_gated_lora_main.pdf`](paper/state_gated_lora_main.pdf) | 189 KB | Main paper (9 pages incl. references) |
| [`paper/state_gated_lora_supplement.pdf`](paper/state_gated_lora_supplement.pdf) | 110 KB | Supplementary material (3 pages) |

**Abstract (EMNLP 2026 submission):**

> A LoRA adapter can win on validation loss yet emit unparseable JSON, drift into the wrong script, or answer in a language the session never activated — breaking the deployed interface even though scalar metrics look fine. We introduce *state-gated promotion*: a small set of automatic gates that name the deployment states an interface must preserve, freeze them before model selection, and turn each gate failure into targeted repair data. On a four-language KO/RU/FR/EN deployment with Gemma 4 E2B, a gate-aware repair curriculum lifts JSON-schema pass rate from **0% to 95.8%** and session-language routing from **0% to 91.7%** against a no-policy ablation matched on base, hyper-parameters, audit, and translation corpus but not on data volume, with no held-out loss penalty. The same stock failure replicates on four other instruction-tuned bases (Gemma 4 E4B, Qwen 2.5 3B, Llama 3.2 3B, Phi-3.5 mini), and the repair recipe recovers schema compliance to ≥91.7% on every base we repaired — evidence that the failure is a property of the deployment interface, not of any one base model.

**Headline numbers:**

| Metric | No-policy ablation | Policy+family repair |
|---|---:|---:|
| Held-out loss (mean) | 0.804 | 0.667 |
| G2 script-state (%) | 92.5 | 91.7 |
| **G3 JSON schema (%)** | **0.0** | **95.8** |
| **G4 session routing (%)** | **0.0** | **91.7** |
| Cross-base G3 (Qwen / Llama / Phi) | 0 / 0 / 0 | 91.7 / 100 / 100 |

The contribution is the **loop itself** — frozen gates that simultaneously diagnose failure, define repair data, and re-evaluate the result — plus cross-base evidence that the failure pattern is a property of the deployment interface, not of any one base model.

**Why no arXiv ID yet:** arXiv cs.CL requires endorsement from an existing cs.* contributor and the lead author's home department (Materials Science) doesn't have one in-house. Endorsement is being requested in parallel; this README will be updated with the arXiv ID and Hugging Face Papers link as soon as the upload is approved. The paper is otherwise complete and is being submitted to EMNLP 2026 (deadline 2026-05-25).
