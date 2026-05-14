#!/usr/bin/env python3
"""LoRA-v2 full training — 20.5K trilingual + transliteration corrections.

vs v1: +300 transliteration training pairs to fix script-direction regression.
"""
from __future__ import annotations
import os, json, pathlib, time

os.environ.setdefault("HF_HOME", "/PATH/REDACTED")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("WANDB_DISABLED", "true")

import unsloth
from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer, SFTConfig

MODEL = "/PATH/REDACTED"
DATA = "/PATH/REDACTED"
EVAL = "/PATH/REDACTED"
OUT = "/PATH/REDACTED"
MAX_SEQ = 2048

print(f"[v2] start {time.strftime('%H:%M:%S')}")

model, tok = FastLanguageModel.from_pretrained(
    model_name=MODEL,
    max_seq_length=MAX_SEQ,
    load_in_4bit=False,
    load_in_16bit=True,
    full_finetuning=False,
)

train_ds = load_dataset("json", data_files=DATA, split="train")
eval_ds = load_dataset("json", data_files=EVAL, split="train")
print(f"[ds] train={len(train_ds)} eval={len(eval_ds)}")


def to_text(ex):
    if "messages" in ex and ex["messages"]:
        return {"text": tok.apply_chat_template(ex["messages"], tokenize=False, add_generation_prompt=False)}
    return {"text": json.dumps(ex, ensure_ascii=False)}


train_ds = train_ds.map(to_text, remove_columns=train_ds.column_names, num_proc=8)
eval_ds = eval_ds.map(to_text, remove_columns=eval_ds.column_names, num_proc=4)

model = FastLanguageModel.get_peft_model(
    model, r=32, lora_alpha=64, lora_dropout=0.05,
    target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
    bias="none", use_gradient_checkpointing="unsloth",
    random_state=20260507, max_seq_length=MAX_SEQ,
)

cfg = SFTConfig(
    output_dir=OUT, dataset_text_field="text",
    max_seq_length=MAX_SEQ,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    num_train_epochs=2,
    learning_rate=2e-4, warmup_ratio=0.03, lr_scheduler_type="cosine",
    logging_steps=20, save_steps=500,
    eval_strategy="steps", eval_steps=200,
    optim="adamw_8bit", bf16=True, fp16=False,
    seed=20260507, dataset_num_proc=4,
    report_to="none",
    save_total_limit=3,
)
trainer = SFTTrainer(model=model, tokenizer=tok,
                     train_dataset=train_ds, eval_dataset=eval_ds, args=cfg)
trainer.train()
model.save_pretrained(OUT + "/adapter")
tok.save_pretrained(OUT + "/adapter")
print(f"[done] {time.strftime('%H:%M:%S')} adapter at {OUT}/adapter")
