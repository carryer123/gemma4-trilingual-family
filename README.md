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

| Component | File |
|---|---|
| iPad SwiftUI app (state-gated tutor) | `app/UI/ContentView.swift` |
| Engine wrapper                       | `app/llama.cpp.swift/LibLlama.swift` |
| Apple Speech wrapper (on-device ASR) | inlined in `ContentView.swift` |
| Gemma 4 chat-template wrap           | `GemmaChat.wrap(_:)` in `ContentView.swift` |
| G1–G4 evaluator                      | `StateGates` enum in `ContentView.swift` |
| Audit log + JSON export              | `AuditLogStore` in `ContentView.swift` |
| Family setup, session router, mode grid | `ContentView.swift` |

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

### Multimodal status

- **Speech in** (parent): Apple `SFSpeechRecognizer`, on-device, locale tracks the first active family language.
- **Speech out**: deferred to system TTS in the demo flow.
- **Camera + vision**: scaffolded in the app shell; Gemma 4 multimodal vision is gated behind the `mmproj` adapter and llama.cpp's multimodal Swift surface, both of which are still moving — a hybrid path using Apple `VNRecognizeTextRequest` and `VNClassifyImageRequest` for fallback labelling is the current plan.

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
  title  = {From False-Green Detection to Gate-Aware Repair:
            State-Gated Data Curricula for Multilingual LoRA Adapters},
  author = {Lee, Byoungsang and Kim, Yunchul and Shim, Youmin and Kwak, Chaewon and Lee, Jung Heon},
  booktitle = {Proceedings of EMNLP},
  year   = {2026},
  note   = {to appear}
}
```
