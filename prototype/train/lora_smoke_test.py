#!/usr/bin/env python3
"""LoRA smoke test: 200 samples, 50 steps, on 1 GPU. Verifies pipeline end-to-end.

Run:
  cd /PATH/REDACTED
  source venv/bin/activate
  CUDA_VISIBLE_DEVICES=0 python prototype/train/lora_smoke_test.py
"""
from __future__ import annotations
import os, json, pathlib

os.environ.setdefault("HF_HOME", "/PATH/REDACTED")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("WANDB_DISABLED", "true")

import unsloth  # apply patches BEFORE transformers import
from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer, SFTConfig

MODEL = os.environ.get("MODEL", "/PATH/REDACTED")
DATA = os.environ.get("DATA", "/PATH/REDACTED")
OUT = os.environ.get("OUT", "/PATH/REDACTED")
MAX_SEQ = int(os.environ.get("MAX_SEQ", "2048"))
N_SAMPLES = int(os.environ.get("N_SAMPLES", "200"))
MAX_STEPS = int(os.environ.get("MAX_STEPS", "50"))

print(f"[smoke] model={MODEL} data={DATA} n={N_SAMPLES} steps={MAX_STEPS}")

model, tok = FastLanguageModel.from_pretrained(
    model_name=MODEL,
    max_seq_length=MAX_SEQ,
    load_in_4bit=False,
    load_in_16bit=True,
    full_finetuning=False,
)

ds = load_dataset("json", data_files=DATA, split="train")
print(f"[ds] loaded {len(ds)}; subsetting to {N_SAMPLES}")
ds = ds.select(range(N_SAMPLES))


def to_text(ex):
    if "messages" in ex and ex["messages"]:
        return {"text": tok.apply_chat_template(ex["messages"], tokenize=False, add_generation_prompt=False)}
    return {"text": json.dumps(ex, ensure_ascii=False)}


ds = ds.map(to_text, remove_columns=ds.column_names, num_proc=4)
print(f"[ds] sample text:\n{ds[0]['text'][:300]}")

model = FastLanguageModel.get_peft_model(
    model, r=16, lora_alpha=16, lora_dropout=0.0,
    target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
    bias="none", use_gradient_checkpointing="unsloth",
    random_state=20260506, max_seq_length=MAX_SEQ,
)

cfg = SFTConfig(
    output_dir=OUT, dataset_text_field="text",
    max_seq_length=MAX_SEQ,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    max_steps=MAX_STEPS,
    learning_rate=2e-4, warmup_ratio=0.03,
    logging_steps=5, save_steps=200,
    optim="adamw_8bit", bf16=True, fp16=False,
    seed=20260506, dataset_num_proc=4,
    report_to="none",
)
trainer = SFTTrainer(model=model, tokenizer=tok, train_dataset=ds, args=cfg)
trainer.train()
model.save_pretrained(OUT + "/adapter")
tok.save_pretrained(OUT + "/adapter")
print(f"[done] adapter saved to {OUT}/adapter")
