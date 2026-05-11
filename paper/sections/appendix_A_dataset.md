# Appendix A: Dataset Construction Details

## A.1 Tatoeba pulls (CC-BY)

Pulled 2026-05-06 from `https://downloads.tatoeba.org/exports/`:

```
tatoeba_sentences.csv     747,730,691 bytes (~750 MB)
tatoeba_links.csv         448,697,642 bytes (~450 MB)
```

After filtering to {KO, RU, EN} and deduplicating at the (src_id, tgt_id)
level:

| Pair | Sentences |
|---|---|
| KO ↔ RU (direct) | 247 |
| KO ↔ EN (direct) | 11,385 |
| RU ↔ EN (direct) | 810,219 |

## A.2 English-pivot trilingual triples

Algorithm (`prototype/data/02_build_trilingual_triples.py`):

1. Index KO sentences by their English-translation key.
2. Index RU sentences by their English-translation key.
3. For each English key present in both indices, take up to 3 KO
   translations × 3 RU translations and emit the (KO, RU, EN) triple.

Result: **12,408** triples. At training time each triple is unfolded
into 6 directional pairs (KO→RU, RU→KO, KO→EN, EN→KO, RU→EN, EN→RU),
producing 74,448 translation training steps from this layer alone.

## A.3 Synthetic learning artifacts

**Object cards** (`03_synth_object_cards.py` →
`04_run_synth_via_ollama.py`):

* 144 Korean object names spanning 9 categories (집, 음식, 동물, 신체,
  자연, 교통, 감정, 행동, plus an open category)
* expanded by (age band: 0-2 / 2-4 / 4-6 / 6-8) × (bridge: ru / en) =
  **1,296 unique prompt configurations**
* Distilled with **Gemma 4 E4B** under `format=json` and `think: False`,
  parallelized across 4 Ollama instances on 4 A100 GPUs (one model per
  GPU, port 11434–11437, round-robin from a pool of 8 client threads)
* Output: 1,294 cards parsed and schema-validated, 2 failed
* End-to-end throughput: **0.87 cards/s** (vs. 0.04 cards/s on a single
  Ollama instance with thinking enabled — a 22× speedup, dominated by
  `think: False`)

JSON schema for an object card (excerpt):

```json
{
  "word": {"ko": "...", "ru": "...", "en": "..."},
  "phonetic": {
    "ko_in_cyrillic_for_ru": "...",
    "ru_in_hangul_for_ko": "...",
    "ko_in_latin_for_en": "...",
    "ru_in_latin_for_en": "..."
  },
  "wife_card":   {"target": "ko", "explanation_in": "ru|en", "text": "..."},
  "husband_card":{"target": "ru", "explanation_in": "ko",    "text": "..."},
  "child_card": {
    "ko_simple": "...", "ru_simple": "...", "en_simple": "...",
    "audio_focus": ["...", "...", "..."]
  },
  "l1_contrast": {
    "ko_vs_ru": "...", "ko_vs_en": "...", "ru_vs_en": "..."
  },
  "function_call_hints": {
    "next_word": ["...", "...", "..."],
    "common_mistake": "...",
    "praise_phrase": {"ko": "...", "ru": "...", "en": "..."}
  }
}
```

**Family scenarios** (`05_synth_family_scenarios.py`):

* 50 daily-life situations × 4 age bands × 3 maternal-Korean levels
  × 2 bridge languages = 1,200 baseline configurations, capped at
  **1,176 unique prompts** after deduplication
* Distilled with the same Ollama pipeline → **1,006 dialogs** parsed and
  schema-validated, 170 schema-failed

**Function-call seeds** (`06_synth_function_calls.py`):

* 6 hand-curated tool invocations (`score_pronunciation`,
  `recommend_next_word`, `explain_in_l1`, `switch_age_mode`,
  `flag_unsafe_input`, `daily_mission`)
* Each seed expanded with 80 paraphrase variants (later replaced with
  Gemma 4 26B paraphrase generation in v3) → **498 examples**

**Transliteration pairs** (added in v2,
`07_synth_transliteration.py`):

* 100 hand-curated pairs spanning KO→Cyrillic (29), RU→Hangul (29),
  KO→Latin (20), RU→Latin (22)
* Each pair × 3 instructional paraphrases = **300 examples**

## A.4 Final training merge

`prototype/data/10_merge_train_jsonl.py` merges the layers and converts
to `messages`-format chat JSONL. Final v2 statistics:

| Source | Examples |
|---|---|
| Tatoeba KO↔RU 6-direction | 494 |
| Tatoeba KO↔EN 6-direction | 3,000 |
| Tatoeba RU↔EN 6-direction | 3,000 |
| English-pivot triples × 6 directions | 12,000 |
| Object cards (chat-formatted) | 1,294 |
| Family scenarios (chat-formatted) | 1,006 |
| Function-call examples | 498 |
| Transliteration pairs (v2 only) | 300 |
| **Total train_v2** | **20,513** |
| eval_v2 (95/5 split) | 1,079 |

JSONL example row:

```json
{"messages": [
  {"role": "system", "content": "Translate KO to RU."},
  {"role": "user", "content": "사과 한 개 먹을래?"},
  {"role": "assistant", "content": "Хочешь съесть яблоко?"}
]}
```
