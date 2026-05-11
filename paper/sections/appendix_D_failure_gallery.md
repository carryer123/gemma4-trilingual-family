# Appendix D: Failure Case Gallery (LoRA-v1 vs. Stock E2B)

This appendix shows the *raw* prompt-response pairs underlying the
quantitative results in §5.2 and the failure-mode catalog in §4.1. The
goal is to make every reader an evaluator.

## D.1 Transliteration regressions (the headline finding)

### D.1.1 KO → Cyrillic
**Prompt**: *Output ONLY a Cyrillic phonetic transliteration of the Korean
phrase '안녕하세요, 우리 아기.' that a Russian speaker can pronounce. No
commentary.*

| Variant | Output | Verdict |
|---|---|---|
| Stock E2B | `Аннёнхасеё, ури аги.` | ✓ correct script + plausible RU phonetic mapping |
| LoRA-v1 | `안녕하세요, 우리 아기.` | ✗ source-language echo — Hangul, not Cyrillic |

### D.1.2 RU → Hangul
**Prompt**: *Output ONLY a Hangul phonetic transliteration of the Russian
phrase 'спасибо, мой малыш.' that a Korean speaker can pronounce. No
commentary.*

| Variant | Output | Verdict |
|---|---|---|
| Stock E2B | `스파시바 모이 말리쉬` | ✓ Hangul transliteration |
| LoRA-v1 | `고마워, 내 아기.` | ✗ Hangul, but **translation** ("thank you, my baby"), not transliteration |

### D.1.3 KO → Latin
**Prompt**: *Output ONLY the Revised Romanization of '주방에서 밥 먹어요'.
No commentary.*

| Variant | Output | Verdict |
|---|---|---|
| Stock E2B | `jubangeseo bap meogeoyo` | ✓ |
| LoRA-v1 | `주방에서 밥 먹어요.` | ✗ source-language echo |

### D.1.4 RU → Latin
**Prompt**: *Output ONLY the BGN/PCGN transliteration of 'спасибо, мой
малыш.' No commentary.*

| Variant | Output | Verdict |
|---|---|---|
| Stock E2B | `spasibo, moy malysh` | ✓ |
| LoRA-v1 | `Благодаря, малыш.` | ✗ wrong word + Cyrillic, not Latin |

## D.2 Schema-label hallucinations

### D.2.1 `func_recommend_next` — invented "animal"
**Prompt**: *Recommend 3 next animal words to learn for an 18-month-old who
already knows: 강아지, 고양이, 토끼.*

LoRA-v1 returned, in valid JSON, this `next` array:

```json
{"next":[
  {"ko":"곰","ru":"медведь","en":"bear"},
  {"ko":"아무개","ru":"кошка","en":"cat"},
  {"ko":"물고기","ru":"рыба","en":"fish"}
]}
```

Three failures in this single response:

1. **"아무개"** is a Korean indefinite pronoun (≈ "someone, anyone"), not
   an animal. The model invented an animal-shaped slot filler.
2. The cat slot is **already in the learned-set** the user provided
   (강아지, 고양이, 토끼). The model failed to honor `learned_set`.
3. The Russian translation of the (invented) "아무개" is given as
   "кошка" (cat) — the model's own contradiction goes unflagged in JSON
   parsing, and would crash a downstream UI that displays the Korean
   word and its Russian audio side-by-side.

Stock E2B for the same prompt returned `["물고기","기린","코끼리"]` —
all real, age-appropriate, and not in the learned set.

### D.2.2 `wife_card.explanation_in` — label vs. text confusion (in distillation, not eval)

In distilled object cards (Appendix A) we observed a separate failure
where the JSON field `wife_card.explanation_in` is *defined as an enum
with values `"ru"` or `"en"`*, but the model emits a sentence such as
`"The Korean word for pot/pan. It is a common household item."` The
JSON parser passes; downstream code that switches on
`explanation_in == "ru"` silently fails. This was caught in the v1
data-validation phase and the v2 distillation prompt was tightened to
re-quote the enum constraint.

## D.3 Persona-bridge collapse

### D.3.1 KO grammar explanation requested *in Russian*
**Prompt** (paraphrased): *Объясни на русском (3–4 предложения):
различие между корейскими частицами '에' и '에서'.*

| Variant | Output | Verdict |
|---|---|---|
| Stock E2B | A clean 3-sentence Russian explanation contrasting направление (에) vs. место действия (에에서) with examples. | ✓ usable for an RU L1 learner |
| LoRA-v1 | A confused Russian paragraph that says "에" and "에에서" *both* mark "where the action takes place," contradicting itself in the next sentence. Grammar regression. | ✗ |

This is **not** a translation failure (the Russian is fluent) and
**not** a schema failure (no JSON involved). It is a *content
regression* on a grammar-explanation policy. Only an evaluator who
knows both Russian and Korean grammar can detect it. BLEU and
perplexity see it as fine.

## D.4 Improvements (LoRA-v1 > Stock)

For balance, the same comparison shows where LoRA-v1 is better:

### D.4.1 Family-context realism (`scenario_breakfast`)

Stock E2B's breakfast dialog includes a didactic line: *"Can you say
'Annyeonghaseyo'?"* — the kind of language-drill phrasing that does not
appear in real multicultural family breakfasts. LoRA-v1's dialog has
the father announce *"아침 먹자. 밥은 짓는 중이야."* and the child say
*"맘마 좀."* — the latter is exactly what our 21-month-old says, in the
correct toddler register. This is a positive signal that the LoRA
absorbed the family-scenario distillation.

### D.4.2 L1-aware refusals (`safety_refuse_inappropriate`)

When the user (in English) asks the model to recommend Russian curse
words for a child, stock E2B refuses in English: *"I cannot fulfill
this request."* LoRA-v1 refuses *in Russian*: *"Я не могу рекомендовать
вам конкретные ругательства."* Because the user's request was *about
Russian*, the L1-aware refusal is more usable to the actual RU L1
mother.

### D.4.3 Empty-response rate

Stock baseline measured in §5.1 had 4–5 empty responses across the
20-probe seed (e.g., `phonetic_ru_to_han`, `code_switch`,
`contrast_ru_ko`, `contrast_ko_ru`). LoRA-v1 had **zero empty
responses** across all 30 probes. This is the single most concrete
quality improvement.

## D.5 What we are not claiming

The improvements in D.4 do *not* offset the regressions in D.1–D.3 in
the absence of a weighted human rubric. The LoRA-v2 (Section 7,
Appendix B) is designed to keep the wins of D.4 while restoring the
correctness of D.1–D.3.
