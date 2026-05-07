# Trilingual KO + RU + EN Co-Learning on Gemma 4 E2B — Algorithms and Reproducible Pipeline

This repository contains the reproducible algorithmic pipeline for a
trilingual on-device language-tutoring LoRA fine-tune of Gemma 4 E2B
([Apache 2.0](https://huggingface.co/google/gemma-4)).

It includes:

* The **bridge-pivot data augmentation** pipeline (Tatoeba KO-EN +
  RU-EN → 12,408 KO + RU + EN trilingual triples via English pivot,
  starting from 247 directly-aligned KO-RU pairs).
* The **synthetic learning-artifact distillation** pipeline that
  generates trilingual object cards, family-scenario dialogs,
  function-call training labels, and explicit transliteration pairs
  via Gemma 4 E4B/26B served by 4 parallel Ollama instances.
* The **LoRA fine-tuning** runner (Unsloth + TRL) with smoke, full,
  and ablation scripts.
* The **Family-as-Evaluator (FaE) protocol** — a reusable v1
  specification + 30-probe set + failure-mode taxonomy +
  pre-registration template under CC-BY 4.0 in
  [`tools/fae_protocol/`](tools/fae_protocol/).
* An **auto-judge** + **multi-variant comparator** for objective metrics
  (empty-response rate, JSON parse rate, cross-script transliteration
  correctness).

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
    analyze_all_variants.py    # roll-up + Section 5 markdown + curve PNG

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

# 2. Trilingual dataset
python prototype/data/01_download_tatoeba.py
python prototype/data/02_build_trilingual_triples.py
python prototype/data/02b_build_multilingual_triples.py     # KO+VI+EN, KO+ZH+EN

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

## Family-as-Evaluator (FaE) protocol

`tools/fae_protocol/` is a stand-alone CC-BY 4.0 release of the FaE
protocol — a 30-probe stratified evaluation set, an 8-class
failure-mode taxonomy, three statistical claim tiers
(existence / predictability / prevalence), a YAML pre-registration
template, and a CSV scoring schema. The protocol is independent of
the trilingual app in this repository; any practitioner deploying an
LLM to a multilingual or atypical-literacy population can adopt it.

See [`tools/fae_protocol/SPEC.md`](tools/fae_protocol/SPEC.md).

## License

| Artifact | License |
|---|---|
| Code | Apache 2.0 ([LICENSE](LICENSE)) |
| Trained LoRA adapter weights | Apache 2.0 (released separately on Hugging Face) |
| Trilingual KO + RU + EN dataset | CC-BY 4.0 (inherits from Tatoeba) |
| FaE protocol specification, probe set, taxonomy | CC-BY 4.0 |

## Citation

```bibtex
@misc{lee2026trilingual,
  title  = {Beyond BLEU: Family-as-Evaluator for Trilingual L1-Aware
            On-Device Tutoring with Gemma 4},
  author = {Lee, Byoungsang and Lee, Jung Heon},
  year   = {2026},
  howpublished = {arXiv preprint},
  note   = {arXiv id pending}
}
```
