#!/usr/bin/env python3
"""Compute cross-variant language-model loss on a shared 4L eval set."""
from __future__ import annotations

import json
import os
import pathlib
import sys
import time
from typing import Iterable

os.environ.setdefault("HF_HOME", "/scratch/hpc198a01/젬마4해커톤/hf_cache")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("WANDB_DISABLED", "true")

import torch
import unsloth
from datasets import load_dataset
from torch.utils.data import DataLoader
from unsloth import FastLanguageModel


PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
DATA_FILE = pathlib.Path(os.environ.get(
    "COMMON_EVAL_FILE",
    str(PROJ / "prototype/data/eval_4l_common.jsonl"),
))
OUT_FILE = pathlib.Path(os.environ.get(
    "COMMON_LOSS_OUT_FILE",
    str(PROJ / "paper/figures/common_4l_loss.json"),
))
LORA_OUT = PROJ / "lora_out"
STOCK = PROJ / "models/unsloth-gemma-4-E2B-it"
FILTER = os.environ.get("VARIANTS_FILTER", "")
MAX_SEQ = int(os.environ.get("MAX_SEQ", "2048"))
BATCH_SIZE = int(os.environ.get("COMMON_LOSS_BATCH", "1"))
MAX_EXAMPLES = int(os.environ.get("COMMON_LOSS_MAX_EXAMPLES", "0"))
FORCE = os.environ.get("FORCE_COMMON_LOSS", "0") == "1"


def log(msg: str) -> None:
    print(msg, flush=True)


def checkpoint_step(path: pathlib.Path) -> int:
    try:
        return int(path.name.rsplit("-", 1)[-1])
    except ValueError:
        return -1


def discover() -> list[tuple[str, str, bool]]:
    wanted = {p.strip() for p in FILTER.split(",") if p.strip()}
    items: list[tuple[str, str, bool]] = []
    if not wanted or "stock" in wanted:
        items.append(("stock", str(STOCK), False))
    for d in sorted(LORA_OUT.iterdir()):
        if not d.is_dir() or (wanted and d.name not in wanted):
            continue
        ad = d / "adapter"
        if ad.is_dir() and (ad / "adapter_config.json").exists():
            items.append((d.name, str(ad), True))
            continue
        checkpoints = sorted(
            [c for c in d.glob("checkpoint-*") if (c / "adapter_config.json").exists()],
            key=checkpoint_step,
        )
        if checkpoints:
            items.append((d.name, str(checkpoints[-1]), True))
    return items


def load_texts(tok) -> list[str]:
    ds = load_dataset("json", data_files=str(DATA_FILE), split="train")
    if MAX_EXAMPLES > 0:
        ds = ds.select(range(min(MAX_EXAMPLES, len(ds))))
    texts = []
    for ex in ds:
        msgs = ex.get("messages")
        if msgs:
            texts.append(tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False))
        else:
            texts.append(json.dumps(ex, ensure_ascii=False))
    return texts


def batches(items: list[str], n: int) -> Iterable[list[str]]:
    for i in range(0, len(items), n):
        yield items[i:i + n]


def eval_one(name: str, path: str, is_adapter: bool) -> dict:
    log(f"[load] {name} from {path}")
    t0 = time.time()
    model, tok = FastLanguageModel.from_pretrained(
        model_name=path,
        max_seq_length=MAX_SEQ,
        load_in_4bit=False,
        load_in_16bit=True,
        full_finetuning=False,
    )
    model.eval()
    texts = load_texts(tok)
    total_loss = 0.0
    total_tokens = 0
    text_tok = getattr(tok, "tokenizer", tok)
    pad_id = text_tok.pad_token_id if text_tok.pad_token_id is not None else text_tok.eos_token_id
    with torch.no_grad():
        for batch in batches(texts, BATCH_SIZE):
            enc = text_tok(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=MAX_SEQ,
            ).to(model.device)
            labels = enc["input_ids"].clone()
            labels[enc["attention_mask"] == 0] = -100
            out = model(**enc, labels=labels)
            n_tokens = int((labels != -100).sum().item())
            total_loss += float(out.loss.item()) * n_tokens
            total_tokens += n_tokens
    loss = total_loss / max(total_tokens, 1)
    result = {
        "variant": name,
        "adapter_path": path,
        "is_adapter": is_adapter,
        "common_eval_file": str(DATA_FILE),
        "examples": len(texts),
        "tokens": total_tokens,
        "loss": loss,
        "perplexity": float(torch.exp(torch.tensor(loss)).item()),
        "elapsed_sec": round(time.time() - t0, 2),
    }
    del model, tok
    torch.cuda.empty_cache()
    log(f"[loss] {name} loss={loss:.4f} ppl={result['perplexity']:.2f}")
    return result


def main() -> None:
    if not DATA_FILE.exists():
        raise SystemExit(f"missing common eval file: {DATA_FILE}")
    existing = json.loads(OUT_FILE.read_text(encoding="utf-8")) if OUT_FILE.exists() else {"variants": {}}
    existing.setdefault("common_eval_file", str(DATA_FILE))
    existing.setdefault("variants", {})
    for name, path, is_adapter in discover():
        if name in existing["variants"] and not FORCE:
            log(f"[skip] {name}")
            continue
        try:
            existing["variants"][name] = eval_one(name, path, is_adapter)
        except Exception as exc:
            log(f"[fail] {name}: {exc}")
    OUT_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"[write] {OUT_FILE}")


if __name__ == "__main__":
    main()
