#!/usr/bin/env python3
"""Wire moon1 SoulX-FlashHead avatar pipeline to Gemma 4 (premium mode).

Flow:
  Phone client →(text/audio + family-context system prompt)→
  this server (FastAPI) →(Gemma 4 26B, MTP drafter, optional LoRA)→ text response
  → ElevenLabs TTS (or local TTS) → wav
  → SoulX-FlashHead Lite (existing /home/moon1/SoulX-FlashHead/)
  → mp4 video chunks → cloudflared tunnel → phone

This is a stub; real implementation lives on moon1.
"""
from __future__ import annotations
import os, json, time
from fastapi import FastAPI
from pydantic import BaseModel
import httpx

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
LLM_MODEL = os.environ.get("LLM_MODEL", "gemma4:26b")
DRAFT_MODEL = os.environ.get("DRAFT_MODEL", "gemma4:26b-mtp-drafter")  # if Ollama supports
SOULX_API = os.environ.get("SOULX_API", "http://moon1.local:7864/api/render")

app = FastAPI()


class TutorRequest(BaseModel):
    speaker: str            # "father" | "mother" | "child"
    speaker_l1: str         # "ko" | "ru" | "en"
    bridge: str             # "ru" | "en"  (for wife learning ko)
    age_band: str           # "0-2" | "2-4" | "4-6" | "6-8"
    target_lang: str        # "ko" | "ru" | "en"
    user_text: str
    persona: str = "ru_l1_korean_teacher"   # one of {ru_l1_korean_teacher, en_l1_korean_teacher, ...}


SYSTEM_TEMPLATE = (
    "You are the trilingual KO/RU/EN family tutor. "
    "Family: father (KO L1) + mother (RU L1, learning KO via {bridge} bridge) + child age {age_band} (KO L1).\n"
    "Current speaker: {speaker} (L1={speaker_l1}). Target language: {target_lang}.\n"
    "Persona: {persona}. Respond in the target language, with L1-aware coaching when needed.\n"
    "If the user asks for a tool call (pronunciation score, recommendation, etc.), respond with strict JSON."
)


@app.post("/tutor")
async def tutor(req: TutorRequest):
    sys = SYSTEM_TEMPLATE.format(**req.dict())
    body = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": sys},
            {"role": "user", "content": req.user_text},
        ],
        "stream": False,
        "options": {"temperature": 0.5, "num_predict": 512}
    }
    async with httpx.AsyncClient(timeout=120) as cli:
        r = await cli.post(f"{OLLAMA}/api/chat", json=body)
        r.raise_for_status()
        out = r.json()
    return {
        "text": out["message"]["content"],
        "elapsed": out.get("total_duration", 0) / 1e9,
        "model": LLM_MODEL,
    }


@app.post("/tutor_with_avatar")
async def tutor_with_avatar(req: TutorRequest):
    """Premium mode: Gemma 4 → text → SoulX render → mp4 chunks."""
    text_resp = await tutor(req)
    text = text_resp["text"]
    async with httpx.AsyncClient(timeout=600) as cli:
        rr = await cli.post(SOULX_API, json={
            "text": text,
            "persona": req.persona,
            "voice_lang": req.target_lang,
        })
        rr.raise_for_status()
    return {
        "text": text,
        "video_url": rr.json().get("stream_url"),
        "elapsed_total": text_resp["elapsed"] + rr.json().get("render_s", 0),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8765")))
