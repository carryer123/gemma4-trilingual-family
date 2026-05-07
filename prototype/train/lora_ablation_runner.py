#!/usr/bin/env python3
"""Generalized LoRA trainer for ablation runs.

Reads training data path from $TRAIN_FILE, writes adapter to $OUT_DIR.
Same hyperparameters as v2 unless overridden via env.

Run example:
  TRAIN_FILE=prototype/data/ablation/L_direct_train.jsonl \\
  OUT_DIR=lora_out/L_direct \\
  CUDA_VISIBLE_DEVICES=0 \\
  ./venv/bin/python prototype/train/lora_ablation_runner.py
"""
from __future__ import annotations
import os, json, pathlib, time

os.environ.setdefault("HF_HOME", "/scratch/hpc198a01/젬마4해커톤/hf_cache")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("WANDB_DISABLED", "true")

import unsloth
from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer, SFTConfig

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
MODEL = str(PROJ / "models/unsloth-gemma-4-E2B-it")
TRAIN_FILE = os.environ.get("TRAIN_FILE")
OUT_DIR = os.environ.get("OUT_DIR")
EVAL_FILE = os.environ.get("EVAL_FILE", str(PROJ / "prototype/data/eval_v2.jsonl"))
MAX_SEQ = int(os.environ.get("MAX_SEQ", "2048"))
EPOCHS = int(os.environ.get("EPOCHS", "2"))
MAX_STEPS = int(os.environ.get("MAX_STEPS", "0"))  # 0 = use epochs
LORA_R = int(os.environ.get("LORA_R", "32"))
LORA_ALPHA = int(os.environ.get("LORA_ALPHA", "64"))

assert TRAIN_FILE, "TRAIN_FILE env required"
assert OUT_DIR, "OUT_DIR env required"

print(f"[abl] {time.strftime('%H:%M:%S')} train={TRAIN_FILE} out={OUT_DIR}")

model, tok = FastLanguageModel.from_pretrained(
    model_name=MODEL, max_seq_length=MAX_SEQ,
    load_in_4bit=False, load_in_16bit=True, full_finetuning=False,
)

train_ds = load_dataset("json", data_files=TRAIN_FILE, split="train")
eval_ds = load_dataset("json", data_files=EVAL_FILE, split="train")
print(f"[ds] train={len(train_ds)} eval={len(eval_ds)}")

def to_text(ex):
    if "messages" in ex and ex["messages"]:
        return {"text": tok.apply_chat_template(ex["messages"], tokenize=False, add_generation_prompt=False)}
    return {"text": json.dumps(ex, ensure_ascii=False)}

train_ds = train_ds.map(to_text, remove_columns=train_ds.column_names, num_proc=8)
eval_ds = eval_ds.map(to_text, remove_columns=eval_ds.column_names, num_proc=4)

model = FastLanguageModel.get_peft_model(
    model, r=LORA_R, lora_alpha=LORA_ALPHA, lora_dropout=0.05,
    target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
    bias="none", use_gradient_checkpointing="unsloth",
    random_state=20260507, max_seq_length=MAX_SEQ,
)

cfg_kwargs = dict(
    output_dir=OUT_DIR, dataset_text_field="text",
    max_seq_length=MAX_SEQ,
    per_device_train_batch_size=2, gradient_accumulation_steps=4,
    learning_rate=2e-4, warmup_ratio=0.03, lr_scheduler_type="cosine",
    logging_steps=20, save_steps=500,
    eval_strategy="steps", eval_steps=200,
    optim="adamw_8bit", bf16=True, fp16=False,
    seed=20260507, dataset_num_proc=4,
    report_to="none", save_total_limit=2,
)
if MAX_STEPS > 0:
    cfg_kwargs["max_steps"] = MAX_STEPS
else:
    cfg_kwargs["num_train_epochs"] = EPOCHS

trainer = SFTTrainer(model=model, tokenizer=tok,
                     train_dataset=train_ds, eval_dataset=eval_ds,
                     args=SFTConfig(**cfg_kwargs))
trainer.train()
model.save_pretrained(OUT_DIR + "/adapter")
tok.save_pretrained(OUT_DIR + "/adapter")
print(f"[done] {time.strftime('%H:%M:%S')} {OUT_DIR}/adapter")
