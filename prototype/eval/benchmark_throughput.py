#!/usr/bin/env python3
"""Measure server-side tokens/sec on A100 for stock vs LoRA-merged models.

Outputs JSON per model with: model_path, n_prompts, total_tokens, total_sec,
tokens_per_sec, ttft_sec_mean.
"""
import os, sys, json, time, pathlib, argparse
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

def measure(model_path: str, label: str, prompts: list[str], max_new: int = 128) -> dict:
    print(f'[{label}] loading {model_path}', flush=True)
    tok = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tok.pad_token is None: tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_path, dtype=torch.bfloat16, device_map='cuda', trust_remote_code=True,
    )
    model.eval()
    # warmup
    inp = tok('hello', return_tensors='pt').to('cuda')
    with torch.inference_mode():
        _ = model.generate(**inp, max_new_tokens=8, do_sample=False, pad_token_id=tok.pad_token_id)
    torch.cuda.synchronize()

    ttfts, decode_ts, total_new = [], [], 0
    t_total0 = time.time()
    for p in prompts:
        # build chat-templated input if possible
        try:
            msgs = [{'role':'user','content':p}]
            text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        except Exception:
            text = p
        enc = tok(text, return_tensors='pt').to('cuda')
        n_in = enc.input_ids.shape[1]
        torch.cuda.synchronize(); t0 = time.time()
        with torch.inference_mode():
            out_first = model.generate(**enc, max_new_tokens=1, do_sample=False, pad_token_id=tok.pad_token_id)
        torch.cuda.synchronize(); t1 = time.time()
        ttfts.append(t1 - t0)
        # full generate
        torch.cuda.synchronize(); t2 = time.time()
        with torch.inference_mode():
            out_full = model.generate(**enc, max_new_tokens=max_new, do_sample=False, pad_token_id=tok.pad_token_id)
        torch.cuda.synchronize(); t3 = time.time()
        n_full = out_full.shape[1] - n_in
        decode_ts.append((t3 - t2, n_full))
        total_new += n_full
    t_total1 = time.time()
    total_sec = t_total1 - t_total0
    decode_total_t = sum(t for t,_ in decode_ts)
    decode_total_n = sum(n for _,n in decode_ts)
    result = {
        'label': label,
        'model_path': model_path,
        'n_prompts': len(prompts),
        'total_new_tokens': total_new,
        'total_wall_sec': total_sec,
        'tokens_per_sec_endtoend': total_new / total_sec if total_sec else 0,
        'tokens_per_sec_decodeonly': decode_total_n / decode_total_t if decode_total_t else 0,
        'ttft_sec_mean': sum(ttfts) / len(ttfts) if ttfts else 0,
        'ttft_sec_median': sorted(ttfts)[len(ttfts)//2] if ttfts else 0,
    }
    print(json.dumps(result, indent=2), flush=True)
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--label', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--probes', default='/PATH/REDACTED')
    ap.add_argument('--n', type=int, default=10)
    ap.add_argument('--max_new', type=int, default=128)
    args = ap.parse_args()

    with open(args.probes) as f:
        prompts = [json.loads(l)['prompt'] for l in f if l.strip()][:args.n]
    print(f'[{args.label}] {args.n} prompts loaded')
    r = measure(args.model, args.label, prompts, max_new=args.max_new)
    pathlib.Path(args.out).write_text(json.dumps(r, indent=2))

if __name__ == '__main__': main()
