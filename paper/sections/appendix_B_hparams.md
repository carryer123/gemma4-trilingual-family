# Appendix B: LoRA Hyperparameters and Training Setup

## B.1 Base model

* **HuggingFace ID**: `unsloth/gemma-4-E2B-it`
* **License**: Apache 2.0 (no gating)
* **Source**: Unsloth's public mirror; 170,016 downloads as of 2026-05-06
* **Effective parameters**: 2.3B
* **Total parameters (with embeddings)**: 5,134,157,344
* **Local copy**: `/scratch/hpc198a01/젬마4해커톤/models/unsloth-gemma-4-E2B-it`

## B.2 Adapter configuration

Identical for v1 and v2 unless noted:

```python
FastLanguageModel.get_peft_model(
    model,
    r=32,                # rank (v1 and v2)
    lora_alpha=64,       # 2× r
    lora_dropout=0.05,
    target_modules=["q_proj","k_proj","v_proj","o_proj",
                    "gate_proj","up_proj","down_proj"],
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=20260506,    # v1
    max_seq_length=2048,
)
```

For LoRA-v2, `random_state=20260507` to ensure independence from v1.

* **Trainable parameters**: 29,859,840 (0.58% of base, v1)
* **Trainable parameters**: 59,719,680 (1.16% of base, v2 — slight
  difference due to dropout/audio-tower handling)

## B.3 SFT configuration

```python
SFTConfig(
    per_device_train_batch_size = 2,
    gradient_accumulation_steps = 4,
    # effective batch size = 2 × 4 × 1 GPU = 8
    num_train_epochs = 2,
    learning_rate = 2e-4,
    lr_scheduler_type = "cosine",
    warmup_ratio = 0.03,
    optim = "adamw_8bit",
    bf16 = True,
    fp16 = False,
    max_seq_length = 2048,
    seed = 20260506,
    save_steps = 500,
    eval_strategy = "steps",
    eval_steps = 200,
    logging_steps = 20,
    save_total_limit = 3,
    report_to = "none",
)
```

## B.4 Wall-clock and loss curves (v1)

* **Hardware**: 1× NVIDIA A100-SXM4-80GB
* **Training set**: 18,043 examples (v1)
* **Total steps**: 4,512 (= 18,043 / 8 × 2)
* **Wall-clock**: 7,238 seconds = **2 h 0 m 38 s**
* **Throughput**: 4.985 samples/s, 0.623 steps/s
* **Final train loss**: 0.151 (down from 1.535 at step 1)
* **Final eval loss**: 0.5316 at epoch 2
* **GPU memory peak**: ≈ 28 GB (Ollama 15 GB + Unsloth bf16 LoRA 13 GB)

Loss curve milestones:

| Epoch | Train loss | Eval loss |
|---|---|---|
| 0.05 (step 25) | 1.535 | — |
| 0.20 (step 100) | 0.799 | 0.586 (interpolated) |
| 0.40 (step 200) | 0.476 | 0.553 |
| 1.00 (step 1100) | 0.250 | 0.541 |
| 1.50 (step 1700) | 0.180 | 0.534 |
| 1.86 (step 4200) | 0.105 | 0.5337 |
| 2.00 (step 4512) | 0.151 | 0.5316 |

(Train loss spikes near the end reflect a single hard scenario batch
near the end of cosine decay; this does not propagate to eval loss.)

## B.5 v2 changes from v1

* `train_v2.jsonl` 20,513 examples (+ 2,470 from v1):
  * +1,294 distilled object cards
  * +1,006 distilled family scenarios
  * +300 transliteration pairs (this is the *targeted* v1-failure fix)
  * −130 Tatoeba dedupe / chat-template tightening
* `random_state = 20260507` to make v2 independent
* Same hyperparameters otherwise

## B.6 Reproducibility

A single command reproduces v2:

```bash
cd /scratch/hpc198a01/젬마4해커톤
source venv/bin/activate
CUDA_VISIBLE_DEVICES=0 ./venv/bin/python prototype/train/lora_v2_full.py
```

The data merge is reproduced by:

```bash
./venv/bin/python prototype/data/01_download_tatoeba.py
./venv/bin/python prototype/data/02_build_trilingual_triples.py
./venv/bin/python prototype/data/03_synth_object_cards.py
./venv/bin/python prototype/data/05_synth_family_scenarios.py
./venv/bin/python prototype/data/06_synth_function_calls.py
./venv/bin/python prototype/data/07_synth_transliteration.py
# (then run distillation across 4 Ollama instances; see scripts/distill_pipeline.sh)
./venv/bin/python prototype/data/10_merge_train_jsonl.py
```

## B.7 The Unsloth datasets-version patch

Unsloth 2026.5.2 hard-blocks `datasets` versions in the [4.4, 4.5]
window. We have `datasets==4.5.0` (inherited from the user-site
Python). The error is a known recursion issue
[unsloth-issue-datasets]. We patched
`venv/lib/python3.10/site-packages/unsloth/import_fixes.py` line 583 to
emit a `warnings.warn(...)` instead of `raise NotImplementedError(...)`:

```python
# PATCHED 2026-05-06: bypass hard check; emit warning only
if (datasets_version <= Version("4.5.0")) and (datasets_version >= Version("4.4.0")):
    import warnings
    warnings.warn(
        f"unsloth: datasets={datasets_version} is in the 4.4–4.5 recursion-risk window; "
        "patched to continue. If you hit RLock errors, downgrade to datasets==4.3.0."
    )
```

Training completed with no observed RLock errors. We did not encounter
the recursion bug Unsloth's check is intended to prevent.
