# Trilingual KO + RU + EN Family Co-Learning on Gemma 4 E2B

A trilingual on-device language-tutoring system built around Gemma 4 E2B
([Apache 2.0](https://huggingface.co/google/gemma-4)) for multicultural
households where two parents have different first languages and a
pre-literate child grows up trilingual.

## What this is

* A **mobile-first co-learning app** that supports two adult learners and a
  pre-literate child in one session, in the same physical room, on a single
  device, fully offline.
* A **bridge-pivot data augmentation pipeline** that turns 247 directly-
  aligned KO-RU sentence pairs into 12,408 trilingual KO + RU + EN triples
  via English-pivot alignment.
* A **Family-as-Evaluator (FaE) protocol specification** for
  niche-population LLM evaluation, with a 30-probe v1 set, a failure-mode
  taxonomy, and a pre-registration template (`tools/fae_protocol/`).
* An **empirical study of policy-frequency regression** in LoRA fine-tuning:
  a target task with very small training share is silently regressed by the
  fine-tune even when overall loss looks healthy.

## Repository layout

```
paper/                  # Markdown sources of the companion paper
  main.md               # Master assembly with abstract + section index
  sections/             # 8 main sections + appendices A/B/D/E/F
  references.bib
  data_release/         # Family-as-Evaluator probe set v1 (30 probes)

prototype/
  data/                 # Tatoeba pulls, pivot triples, distill prompts, ablation builder
  train/                # Smoke + full LoRA + ablation runner
  eval/                 # Auto-judge, baseline, side-by-side, multi-variant analyzer
  demo/                 # Gradio app (HuggingFace Space-ready)
  android/              # Skeleton README for on-device deployment
  server/               # FastAPI premium-tier wire to a SoulX-FlashHead avatar

tools/fae_protocol/     # Standalone protocol release (CC-BY 4.0)
  SPEC.md
  probes_v1.jsonl + sha256
  preregistration_template.yaml
  scoring_template.csv
  taxonomy_v1.txt
  examples/run_lee2026.yaml

scripts/                # Setup, build, automation
```

## Quick start

```bash
# 1. Set up isolated venv (everything stays under this directory)
bash setup_env.sh
bash install_packages.sh

# 2. Build the trilingual dataset (Tatoeba + English-pivot triples)
python prototype/data/01_download_tatoeba.py
python prototype/data/02_build_trilingual_triples.py

# 3. Generate prompt scaffolds and run distillation against a local Ollama
python prototype/data/03_synth_object_cards.py
python prototype/data/05_synth_family_scenarios.py
python prototype/data/06_synth_function_calls.py
python prototype/data/07_synth_transliteration.py

# 4. Merge into a single train/eval JSONL
python prototype/data/10_merge_train_jsonl.py

# 5. Train the LoRA adapter
CUDA_VISIBLE_DEVICES=0 python prototype/train/lora_v2_full.py

# 6. Evaluate against the 30-probe Family-as-Evaluator set
CUDA_VISIBLE_DEVICES=0 python prototype/eval/eval_all_variants.py
python prototype/eval/analyze_all_variants.py
```

## Run the demo locally

```bash
bash scripts/launch_demo_local.sh
# then open http://localhost:7860
```

The demo is a five-tab Gradio app: translation, trilingual object card,
family scenario, L1-aware grammar, and cross-script transliteration. Each
tab corresponds to one category of the Family-as-Evaluator probe set.

## Family-as-Evaluator protocol

The FaE protocol is released as a standalone artifact under CC-BY 4.0 in
[`tools/fae_protocol/`](tools/fae_protocol/). It defines a 30-probe
stratified set, a 5-point Likert + free-text scoring scheme, an 8-class
failure-mode taxonomy, and three claim tiers (existence / predictability /
prevalence) so adopters can publish honest single-N case studies and a
clear path to N-scaled validation.

Adopters are encouraged to fork, localize the probes for their own
language triple, pre-register, and contribute new failure-mode tags. See
[`tools/fae_protocol/SPEC.md`](tools/fae_protocol/SPEC.md).

## Authors

| Author | Affiliation | Contribution |
|---|---|---|
| **Byoungsang Lee** | School of Advanced Materials Science and Engineering, Sungkyunkwan University · MoonTechnology | first author — system, model, paper |
| **Prof. Jung Heon Lee** | School of Advanced Materials Science and Engineering, Sungkyunkwan University · Department of MetaBioHealth, Sungkyunkwan University | corresponding author — supervision |

ORCID: Byoungsang Lee 0000-0001-6874-0935 · Jung Heon Lee 0000-0003-4790-3525
Correspondence: Prof. Jung Heon Lee — `jhlee7@skku.edu`

## License

* Code: **Apache 2.0** ([LICENSE](LICENSE))
* Trained LoRA adapter weights: Apache 2.0 (released separately on Hugging Face)
* Trilingual KO + RU + EN dataset: CC-BY 4.0 (inherits from Tatoeba)
* Family-as-Evaluator protocol specification, probe set, taxonomy: CC-BY 4.0
* This README and the paper text: CC-BY 4.0

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
