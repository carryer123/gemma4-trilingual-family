#!/usr/bin/env python3
"""LoRA fine-tune Gemma 4 E2B for trilingual family co-learning.

Run:
  cd /scratch/hpc198a01/젬마4해커톤
  source venv/bin/activate
  source setup_env.sh
  python prototype/train/train_lora_v1.py

Hardware: 1× A100 80GB sufficient (E2B QLoRA r=32 ~ 12GB).

Default behavior: tries Unsloth first (2× faster, 50-80% memory), falls back to
plain HF + PEFT if Unsloth import fails.
"""
from __future__ import annotations
import os, sys, json, pathlib, time

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
os.environ.setdefault("HF_HOME", str(PROJ / "hf_cache"))
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
os.environ.setdefault("WANDB_DISABLED", "true")  # opt-in only

MODEL_ID = os.environ.get("MODEL_ID", "google/gemma-4-E2B-it")
TRAIN_FILE = pathlib.Path(os.environ.get("TRAIN_FILE", str(PROJ / "prototype/data/train_v1.jsonl")))
EVAL_FILE = pathlib.Path(os.environ.get("EVAL_FILE", str(PROJ / "prototype/data/eval_v1.jsonl")))
OUT_DIR = pathlib.Path(os.environ.get("OUT_DIR", str(PROJ / "lora_out/lora_v1")))
OUT_DIR.mkdir(parents=True, exist_ok=True)

MAX_SEQ = int(os.environ.get("MAX_SEQ", "4096"))
BATCH = int(os.environ.get("BATCH", "8"))
GRAD_ACCUM = int(os.environ.get("GRAD_ACCUM", "4"))
LR = float(os.environ.get("LR", "2e-4"))
EPOCHS = int(os.environ.get("EPOCHS", "2"))
LORA_R = int(os.environ.get("LORA_R", "32"))
LORA_ALPHA = int(os.environ.get("LORA_ALPHA", "64"))


def load_dataset_for_chat(tokenizer, path):
    """Load JSONL with messages and apply chat template."""
    from datasets import load_dataset
    ds = load_dataset("json", data_files=str(path), split="train")
    def fmt(ex):
        text = tokenizer.apply_chat_template(ex["messages"], tokenize=False, add_generation_prompt=False)
        return {"text": text}
    return ds.map(fmt, remove_columns=ds.column_names)


def train_unsloth():
    from unsloth import FastLanguageModel
    from transformers import TrainingArguments
    from trl import SFTTrainer, SFTConfig

    print(f"[unsloth] loading {MODEL_ID}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_ID,
        max_seq_length=MAX_SEQ,
        load_in_4bit=True,
        dtype=None,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_R, lora_alpha=LORA_ALPHA, lora_dropout=0.05,
        target_modules=["q_proj","k_proj","v_proj","o_proj",
                        "gate_proj","up_proj","down_proj"],
        bias="none", use_gradient_checkpointing="unsloth",
        random_state=20260506,
    )

    train_ds = load_dataset_for_chat(tokenizer, TRAIN_FILE)
    eval_ds = load_dataset_for_chat(tokenizer, EVAL_FILE)

    cfg = SFTConfig(
        output_dir=str(OUT_DIR),
        per_device_train_batch_size=BATCH,
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=LR,
        num_train_epochs=EPOCHS,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        logging_steps=20,
        save_steps=200,
        eval_strategy="steps",
        eval_steps=100,
        bf16=True,
        max_seq_length=MAX_SEQ,
        packing=True,
        packing_strategy="bfd",
        report_to="none",
        save_total_limit=3,
        dataset_text_field="text",
        seed=20260506,
    )
    trainer = SFTTrainer(
        model=model, tokenizer=tokenizer,
        train_dataset=train_ds, eval_dataset=eval_ds,
        args=cfg,
    )
    trainer.train()
    trainer.save_model(str(OUT_DIR / "final"))
    tokenizer.save_pretrained(str(OUT_DIR / "final"))
    print(f"[done] saved to {OUT_DIR / 'final'}")


def train_hf_peft():
    """Fallback path if Unsloth unavailable."""
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import SFTTrainer, SFTConfig
    import torch

    print(f"[hf] loading {MODEL_ID}")
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_quant_type="nf4")
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, quantization_config=bnb, device_map="auto")
    model = prepare_model_for_kbit_training(model)
    lc = LoraConfig(r=LORA_R, lora_alpha=LORA_ALPHA, lora_dropout=0.05,
                    target_modules=["q_proj","k_proj","v_proj","o_proj",
                                    "gate_proj","up_proj","down_proj"],
                    bias="none", task_type="CAUSAL_LM")
    model = get_peft_model(model, lc)
    model.print_trainable_parameters()

    train_ds = load_dataset_for_chat(tok, TRAIN_FILE)
    eval_ds = load_dataset_for_chat(tok, EVAL_FILE)

    cfg = SFTConfig(
        output_dir=str(OUT_DIR),
        per_device_train_batch_size=BATCH,
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=LR,
        num_train_epochs=EPOCHS,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        logging_steps=20,
        save_steps=200,
        eval_strategy="steps",
        eval_steps=100,
        bf16=True,
        max_seq_length=MAX_SEQ,
        packing=True,
        packing_strategy="bfd",
        report_to="none",
        save_total_limit=3,
        dataset_text_field="text",
        seed=20260506,
    )
    trainer = SFTTrainer(model=model, tokenizer=tok,
                         train_dataset=train_ds, eval_dataset=eval_ds, args=cfg)
    trainer.train()
    trainer.save_model(str(OUT_DIR / "final"))
    tok.save_pretrained(str(OUT_DIR / "final"))
    print(f"[done] saved to {OUT_DIR / 'final'}")


def main():
    if not TRAIN_FILE.exists():
        print(f"[error] missing {TRAIN_FILE}; run prototype/data/10_merge_train_jsonl.py first", file=sys.stderr)
        sys.exit(2)
    try:
        import unsloth  # noqa
        print("[path] unsloth available")
        train_unsloth()
    except Exception as e:
        print(f"[fallback] unsloth unavailable ({e}); using HF+PEFT")
        train_hf_peft()


if __name__ == "__main__":
    main()
