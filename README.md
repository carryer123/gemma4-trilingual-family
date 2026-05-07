# Multilingual Family Co-Learning on Gemma 4 — Algorithms and Reproducible Pipeline

A general-purpose, on-device multilingual family-tutoring pipeline built
around Gemma 4 E2B ([Apache 2.0](https://huggingface.co/google/gemma-4)).

The pipeline is **language-agnostic**: data, training, and evaluation scripts are parameterized over a tuple `(L1, L2, bridge)`. Adding a new language triple requires editing one list of language codes — no changes to the training or evaluation logic.


## What's in this repository

* The **bridge-pivot data augmentation** pipeline (Tatoeba L1-EN +
  L2-EN → L1 + L2 + EN trilingual triples via English pivot, with
  optional length-similarity filtering).
* The **synthetic learning-artifact distillation** pipeline that
  generates trilingual object cards, family-scenario dialogs,
  function-call training labels, and explicit cross-script
  transliteration pairs via Gemma 4 E4B/26B served by parallel
  Ollama instances.
* The **LoRA fine-tuning** runner (Unsloth + TRL) with smoke, full,
  and ablation scripts. Includes a 4-arm bridge-pivot ablation
  (`L_direct`, `L_pivot_only`, `L_pivot_filtered`, `L_multilingual`)
  and a 5-arm policy-frequency sweep (`L_policy_{0,1,3,5,10}%`) for
  studying when LoRA regresses on under-represented policies.
* The **Family-as-Evaluator (FaE) protocol** — a reusable v1
  specification + 30-probe stratified set + 8-class failure-mode
  taxonomy + 3-tier statistical claim framework + YAML
  pre-registration template, released CC-BY 4.0 in
  [`tools/fae_protocol/`](tools/fae_protocol/).
* An **auto-judge** + **multi-variant comparator** for objective
  metrics (empty-response rate, JSON-schema parse rate, cross-script
  transliteration script-correctness).

## Repository layout

```
prototype/
  data/                        # data pipeline (numbered 01–11)
    01_download_tatoeba.py
    02_build_trilingual_triples.py
    02b_build_multilingual_triples.py
    03_synth_object_cards.py
    04_run_synth_via_ollama.py
    04_run_synth_with_26b.py
    05_synth_family_scenarios.py
    06_synth_function_calls.py
    07_synth_transliteration.py
    10_merge_train_jsonl.py
    11_build_ablation_sets.py

  train/
    lora_smoke_test.py         # 200-example smoke run
    lora_v1_full.py            # baseline LoRA
    lora_v2_full.py            # LoRA + transliteration policy fix
    lora_ablation_runner.py    # parameterized runner for ablation arms
    train_lora_v1.py           # standalone reference trainer

  eval/
    baseline_via_ollama.py     # stock baseline through Ollama API
    baseline_e2b_trilingual.py # stock baseline through HF Transformers
    lora_v1_vs_stock.py        # side-by-side eval
    eval_all_variants.py       # multi-variant runner
    auto_judge.py              # objective metrics on a single comparison
    analyze_all_variants.py    # roll-up + ablation table + curve PNG

tools/fae_protocol/            # CC-BY 4.0 FaE release
  SPEC.md
  probes_v1.jsonl + probes_v1.sha256
  preregistration_template.yaml
  scoring_template.csv
  taxonomy_v1.txt

scripts/
  distill_pipeline.sh          # auto-pipeline: object distill → scenario distill → merge
  run_ablation_queue.sh        # 4-arm parallel ablation + 5-arm policy sweep

setup_env.sh                   # venv layout
install_packages.sh            # pip dependencies
```

## Quick start

```bash
# 1. Isolated venv + dependencies
bash setup_env.sh
bash install_packages.sh

# 2. Multilingual dataset 
python prototype/data/01_download_tatoeba.py
python prototype/data/02_build_trilingual_triples.py
python prototype/data/02b_build_multilingual_triples.py     # example multilingual triples

# 3. Distillation prompts (no-LLM scaffolding)
python prototype/data/03_synth_object_cards.py
python prototype/data/05_synth_family_scenarios.py
python prototype/data/06_synth_function_calls.py
python prototype/data/07_synth_transliteration.py

# 4. Distill against a local Ollama (4 instances on 4 GPUs recommended)
TARGET=object  PARALLEL=8 python prototype/data/04_run_synth_via_ollama.py
TARGET=scenario PARALLEL=8 python prototype/data/04_run_synth_via_ollama.py

# 5. Merge into JSONL
python prototype/data/10_merge_train_jsonl.py

# 6. Train
CUDA_VISIBLE_DEVICES=0 python prototype/train/lora_v2_full.py

# 7. Multi-variant evaluation + analysis
CUDA_VISIBLE_DEVICES=0 python prototype/eval/eval_all_variants.py
python prototype/eval/analyze_all_variants.py

# 8. Ablation sweep (build 9 variant data sets, then queue training)
python prototype/data/11_build_ablation_sets.py
bash scripts/run_ablation_queue.sh
```

## Adding a new language triple

The pipeline is parameterized over `(L1, L2, bridge)`. To add e.g. an
EN + ES + (no bridge needed) pair, or a DE + TR + EN triple:

1. Add the `(language_a, language_b)` pair to the `PAIRS` list in
   `prototype/data/01_download_tatoeba.py` and re-run.
2. Add the new triple's bridge-pivot specification to
   `prototype/data/02b_build_multilingual_triples.py` (one entry in the
   `PAIRS` list).
3. (Optional) Localize the FaE probe set: translate the *input texts*
   of the 30 probes in `tools/fae_protocol/probes_v1.jsonl` to the new
   language triple. Keep the rubric and probe ids identical; suffix
   the probe ids with `-{lang_triple}` to keep the protocol's
   reuse-rule satisfied.

## Family-as-Evaluator (FaE) protocol

`tools/fae_protocol/` is a stand-alone CC-BY 4.0 release of the FaE
protocol — a 30-probe stratified evaluation set, an 8-class failure-
mode taxonomy, three statistical claim tiers
(existence / predictability / prevalence), a YAML pre-registration
template, and a CSV scoring schema. The protocol is independent of
the dataset and the model in this repository; any practitioner
deploying an LLM to a multilingual, multi-script, or atypical-
literacy population can adopt it.

See [`tools/fae_protocol/SPEC.md`](tools/fae_protocol/SPEC.md).

## License

| Artifact | License |
|---|---|
| Code | Apache 2.0 ([LICENSE](LICENSE)) |
| Trained LoRA adapter weights | Apache 2.0 (released separately on Hugging Face) |
| Multilingual datasets | CC-BY 4.0 (inherits from Tatoeba) |
| FaE protocol specification, probe set, taxonomy | CC-BY 4.0 |
