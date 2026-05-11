#!/usr/bin/env python3
"""Expanded transliteration training set — 1500-3000 pairs for proper
policy-fraction grid (currently capped at 300 ≈ 1.84% effective max).

Strategy: 100 hand-curated pairs (existing in 07_*) × 5 paraphrase variants ×
4 source-lang annotations + 100 NEW pairs in each direction.

Total target: ~2400 pairs → effective policy share up to 12% on a 16K base.
"""
from __future__ import annotations
import json, pathlib

PROJ = pathlib.Path("/scratch/hpc198a01/젬마4해커톤")
OUT = PROJ / "prototype/data/raw/transliteration_v2.jsonl"

# extend the 07_*.py KO_TO_CYR set (already 30 pairs) to 100 pairs
KO_TO_CYR_EXTENDED = [
    # original 30 from 07_*
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
    # +70 new
    ("이거", "Иго"), ("저거", "Чого"), ("뭐예요", "Мвоеё"),
    ("어디", "Оди"), ("언제", "Ондже"), ("누구", "Нугу"),
    ("왜", "Вэ"), ("어떻게", "Оттокхе"),
    ("크다", "Кыда"), ("작다", "Чакта"), ("높다", "Нопта"),
    ("낮다", "Натта"), ("덥다", "Топта"), ("춥다", "Чхупта"),
    ("빠르다", "Ппарыда"), ("느리다", "Ныри다"),
    ("머리", "Мори"), ("얼굴", "Олгуль"), ("눈", "Нун"),
    ("코", "Кхо"), ("입", "Ип"), ("귀", "Кви"),
    ("손", "Сон"), ("발", "Паль"), ("배", "Пэ"),
    ("등", "Тын"), ("팔", "Пхаль"), ("다리", "Тари"),
    ("학생", "Хаксэн"), ("선생님", "Сонсэнним"),
    ("친구", "Чхингу"), ("가족", "Качжок"),
    ("형", "Хён"), ("누나", "Нуна"), ("동생", "Тонсэн"),
    ("도시", "Тоси"), ("나라", "Нара"), ("바다", "Пада"),
    ("산", "Сан"), ("강", "Кан"), ("호수", "Хосу"),
    ("나무", "Наму"), ("꽃", "Кот"), ("잎", "Ип"),
    ("열매", "Ёльмэ"), ("씨앗", "Ссиат"),
    ("아침", "Ачхим"), ("점심", "Чомсим"), ("저녁", "Чонёк"),
    ("아침밥", "Ачхимпап"), ("저녁밥", "Чонёкпап"),
    ("일", "Иль"), ("이", "И"), ("삼", "Сам"),
    ("사", "Са"), ("오", "О"), ("육", "Юк"),
    ("칠", "Чхиль"), ("팔", "Пхаль"), ("구", "Ку"),
    ("십", "Сип"), ("백", "Пэк"), ("천", "Чхон"),
    ("월요일", "Воррёиль"), ("화요일", "Хваёиль"),
    ("수요일", "Суёиль"), ("목요일", "Могёиль"),
    ("금요일", "Кымёиль"), ("토요일", "Тхоёиль"),
    ("일요일", "Иррёиль"),
    ("봄", "Пом"), ("여름", "Ёрым"), ("가을", "Каыль"),
    ("겨울", "Кёуль"),
    ("어제", "Одже"), ("오늘", "Оныль"), ("내일", "Нэиль"),
    ("주말", "Чумаль"),
    ("아이", "Аи"), ("어른", "Орын"),
]

RU_TO_HAN_EXTENDED = [
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
    # +70 new
    ("где", "그제"), ("когда", "카그다"), ("почему", "파체무"),
    ("кто", "크토"), ("что", "쉬토"), ("как", "카크"),
    ("я", "야"), ("ты", "트이"), ("он", "온"), ("она", "아나"),
    ("мы", "므이"), ("вы", "브이"), ("они", "아니"),
    ("человек", "첼라볘크"), ("друг", "드루크"), ("семья", "셰미야"),
    ("брат", "브라트"), ("сестра", "셰스트라"), ("сын", "스인"),
    ("дочь", "도치"), ("ребёнок", "리뵤노크"),
    ("страна", "스트라나"), ("город", "고라트"),
    ("море", "모례"), ("гора", "가라"), ("река", "리카"),
    ("озеро", "오졔라"), ("дерево", "졔례바"), ("цветок", "쯔비톡"),
    ("лист", "리스트"), ("солнце", "쏜쩨"), ("луна", "루나"),
    ("звезда", "즈비즈다"), ("небо", "녜바"), ("земля", "지믈랴"),
    ("утро", "우트라"), ("день", "졘"), ("вечер", "볘체르"),
    ("ночь", "노치"), ("один", "아진"), ("два", "드바"),
    ("три", "트리"), ("четыре", "체트이례"), ("пять", "퍄찌"),
    ("шесть", "솉씨"), ("семь", "솜"), ("восемь", "보셈"),
    ("девять", "졔뱌찌"), ("десять", "졔샤찌"),
    ("сто", "스토"), ("тысяча", "트이샤차"),
    ("понедельник", "파니졜닉"), ("вторник", "프토르닉"),
    ("среда", "스리다"), ("четверг", "체트볘르크"),
    ("пятница", "퍄트니짜"), ("суббота", "수보타"),
    ("воскресенье", "바스크리쎼니예"),
    ("весна", "비스나"), ("лето", "례타"), ("осень", "오셰니"),
    ("зима", "지마"),
    ("вчера", "프체라"), ("сегодня", "셰보드냐"), ("завтра", "자프트라"),
    ("выходной", "브이하드노이"),
    ("горячий", "가랴치"), ("холодный", "할로드느이"),
    ("большой", "발쇼이"), ("маленький", "말렌키"),
]

KO_TO_LAT_EXTENDED = [
    ("안녕하세요", "annyeonghaseyo"), ("감사합니다", "gamsahamnida"),
    ("사랑해요", "saranghaeyo"), ("괜찮아요", "gwaenchanayo"),
    ("우리 아기", "uri agi"), ("아빠", "appa"), ("엄마", "eomma"),
    ("학교", "hakgyo"), ("집", "jip"), ("밥", "bap"),
    ("물", "mul"), ("우유", "uyu"), ("사과", "sagwa"),
    ("강아지", "gangaji"), ("고양이", "goyangi"), ("토끼", "tokki"),
    ("주방에서 밥 먹어요", "jubangeseo bap meogeoyo"),
    ("좋은 아침이에요", "joeun achimieyo"),
    ("잘자요", "jaljayo"), ("내일 봐요", "naeil bwayo"),
    # +50 new
    ("이거 뭐예요", "igeo mwoyeyo"), ("어디 가요", "eodi gayo"),
    ("얼마예요", "eolmayeyo"), ("좋아해요", "joahaeyo"),
    ("싫어해요", "sireohaeyo"), ("괜찮아요", "gwaenchanayo"),
    ("미안해요", "mianhaeyo"), ("도와주세요", "dowajuseyo"),
    ("천천히", "cheoncheonhi"), ("빨리", "ppalli"),
    ("학생", "haksaeng"), ("선생님", "seonsaengnim"),
    ("친구", "chingu"), ("가족", "gajok"),
    ("아침", "achim"), ("점심", "jeomsim"), ("저녁", "jeonyeok"),
    ("일주일", "iljuil"), ("주말", "jumal"), ("휴일", "hyuil"),
    ("봄", "bom"), ("여름", "yeoreum"), ("가을", "gaeul"), ("겨울", "gyeoul"),
    ("머리", "meori"), ("얼굴", "eolgul"), ("손", "son"), ("발", "bal"),
    ("크다", "keuda"), ("작다", "jakda"), ("높다", "nopda"), ("낮다", "natda"),
    ("멀다", "meolda"), ("가깝다", "gakkapda"),
    ("덥다", "deopda"), ("춥다", "chupda"),
    ("배고파요", "baegopayo"), ("졸려요", "jolryeoyo"),
    ("기뻐요", "gippeoyo"), ("슬퍼요", "seulpeoyo"),
    ("재미있어요", "jaemiisseoyo"), ("재미없어요", "jaemieopseoyo"),
    ("월요일", "woryoil"), ("화요일", "hwayoil"), ("수요일", "suyoil"),
    ("목요일", "mogyoil"), ("금요일", "geumyoil"),
    ("토요일", "toyoil"), ("일요일", "iryoil"),
    ("화장실", "hwajangsil"), ("입구", "ipgu"), ("출구", "chulgu"),
]

RU_TO_LAT_EXTENDED = [
    ("спасибо", "spasibo"), ("пожалуйста", "pozhaluysta"),
    ("привет", "privet"), ("я люблю тебя", "ya lyublyu tebya"),
    ("мама", "mama"), ("папа", "papa"), ("малыш", "malysh"),
    ("молоко", "moloko"), ("вода", "voda"), ("хлеб", "khleb"),
    ("собака", "sobaka"), ("кошка", "koshka"), ("дом", "dom"),
    ("школа", "shkola"), ("книга", "kniga"), ("спать", "spat'"),
    ("сладкий", "sladkiy"), ("спокойной ночи", "spokoynoy nochi"),
    ("сегодня", "segodnya"), ("завтра", "zavtra"),
    # +50 new
    ("где ты", "gde ty"), ("как дела", "kak dela"),
    ("сколько стоит", "skol'ko stoit"), ("я хочу", "ya khochu"),
    ("я не знаю", "ya ne znayu"), ("извините", "izvinite"),
    ("помогите", "pomogite"), ("медленно", "medlenno"),
    ("быстро", "bystro"), ("ребёнок", "rebyonok"),
    ("учитель", "uchitel'"), ("друг", "drug"),
    ("семья", "sem'ya"), ("утро", "utro"), ("вечер", "vecher"),
    ("неделя", "nedelya"), ("выходной", "vykhodnoy"),
    ("месяц", "mesyats"), ("год", "god"),
    ("весна", "vesna"), ("лето", "leto"), ("осень", "osen'"), ("зима", "zima"),
    ("голова", "golova"), ("лицо", "litso"), ("рука", "ruka"), ("нога", "noga"),
    ("большой", "bol'shoy"), ("маленький", "malen'kiy"),
    ("высокий", "vysokiy"), ("низкий", "nizkiy"),
    ("далеко", "daleko"), ("близко", "blizko"),
    ("горячий", "goryachiy"), ("холодный", "kholodnyy"),
    ("я голоден", "ya goloden"), ("я устал", "ya ustal"),
    ("я рад", "ya rad"), ("мне грустно", "mne grustno"),
    ("интересно", "interesno"), ("скучно", "skuchno"),
    ("понедельник", "ponedel'nik"), ("вторник", "vtornik"),
    ("среда", "sreda"), ("четверг", "chetverg"),
    ("пятница", "pyatnitsa"), ("суббота", "subbota"),
    ("воскресенье", "voskresen'ye"),
    ("туалет", "tualet"), ("вход", "vkhod"), ("выход", "vykhod"),
]

INSTRUCTION_TEMPLATES = [
    "Output ONLY a {tgt_label} phonetic transliteration of the {src_lang} text. No commentary.\n\n{src}",
    "Convert to a {tgt_label} phonetic transliteration of the {src_lang} text. No commentary.\n\n{src}",
    "Write the following {src_lang} text in {tgt_label} phonetic transliteration only.\n\n{src}",
    "Phonetically transliterate this {src_lang} text into {tgt_label}. Output the transliteration only.\n\n{src}",
    "Render this {src_lang} text using {tgt_label} characters approximating the {src_lang} pronunciation.\n\n{src}",
]

DIRECTIONS = [
    ("Korean", "Cyrillic", KO_TO_CYR_EXTENDED),
    ("Russian", "Hangul", RU_TO_HAN_EXTENDED),
    ("Korean", "Latin (Revised Romanization)", KO_TO_LAT_EXTENDED),
    ("Russian", "Latin (BGN/PCGN)", RU_TO_LAT_EXTENDED),
]


def make_chat(src_lang, tgt_label, src, tgt, template):
    sys = (
        "You are a phonetic transliterator for a multicultural Korean-Russian-English household. "
        "When asked to transliterate, output ONLY the requested script. Do NOT translate. "
        "Preserve the source's pronunciation in the target script."
    )
    user = template.format(src_lang=src_lang, tgt_label=tgt_label, src=src)
    return {"messages": [
        {"role": "system", "content": sys},
        {"role": "user", "content": user},
        {"role": "assistant", "content": tgt},
    ]}


def main():
    rows = []
    for src_lang, tgt_label, pairs in DIRECTIONS:
        for src, tgt in pairs:
            for tmpl in INSTRUCTION_TEMPLATES:
                rows.append(make_chat(src_lang, tgt_label, src, tgt, tmpl))
    with OUT.open("w", encoding="utf-8") as fo:
        for r in rows:
            fo.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[transliteration v2] {len(rows)} -> {OUT.name}")
    print(f"  per-direction (5 templates each):")
    for src_lang, tgt_label, pairs in DIRECTIONS:
        print(f"    {src_lang} → {tgt_label}: {len(pairs)} pairs × 5 = {len(pairs)*5}")


if __name__ == "__main__":
    main()
