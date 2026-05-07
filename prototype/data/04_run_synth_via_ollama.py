#!/usr/bin/env python3
"""Run prompts through Gemma 4 (Ollama) to synthesize learning cards.

No HF token needed — uses local Ollama API.

Reads:  prototype/data/raw/{object_cards,family_scenarios}_prompts.jsonl
Writes: prototype/data/raw/{object_cards,family_scenarios}.jsonl
        prototype/data/raw/*_failed.jsonl (for retry)

Env:
  MODEL=gemma4:26b   (or gemma4:e4b for faster)
  TARGET=object | scenario  (which prompts to run)
  MAX_PROMPTS=100  (0=all)
  PARALLEL=4  (concurrent Ollama requests)
"""
from __future__ import annotations
import os, json, pathlib, time, urllib.request, threading
import queue

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
RAW = PROJ / "prototype/data/raw"

MODEL = os.environ.get("MODEL", "gemma4:26b")
HOSTS_ENV = os.environ.get("OLLAMA_HOSTS", "http://127.0.0.1:11434,http://127.0.0.1:11435,http://127.0.0.1:11436,http://127.0.0.1:11437")
HOSTS = [h.strip() for h in HOSTS_ENV.split(",") if h.strip()]
TARGET = os.environ.get("TARGET", "object")  # object | scenario
MAX_PROMPTS = int(os.environ.get("MAX_PROMPTS", "0"))
PARALLEL = int(os.environ.get("PARALLEL", str(len(HOSTS) * 2)))

if TARGET == "object":
    IN = RAW / "object_cards_prompts.jsonl"
    OUT = RAW / "object_cards.jsonl"
    FAIL = RAW / "object_cards_failed.jsonl"
    REQUIRED_KEYS = {"word", "phonetic", "wife_card", "husband_card", "child_card", "l1_contrast"}
elif TARGET == "scenario":
    IN = RAW / "family_scenarios_prompts.jsonl"
    OUT = RAW / "family_scenarios.jsonl"
    FAIL = RAW / "family_scenarios_failed.jsonl"
    REQUIRED_KEYS = {"scenario", "narrative", "dialog"}
else:
    raise SystemExit(f"Unknown TARGET={TARGET}")


_host_counter = [0]
_host_lock = threading.Lock()
def pick_host():
    with _host_lock:
        h = HOSTS[_host_counter[0] % len(HOSTS)]
        _host_counter[0] += 1
        return h

def call_ollama(system: str, user: str, max_tokens: int = 2048) -> tuple[str, dict]:
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "think": False,           # disable thinking trace — emit final JSON directly
        "options": {"temperature": 0.6, "top_p": 0.9, "num_predict": max_tokens},
        "format": "json",  # Ollama JSON mode
    }
    host = pick_host()
    req = urllib.request.Request(
        f"{host}/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        out = json.loads(resp.read())
    return out["message"]["content"], out


def is_valid(obj) -> bool:
    return isinstance(obj, dict) and REQUIRED_KEYS.issubset(obj)


def worker(jobs: queue.Queue, ok_q: queue.Queue, fail_q: queue.Queue, done_evt: threading.Event):
    while not done_evt.is_set():
        try:
            row = jobs.get(timeout=1)
        except queue.Empty:
            return
        try:
            text, raw = call_ollama(row["system"], row["user"])
            try:
                obj = json.loads(text)
            except Exception as e:
                fail_q.put({"meta": row["meta"], "raw": text, "reason": f"json_parse:{e}"})
                continue
            if is_valid(obj):
                key = "card" if TARGET == "object" else "scenario"
                ok_q.put({"meta": row["meta"], key: obj})
            else:
                fail_q.put({"meta": row["meta"], "raw": text, "reason": "schema"})
        except Exception as e:
            fail_q.put({"meta": row.get("meta", {}), "raw": "", "reason": f"ollama:{e}"})
        finally:
            jobs.task_done()


def main():
    rows = [json.loads(l) for l in IN.read_text(encoding="utf-8").splitlines() if l.strip()]
    if MAX_PROMPTS:
        rows = rows[:MAX_PROMPTS]
    print(f"[run] {TARGET}: {len(rows)} prompts via {MODEL} (parallel={PARALLEL})")

    jobs: queue.Queue = queue.Queue()
    ok_q: queue.Queue = queue.Queue()
    fail_q: queue.Queue = queue.Queue()
    done_evt = threading.Event()

    for r in rows:
        jobs.put(r)

    workers = [threading.Thread(target=worker, args=(jobs, ok_q, fail_q, done_evt), daemon=True)
               for _ in range(PARALLEL)]
    for w in workers:
        w.start()

    n_ok = n_fail = 0
    t0 = time.time()
    last_report = t0
    with OUT.open("w", encoding="utf-8") as fo, FAIL.open("w", encoding="utf-8") as ff:
        while jobs.unfinished_tasks > 0 or not (ok_q.empty() and fail_q.empty()):
            try:
                row = ok_q.get(timeout=1)
                fo.write(json.dumps(row, ensure_ascii=False) + "\n")
                fo.flush()
                n_ok += 1
            except queue.Empty:
                pass
            try:
                row = fail_q.get_nowait()
                ff.write(json.dumps(row, ensure_ascii=False) + "\n")
                ff.flush()
                n_fail += 1
            except queue.Empty:
                pass
            if time.time() - last_report > 15:
                rate = (n_ok + n_fail) / (time.time() - t0)
                print(f"  [progress] ok={n_ok} fail={n_fail} {rate:.2f}/s remaining={jobs.unfinished_tasks}", flush=True)
                last_report = time.time()
        done_evt.set()

    elapsed = time.time() - t0
    print(f"[done] ok={n_ok} fail={n_fail} elapsed={elapsed/60:.1f}min")


if __name__ == "__main__":
    main()
