#!/usr/bin/env python3
"""Gradio demo for the Trilingual KO+RU+EN family-tutor LoRA.

Runs the LoRA-v2 adapter on Gemma 4 E2B and exposes:
  1. Translation tab (any direction among KO/RU/EN)
  2. Trilingual object-card tab (Korean object → JSON learning card)
  3. Family scenario tab (situation + age band → JSON dialog)
  4. L1-aware grammar explanation tab
  5. Cross-script transliteration tab
  6. Free chat tab

Deploy as HuggingFace Space (CPU/GPU) or run locally.
"""
import os, json, pathlib
os.environ.setdefault("HF_HOME", "/PATH/REDACTED")

import gradio as gr
import torch
import unsloth
from unsloth import FastLanguageModel

PROJ = pathlib.Path("/PATH/REDACTED")
ADAPTER = os.environ.get("ADAPTER_PATH", str(PROJ / "lora_out/lora_v2/adapter"))

print(f"[demo] loading {ADAPTER}")
model, tok = FastLanguageModel.from_pretrained(
    model_name=ADAPTER, max_seq_length=2048,
    load_in_4bit=False, load_in_16bit=True, full_finetuning=False,
)
FastLanguageModel.for_inference(model)


def gen(prompt: str, max_new: int = 512, temperature: float = 0.3) -> str:
    messages = [{"role": "user", "content": prompt}]
    text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    text_tok = getattr(tok, "tokenizer", tok)
    enc = text_tok(text, return_tensors="pt", add_special_tokens=False)
    input_ids = enc.input_ids.to(model.device)
    attn = enc.attention_mask.to(model.device) if enc.get("attention_mask") is not None else None
    with torch.inference_mode():
        out = model.generate(
            input_ids=input_ids, attention_mask=attn,
            max_new_tokens=max_new,
            do_sample=temperature > 0,
            temperature=temperature if temperature > 0 else None,
            top_p=0.9, pad_token_id=text_tok.eos_token_id,
        )
    txt = text_tok.decode(out[0][input_ids.shape[1]:], skip_special_tokens=True).strip()
    return txt


# ---------- tabs ----------
def translate(text, src, tgt):
    if not text.strip():
        return ""
    return gen(f"Translate {src.upper()} to {tgt.upper()} only (no commentary):\n\n{text}")


def card(object_ko, age_band, bridge):
    sys_prompt = (
        f"You are the trilingual KO/RU/EN family AI tutor. "
        f"Family: father (KO L1), mother (RU L1, bridge={bridge}), "
        f"child age {age_band}. When given a Korean object, output a JSON learning card."
    )
    user = f"Object: {object_ko}"
    return gen(f"{sys_prompt}\n\n{user}", max_new=1500)


def scenario(situation, age_band, mom_ko_level, bridge):
    sys_prompt = "You are the trilingual KO/RU/EN family AI tutor. Generate JSON dialogs for daily co-learning."
    user = (f"Scenario: {situation}\nAge: {age_band}\n"
            f"Mother KO level: {mom_ko_level}\nBridge: {bridge}\n")
    return gen(f"{sys_prompt}\n\n{user}", max_new=1500)


def grammar(concept, l1, target_lang):
    sys_prompt = (f"Explain a {target_lang.upper()} grammar concept to a {l1.upper()}-L1 learner "
                  f"in {l1.upper()} (3-4 sentences). Cite concrete examples from both languages.")
    return gen(f"{sys_prompt}\n\n{concept}")


def translit(text, src_lang, tgt_script):
    sys_prompt = (
        "You are a phonetic transliterator for a multicultural Korean-Russian-English household. "
        "Output ONLY the requested script. Do NOT translate."
    )
    user = f"Convert to a {tgt_script} phonetic transliteration of the {src_lang.upper()} text:\n\n{text}"
    return gen(f"{sys_prompt}\n\n{user}")


def chat(message, history):
    history = history or []
    convo = ""
    for u, a in history:
        convo += f"User: {u}\nAssistant: {a}\n"
    convo += f"User: {message}\nAssistant:"
    resp = gen(convo, temperature=0.7)
    history.append((message, resp))
    return "", history


# ---------- UI ----------
with gr.Blocks(title="Trilingual Family Tutor (Gemma 4 E2B + LoRA-v2)") as demo:
    gr.Markdown("""
    # 🏡 Trilingual Family Tutor — KO + RU + EN
    Gemma 4 E2B on-device + Apache 2.0 LoRA adapter trained on a multicultural family use case.
    Open-source: [GitHub](https://github.com/[author]/gemma4-trilingual-family) ·
    [Paper](https://arxiv.org/abs/[id]) ·
    Family-as-Evaluator [protocol spec](https://github.com/[author]/gemma4-trilingual-family/blob/main/tools/fae_protocol/SPEC.md).
    """)

    with gr.Tab("Translation"):
        with gr.Row():
            src = gr.Dropdown(["ko","ru","en"], value="ko", label="From")
            tgt = gr.Dropdown(["ko","ru","en"], value="ru", label="To")
        text = gr.Textbox(lines=3, label="Input text")
        out = gr.Textbox(lines=3, label="Translation")
        btn = gr.Button("Translate")
        btn.click(translate, [text, src, tgt], out)

    with gr.Tab("Trilingual object card"):
        ob = gr.Textbox(label="Korean object name (e.g., 사과, 강아지, 자동차)")
        age = gr.Dropdown(["0-2","2-4","4-6","6-8"], value="0-2", label="Child age band")
        br = gr.Dropdown(["ru","en"], value="ru", label="Mother's bridge language")
        out2 = gr.JSON(label="Learning card")
        btn2 = gr.Button("Generate card")
        def card_wrapper(*args):
            try: return json.loads(card(*args))
            except: return {"raw_text": card(*args)}
        btn2.click(card_wrapper, [ob, age, br], out2)

    with gr.Tab("Family scenario"):
        sit = gr.Textbox(label="Situation (e.g., 식탁 아침 식사, 공원 산책)")
        age3 = gr.Dropdown(["0-2","2-4","4-6","6-8"], value="2-4", label="Child age band")
        mko = gr.Dropdown(["초","중","고"], value="중", label="Mother's KO level")
        br3 = gr.Dropdown(["ru","en"], value="en", label="Mother's bridge")
        out3 = gr.JSON(label="Dialog")
        btn3 = gr.Button("Generate scenario")
        def scen_wrapper(*args):
            try: return json.loads(scenario(*args))
            except: return {"raw_text": scenario(*args)}
        btn3.click(scen_wrapper, [sit, age3, mko, br3], out3)

    with gr.Tab("L1-aware grammar"):
        cc = gr.Textbox(label="Grammar concept (e.g., '에' vs '에서')")
        l1 = gr.Dropdown(["ru","en","ko"], value="ru", label="Learner's L1")
        tl = gr.Dropdown(["ko","ru","en"], value="ko", label="Target language")
        out4 = gr.Textbox(lines=4, label="Explanation")
        btn4 = gr.Button("Explain")
        btn4.click(grammar, [cc, l1, tl], out4)

    with gr.Tab("Cross-script transliteration"):
        t = gr.Textbox(label="Source text")
        sl = gr.Dropdown(["ko","ru","en"], value="ko", label="Source language")
        ts = gr.Dropdown(
            ["Cyrillic","Hangul","Latin (Revised Romanization)","Latin (BGN/PCGN)"],
            value="Cyrillic", label="Target script")
        out5 = gr.Textbox(lines=2, label="Transliteration")
        btn5 = gr.Button("Transliterate")
        btn5.click(translit, [t, sl, ts], out5)

    with gr.Tab("Free chat"):
        cb = gr.Chatbot()
        cm = gr.Textbox(label="Message")
        cm.submit(chat, [cm, cb], [cm, cb])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
