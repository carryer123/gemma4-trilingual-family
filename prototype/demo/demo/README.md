# Gradio Demo — Trilingual Family Tutor

## Local run

```bash
cd /PATH/REDACTED
source venv/bin/activate
pip install gradio
ADAPTER_PATH=lora_out/lora_v2/adapter \
  CUDA_VISIBLE_DEVICES=0 \
  ./venv/bin/python prototype/demo/app.py
```

Browse to http://localhost:7860 (or expose via `share=True` / cloudflared / ngrok).

## HuggingFace Space deployment

1. Create new Space at huggingface.co/spaces — choose Gradio SDK + GPU (T4 small or A10G)
2. Add files:
   - `app.py` — the file in this directory (rename or symlink)
   - `requirements.txt`:
     ```
     unsloth
     unsloth_zoo
     transformers>=4.50
     peft>=0.13
     trl>=0.12
     bitsandbytes>=0.44
     accelerate>=1.0
     gradio>=4.0
     hf_transfer
     ```
   - `README.md` (Space card)
3. Push the LoRA-v2 adapter to a HF model repo (or include in the Space if small)
4. Set `ADAPTER_PATH` in Space secrets to the HF model repo ID

## Five tabs (matches paper Section 3.1 capabilities)

1. **Translation** — KO ↔ RU ↔ EN any direction
2. **Trilingual object card** — Korean object name → JSON learning card with
   3-language word + 4-direction phonetic + L1 contrast + family cards per role
3. **Family scenario** — daily-life situation + age + parent KO level + bridge
   → JSON dialog with simultaneous learning targets per family member
4. **L1-aware grammar** — explain a Korean/Russian/English grammar concept in
   the learner's L1, with concrete contrast examples
5. **Cross-script transliteration** — KO ↔ {Cyrillic, Hangul, Latin}

These five tabs are also the five categories of the Family-as-Evaluator probe
set (Appendix C of the paper). Reviewers / family-evaluators can use the demo
to *replicate the protocol* against any input they choose.
