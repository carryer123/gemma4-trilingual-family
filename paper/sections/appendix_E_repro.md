# Appendix E: Reproducibility

## E.1 Hardware and environment

* **Cluster node**: 4× NVIDIA A100-SXM4-80GB (single host, all GPUs visible)
* **Storage**: Lustre `/scratch/hpc198a01/`, 937 TB free at start of run
* **OS**: Linux 5.14.0-427.13.1.el9_4.x86_64 (RHEL 9.4 derivative)
* **Python**: 3.10.14 (`/scratch/hpc198a01/py310env/`, then `젬마4해커톤/venv/`)
* **CUDA Toolkit**: 12.8 (driver-side); cuda-bindings 12.9.4
* **PyTorch**: 2.10.0+cu128
* **transformers**: 5.8.0
* **trl**: 1.3.0
* **peft**: 0.12+
* **datasets**: 4.5.0 (with the Unsloth check patched, see Appendix B.7)
* **bitsandbytes**: 0.44+
* **accelerate**: 1.12.0
* **Unsloth**: 2026.5.2
* **Ollama**: 0.23.1 (4 instances, ports 11434–11437, one per GPU,
  `OLLAMA_NUM_PARALLEL=2`)
* **vLLM**: 0.19.1 (installed but not used in v1/v2)
* **hf_transfer**: enabled (`HF_HUB_ENABLE_HF_TRANSFER=1`)

## E.2 Model digests (Ollama)

```
gemma4:e2b   sha256 7fbdbf8f5e45...   7.2 GB
gemma4:e4b   sha256 c6eb396dbd59...   9.6 GB
gemma4:26b   sha256 5571076f3d70...  17 GB
```

For Unsloth-served E2B (HF mirror):

```
unsloth/gemma-4-E2B-it (last_modified 2026-05-05 13:48:03 UTC)
local: models/unsloth-gemma-4-E2B-it/
sizes: 9.6 GB total; model.safetensors ≈ 9.5 GB
```

## E.3 Random seeds and determinism

| Component | Seed |
|---|---|
| Tatoeba shuffle (merge stage) | 20260506 |
| LoRA-v1 SFTConfig | 20260506 |
| LoRA-v1 PEFT random_state | 20260506 |
| LoRA-v2 SFTConfig | 20260507 |
| LoRA-v2 PEFT random_state | 20260507 |
| Family-as-Evaluator probe order | sorted by `id` (deterministic) |

We do not promise bit-for-bit determinism due to (a) bf16 nondeterminism
on A100 tensor cores and (b) Ollama's distillation temperature 0.6
sampling. Loss curves and final adapters are reproducible to within
typical bf16 noise; objective metrics in §5.2 are reproducible.

## E.4 Cost ledger

Total wall-clock from the moment we entered `젬마4해커톤/`:

| Stage | Time | Resource |
|---|---|---|
| venv + package install | ~12 min | CPU + network |
| Tatoeba download + extraction | ~6 min | network |
| Ollama install + model pulls | ~15 min | network |
| Distillation: object cards × 1,294 | ~25 min | 4× A100 |
| Distillation: family scenarios × 1,006 | ~30 min | 4× A100 |
| LoRA-v1 training | 2 h 0 m | 1× A100 |
| LoRA-v1 vs stock auto-judge | ~6 min (load × 2 + 60 generations) | 1× A100 |
| LoRA-v2 training | (in progress, ETA 2 h) | 1× A100 |
| Paper authoring (this document) | concurrent with above | CPU only |

## E.5 Repository layout

```
/scratch/hpc198a01/젬마4해커톤/
├── README.md
├── CREDENTIALS_NEEDED.md
├── setup_env.sh
├── install_packages.sh
├── docs/
│   ├── 아키텍처_결정_20260506.md
│   ├── 파인튜닝_플랜_20260506.md
│   └── (more)
├── research/
│   ├── 대회규정_요약_20260506.md
│   ├── 대회규정_상세_20260506.md
│   ├── Gemma4_스펙_요약_20260506.md
│   ├── MTP_드래프터_요약_20260506.md
│   └── 다국어_데이터셋_큐레이션_20260506.md
├── prototype/
│   ├── data/        (01–10_*.py)
│   ├── train/       (lora_smoke_test.py, lora_v1_full.py, lora_v2_full.py)
│   ├── eval/        (baseline_via_ollama.py, lora_v1_vs_stock.py, auto_judge.py)
│   ├── android/     (skeleton README + planned Kotlin module)
│   └── server/      (moon1_wire.py)
├── paper/
│   ├── PAPER_OUTLINE.md
│   ├── sections/    (01–08 + appendix_A/B/D/E)
│   └── data_release/
│       └── family_as_evaluator_probes_v1.jsonl   (30 probes)
├── lora_out/lora_v1/adapter/     (the released LoRA-v1 adapter, 259 MB)
├── lora_out/lora_v2/             (in progress)
├── models/
│   └── unsloth-gemma-4-E2B-it/   (9.6 GB)
├── ollama_models/                (33 GB across e2b/e4b/26b)
└── logs/                         (all training and distillation logs)
```

## E.6 The hackathon submission

The Kaggle Gemma 4 Good Hackathon submission (deadline 2026-05-18 UTC)
will include:

* **Public code repo**: GitHub `gemma4-trilingual-family` (Apache 2.0)
* **Public LoRA adapter**: HuggingFace `<author>/gemma-4-E2B-trilingual-family-lora`
* **Public dataset card**: HuggingFace `<author>/trilingual-ko-ru-en-family-v2`
* **Demo video**: 5 minutes, mirroring the demo path documented in §3.1
* **Technical write-up**: this paper as the technical-track entry
* **Cover image**: brand assets in `assets/`

## E.7 Things future-us should not forget

* Gemma 4 license requires attribution and a link to the Gemma 4 model
  card. Our Apache 2.0 release inherits the Apache 2.0 of Gemma 4.
* Tatoeba CC-BY requires attribution. Each downloaded sentence is
  CC-BY-2.0 [tatoeba-license].
* The MTP drafter and SoulX-FlashHead components have their own
  licenses; the moon1 deployment is not part of the Apache 2.0 release.
* The 21-month-old participant's voice data does not appear in any
  released artifact; only second-hand parental observations of
  attention/laughter/repetition are reported.
* If we move the N=20 multicultural family panel forward (Section 7), an IRB or
  equivalent local-ethics review is required; we will not retroactively
  release the v1 single-family data as if it were panel data.
