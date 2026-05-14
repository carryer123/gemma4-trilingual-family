#!/usr/bin/env python3
"""
Merge LoRA-v2 into Gemma 4 E2B base, then export to LiteRT-LM int4 .litertlm.

This is the HPC-side pipeline that produces the on-device artifact:
    app/src/main/assets/gemma-4-E2B-it-merged.litertlm

Stages:
  1. Load HF safetensors base + LoRA-v2 adapter (PEFT).
  2. peft.merge_and_unload() → standalone HF model with LoRA-v2 baked in.
  3. ai_edge_torch convert → LiteRT (.tflite) with int4 PTQ.
  4. Bundle .tflite + tokenizer + chat template → .litertlm.

Run on HPC GPU (≥24GB recommended). Wall time: 4-8 h on a single H100.

Env knobs:
  BASE_MODEL=hf_cache/...gemma-4-E2B-it
  LORA_PATH=/PATH/REDACTED
  OUT_LITERTLM=/PATH/REDACTED

NOTE: ai-edge-torch + LiteRT-LM bundler API surfaces evolve fast. If a step
fails, consult:
  https://ai.google.dev/edge/litert-lm
  https://ai.google.dev/gemma/docs/conversions/hf-to-mediapipe-task
  https://github.com/google-ai-edge/ai-edge-torch
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

BASE_MODEL = os.environ.get(
    "BASE_MODEL",
    "/PATH/REDACTED",
)
LORA_PATH = os.environ.get(
    "LORA_PATH",
    "/PATH/REDACTED",
)
OUT_DIR = Path(os.environ.get(
    "OUT_DIR",
    "/PATH/REDACTED",
))
OUT_LITERTLM = OUT_DIR / "gemma-4-E2B-it-merged.litertlm"
WORK = Path(os.environ.get(
    "WORK_DIR",
    "/PATH/REDACTED",
))


def stage1_merge() -> Path:
    """LoRA-v2 → base manual merge (bypasses peft for Gemma4ClippableLinear).

    peft 0.18.1 doesn't recognise Gemma4ClippableLinear as a Linear wrapper, but
    the LoRA was actually attached to its inner `.linear` (a real nn.Linear), so
    we apply `W += (alpha/r) · B @ A` directly module-by-module.
    """
    import json
    import torch
    from collections import defaultdict
    from safetensors import safe_open
    from transformers import AutoModelForCausalLM, AutoProcessor, AutoTokenizer

    merged_dir = WORK / "merged_hf"
    if (merged_dir / "config.json").exists():
        print(f"[stage1] skip — merged exists at {merged_dir}")
        return merged_dir
    merged_dir.mkdir(parents=True, exist_ok=True)

    cfg = json.loads((Path(LORA_PATH) / "adapter_config.json").read_text())
    scaling = float(cfg["lora_alpha"]) / float(cfg["r"])
    print(f"[stage1] LoRA r={cfg['r']} alpha={cfg['lora_alpha']} → scaling={scaling}")

    print(f"[stage1] loading base {BASE_MODEL}")
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, dtype=torch.bfloat16, device_map="auto",
    )

    print(f"[stage1] loading LoRA-v2 {LORA_PATH}")
    pairs: dict[str, dict[str, torch.Tensor]] = defaultdict(dict)
    with safe_open(str(Path(LORA_PATH) / "adapter_model.safetensors"), framework="pt") as f:
        for key in f.keys():
            # key like: base_model.model.<module_path>.lora_A.weight
            assert key.startswith("base_model.model."), f"unexpected key {key}"
            inner = key[len("base_model.model."):]
            if inner.endswith(".lora_A.weight"):
                mod_path = inner[: -len(".lora_A.weight")]
                pairs[mod_path]["A"] = f.get_tensor(key)
            elif inner.endswith(".lora_B.weight"):
                mod_path = inner[: -len(".lora_B.weight")]
                pairs[mod_path]["B"] = f.get_tensor(key)
            else:
                print(f"[stage1] WARN ignoring {key}")

    print(f"[stage1] applying {len(pairs)} LoRA deltas …")
    applied, skipped = 0, []
    for mod_path, ab in pairs.items():
        if "A" not in ab or "B" not in ab:
            skipped.append(mod_path); continue
        try:
            module = model.get_submodule(mod_path)
        except AttributeError:
            skipped.append(mod_path); continue
        weight = getattr(module, "weight", None)
        if weight is None:
            skipped.append(mod_path); continue
        A = ab["A"].to(weight.device, dtype=torch.float32)
        B = ab["B"].to(weight.device, dtype=torch.float32)
        delta = scaling * (B @ A)
        with torch.no_grad():
            weight.data += delta.to(weight.dtype)
        applied += 1
    print(f"[stage1] applied={applied} skipped={len(skipped)}")
    if skipped[:3]:
        print(f"[stage1] first skipped: {skipped[:3]}")

    print(f"[stage1] saving merged → {merged_dir}")
    model.save_pretrained(merged_dir, safe_serialization=True)
    # Persist tokenizer + processor (Gemma 4 audio uses a multimodal processor)
    try:
        AutoProcessor.from_pretrained(BASE_MODEL).save_pretrained(merged_dir)
    except Exception:
        AutoTokenizer.from_pretrained(BASE_MODEL).save_pretrained(merged_dir)
    print(f"[stage1] ok → {merged_dir}")
    return merged_dir


def stage2_export_litert(merged_dir: Path) -> Path:
    """HF safetensors → LiteRT (.tflite) with int4 PTQ via ai-edge-torch."""
    try:
        import ai_edge_torch  # noqa: F401
        from ai_edge_torch.generative.utilities import converter as gen_conv
    except ImportError as exc:
        sys.exit(
            f"[stage2] ai-edge-torch not installed ({exc}). "
            "pip install -U ai-edge-torch ai-edge-litert ai-edge-quantizer"
        )

    tflite_dir = WORK / "litert"
    tflite_dir.mkdir(parents=True, exist_ok=True)
    out_tflite = tflite_dir / "gemma4_e2b_int4.tflite"
    if out_tflite.exists():
        print(f"[stage2] skip — {out_tflite}")
        return out_tflite

    # API surface for ai-edge-torch.generative is in flux; below is the 2026
    # canonical one. Adjust per repo HEAD if it has moved.
    print(f"[stage2] convert {merged_dir} → {out_tflite}")
    gen_conv.convert_to_tflite(
        checkpoint_path=str(merged_dir),
        output_path=str(out_tflite),
        prefill_seq_len=1024,
        kv_cache_max_len=2048,
        quantize="dynamic_int4_block32",
    )
    print(f"[stage2] ok → {out_tflite}")
    return out_tflite


def stage3_bundle_task(merged_dir: Path, tflite: Path) -> Path:
    """Bundle .tflite + tokenizer + chat template → MediaPipe .task.

    This is the cross-platform artifact (Android MediaPipe Genai + iOS
    MediaPipeTasksGenAI both load the same .task file).
    """
    out_task = OUT_DIR / "gemma-4-E2B-it-merged.task"
    try:
        from mediapipe.tasks.python.genai import bundler as mp_bundler  # type: ignore
    except ImportError:
        sys.exit(
            "[stage3] mediapipe genai bundler not installed. "
            "pip install -U 'mediapipe>=0.10.27'"
        )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[stage3] bundle → {out_task}")
    config = mp_bundler.BundleConfig(
        tflite_model=str(tflite),
        tokenizer_model=str(Path(merged_dir) / "tokenizer.json"),
        start_token="<bos>",
        stop_tokens=["<eos>", "<end_of_turn>"],
        output_filename=str(out_task),
        prompt_prefix="<start_of_turn>user\n",
        prompt_suffix="<end_of_turn>\n<start_of_turn>model\n",
    )
    mp_bundler.create_bundle(config)
    print(f"[stage3] ok → {out_task} ({out_task.stat().st_size/1e9:.2f} GB)")
    return out_task


def stage4_bundle_litertlm(merged_dir: Path, tflite: Path) -> Path | None:
    """Optional: also produce a .litertlm bundle for future LiteRT-LM Android.
    Skipped if ai-edge-litert-lm not installed (it is not required for the demo)."""
    try:
        from ai_edge_litert_lm import bundler  # type: ignore
    except ImportError:
        print("[stage4] skip — ai-edge-litert-lm not installed (optional)")
        return None
    print(f"[stage4] bundle → {OUT_LITERTLM}")
    bundler.bundle(
        tflite_path=str(tflite),
        tokenizer_dir=str(merged_dir),
        chat_template_path=str(Path(merged_dir) / "chat_template.jinja"),
        output_path=str(OUT_LITERTLM),
    )
    return OUT_LITERTLM


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    merged = stage1_merge()
    tflite = stage2_export_litert(merged)
    task_bundle = stage3_bundle_task(merged, tflite)
    stage4_bundle_litertlm(merged, tflite)  # optional, ignored if missing
    print("\n[done] cross-platform artifact:", task_bundle)
    print("[done] copy this to:")
    print("  Android: prototype/android/app/src/main/assets/gemma-4-E2B-it-merged.task")
    print("  iOS:     prototype/ios/Models/  (then drag into Xcode)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
