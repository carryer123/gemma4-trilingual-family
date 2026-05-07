#!/usr/bin/env python3
"""Generate explicit transliteration training pairs to fix LoRA-v1's
script-direction regression on phonetic probes.

Output: prototype/data/raw/transliteration.jsonl
"""
import json, pathlib

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
OUT = PROJ / "prototype/data/raw/transliteration.jsonl"
OUT.parent.mkdir(parents=True, exist_ok=True)

# Curated KO → Cyrillic transliterations (Russian-pronounceable)
KO_TO_CYR = [
    ("안녕하세요", "Аннёнхасеё"), ("감사합니다", "Камсахамнида"),
    ("사랑해요", "Саранхэё"), ("괜찮아요", "Квенчанаё"),
    ("미안해요", "Мианэё"), ("안녕히 가세요", "Аннёнхи касеё"),
    ("좋아해요", "Чоахэё"), ("싫어해요", "Сирохэё"),
    ("배고파요", "Пэгопаё"), ("물 주세요", "Муль чусеё"),
    ("우리 아기", "Ури аги"), ("아빠", "Аппа"), ("엄마", "Омма"),
    ("할아버지", "Харабоджи"), ("할머니", "Хальмони"),
    ("학교", "Хаккё"), ("집", "Чип"), ("밥", "Пап"),
    ("물", "Муль"), ("우유", "Ую"), ("빵", "Ппан"),
    ("사과", "Сагва"), ("바나나", "Банана"), ("강아지", "Канаджи"),
    ("고양이", "Коянъи"), ("토끼", "Токки"), ("자다", "Чада"),
    ("먹다", "Мокта"), ("가다", "Када"), ("오다", "Ода"),
]

# Curated RU → Hangul transliterations (Korean-pronounceable)
RU_TO_HAN = [
    ("спасибо", "스파시바"), ("пожалуйста", "파잘루이스타"),
    ("привет", "프리뱨트"), ("здравствуйте", "즈드라스트부이쩨"),
    ("до свидания", "다 스비다니야"), ("извините", "이즈비니쩨"),
    ("я люблю тебя", "야 류블류 찌뱌"), ("мама", "마마"),
    ("папа", "파파"), ("бабушка", "바부쉬카"), ("дедушка", "졔두쉬카"),
    ("малыш", "말르이쉬"), ("молоко", "말라코"), ("вода", "바다"),
    ("хлеб", "흘롑"), ("яблоко", "야블라카"), ("банан", "바난"),
    ("собака", "사바카"), ("кошка", "코쉬카"), ("кролик", "크롤리크"),
    ("дом", "돔"), ("школа", "쉬콜라"), ("книга", "크니가"),
    ("спать", "스파찌"), ("есть", "예스찌"), ("идти", "이찌"),
    ("сладкий", "슬라드키"), ("сегодня", "셰보드냐"),
    ("завтра", "자프트라"), ("спокойной ночи", "스파코이나이 노치"),
]

# KO → Latin (Revised Romanization)
KO_TO_LAT = [
    ("안녕하세요", "annyeonghaseyo"), ("감사합니다", "gamsahamnida"),
    ("사랑해요", "saranghaeyo"), ("괜찮아요", "gwaenchanayo"),
    ("우리 아기", "uri agi"), ("아빠", "appa"), ("엄마", "eomma"),
    ("학교", "hakgyo"), ("집", "jip"), ("밥", "bap"),
    ("물", "mul"), ("우유", "uyu"), ("사과", "sagwa"),
    ("강아지", "gangaji"), ("고양이", "goyangi"), ("토끼", "tokki"),
    ("주방에서 밥 먹어요", "jubangeseo bap meogeoyo"),
    ("좋은 아침이에요", "joeun achimieyo"),
    ("잘자요", "jaljayo"), ("내일 봐요", "naeil bwayo"),
]

# RU → Latin (BGN/PCGN)
RU_TO_LAT = [
    ("спасибо", "spasibo"), ("пожалуйста", "pozhaluysta"),
    ("привет", "privet"), ("я люблю тебя", "ya lyublyu tebya"),
    ("мама", "mama"), ("папа", "papa"), ("малыш", "malysh"),
    ("молоко", "moloko"), ("вода", "voda"), ("хлеб", "khleb"),
    ("собака", "sobaka"), ("кошка", "koshka"), ("дом", "dom"),
    ("школа", "shkola"), ("книга", "kniga"), ("спать", "spat'"),
    ("сладкий", "sladkiy"), ("спокойной ночи", "spokoynoy nochi"),
    ("сегодня", "segodnya"), ("завтра", "zavtra"),
]


def make_chat(src_lang, src_script_label, tgt_script_label, src, tgt):
    """One transliteration training example."""
    sys = (
        "You are a phonetic transliterator for a multicultural Korean-Russian-English household. "
        "When asked to transliterate, output ONLY the requested script. Do NOT translate. "
        "Preserve the source's pronunciation in the target script."
    )
    user = (
        f"Output ONLY a {tgt_script_label} phonetic transliteration of "
        f"the {src_lang} text. No commentary.\n\n{src}"
    )
    return {
        "messages": [
            {"role": "system", "content": sys},
            {"role": "user", "content": user},
            {"role": "assistant", "content": tgt},
        ]
    }


def main():
    rows = []
    for src, tgt in KO_TO_CYR:
        rows.append(make_chat("Korean", "Hangul", "Cyrillic", src, tgt))
    for src, tgt in RU_TO_HAN:
        rows.append(make_chat("Russian", "Cyrillic", "Hangul", src, tgt))
    for src, tgt in KO_TO_LAT:
        rows.append(make_chat("Korean", "Hangul", "Latin (Revised Romanization)", src, tgt))
    for src, tgt in RU_TO_LAT:
        rows.append(make_chat("Russian", "Cyrillic", "Latin (BGN/PCGN)", src, tgt))

    # Each example × 3 instructional paraphrases for robustness
    expanded = list(rows)
    for r in rows:
        u_orig = r["messages"][1]["content"]
        # paraphrase 1
        u_alt1 = u_orig.replace("Output ONLY", "Convert to")
        # paraphrase 2
        u_alt2 = u_orig.replace("Output ONLY", "Write in")
        for u_new in [u_alt1, u_alt2]:
            new = json.loads(json.dumps(r))
            new["messages"][1]["content"] = u_new
            expanded.append(new)

    with OUT.open("w", encoding="utf-8") as fo:
        for r in expanded:
            fo.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[transliteration] {len(expanded)} -> {OUT.name}")


if __name__ == "__main__":
    main()
