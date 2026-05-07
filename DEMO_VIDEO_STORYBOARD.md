# Demo Video Storyboard — Kaggle Gemma 4 Good Hackathon

**Length**: 5:00 (hard cap; aim for 4:45 for safety margin)
**Aspect ratio**: 16:9 horizontal, 1080p minimum
**Audio**: family voices + ambient, optional light music ≤ −20 dBFS
**Subtitles**: trilingual (KO/RU/EN) burned-in or sidecar SRT

---

## Shot list

| # | T | Duration | Shot | Sound | On-screen text |
|---|---|---|---|---|---|
| 1 | 0:00 | 0:08 | Wide shot of family at breakfast table — father, mother, baby in high chair. Three languages overlap naturally. | Ambient family sounds, no music | "한 가정. 세 언어. // Одна семья. Три языка. // One home. Three languages." |
| 2 | 0:08 | 0:12 | Close-up: mother stirring tea, asking baby in Russian *"Хочешь яблоко?"*. Father offers spoon: *"사과 먹어볼래?"*. Baby looks at fruit. | Live audio | (subtitles only) |
| 3 | 0:20 | 0:10 | Quick cut: Duolingo / Papago / Babbel logos appear briefly with red ✗ overlays. Caption: "Built for one learner, one direction, one script." | Single percussive hit | "1 learner ✗  1 direction ✗  1 script ✗" |
| 4 | 0:30 | 0:20 | Phone in mother's hand. App opens. Camera mode. Mother points camera at apple on the table. Phone shows trilingual card: 사과 / яблоко / apple, plus Cyrillic transliteration "сагуа" — and audio plays in three languages. | UI feedback sounds + 3-language TTS | "Camera → Gemma 4 E2B on-device → trilingual card" |
| 5 | 0:50 | 0:15 | Mother taps "Bridge: Russian" → explanation switches to Russian. She taps "Bridge: English" → switches to English (her common language with husband). | UI tap sound | "L1-aware bridge: RU or EN" |
| 6 | 1:05 | 0:15 | Father picks up the phone, points at кошка (toy cat). Phone shows кошка / 고양이 / cat — Hangul transliteration "코쉬카" so he can pronounce in Russian. | UI + 3-language TTS | "Father learns Russian. Same screen, same session." |
| 7 | 1:20 | 0:25 | Voice path. Mother speaks: *"Сладкий, давай поедим"*. Phone responds in three languages with breakfast vocab + L1-aware coaching note. Baby looks at phone, repeats "맘마". Phone responds with developmental encouragement and a daily-mission card. | Live + UI | "Audio in (native E2B) → trilingual response" |
| 8 | 1:45 | 0:20 | Father uses `recommend_next_word`. Phone shows three new animal words age-appropriate for 21-month-old. He picks "곰 / медведь / bear" and the family follows together. | UI | "Function calling: next_word, score_pronunciation, l1_explain" |
| 9 | 2:05 | 0:15 | Cut to settings: "Premium mode (network)" toggle. Phone connects to moon1 via cloudflared. | Network connect sound | "Premium tier: moon1 server, opt-in" |
| 10 | 2:20 | 0:30 | Avatar appears — RU-L1 Korean teacher persona. SoulX-FlashHead lip-sync. Mother converses live in Korean with the teacher. The teacher's pronunciation has a deliberate Russian accent so the mother feels at ease. | Live, with teacher's voice | "RU-L1 Korean teacher persona — live talking head" |
| 11 | 2:50 | 0:25 | Mother asks the teacher to switch to English bridge. Teacher continues in English with the same persona. | Live | "Bridge language switch: voice + face stay consistent" |
| 12 | 3:15 | 0:20 | Quick cut: 76M MTP drafter explained visually. Speedometer 800 ms → 270 ms. | UI + zip sound | "76M MTP drafter: 3× faster real-time" |
| 13 | 3:35 | 0:15 | Cut to dataset diagram — 247 KO-RU pairs → 12,408 trilingual triples via English pivot. | Diagram animation | "Bridge-pivot: 247 → 12,408 (50×)" |
| 14 | 3:50 | 0:20 | Auto-judge result: bar chart showing LoRA-v1 fixed empty responses (5→0) and family-context realism, but **regressed** on transliteration (100% → 25%). Honest framing: "We caught it, fixed in v2." | Chart animation | "Family-as-Evaluator caught what BLEU couldn't" |
| 15 | 4:10 | 0:20 | LoRA-v2 result: transliteration restored to ≥95%, family-context wins kept. | Chart animation | "v2: 300 transliteration pairs → restored" |
| 16 | 4:30 | 0:15 | Map of Korea + multicultural-family statistics overlay. Sejong Family Center logo. | Soft music | "From one family → 20 families (2026 Q4) → public infrastructure" |
| 17 | 4:45 | 0:15 | Closing card. Apache 2.0, GitHub link, paper link. Family wave. | Music fade | "Apache 2.0 · Free · Offline · Family-evaluated" |

**Total**: 5:00

---

## Production notes

### Filming
- 4K source ≥ 60 Mbps if possible; export 1080p H.264 ≤ 100 MB for upload
- Smartphone camera footage: shoot vertically *and* horizontally; crop horizontal in edit
- Family scenes: candid > scripted. The 21-month-old will not perform on cue. Use 5+ takes and pick the most natural snippet.
- Avatar tier (shots 10–11): record both phone screen and a separate moon1 monitor to make the live nature of the connection visible. Show network indicator.

### Editing
- Cuts ≤ 4 s on average for the first half (mobile-demo half); longer cuts (8–12 s) for the avatar and analysis half. Keeps engagement up while still letting "show, not tell" land.
- Subtitles essential — three languages on screen is unreadable without them.
- License-safe music: Epidemic Sound, Artlist, or no music at all. Do not use copyrighted audio.

### Privacy
- Baby's face: blur or use back-of-head shots only. Never frontal close-up. Parental consent on record.
- Wife's face: own consent on record (she is co-author).
- Avatar persona: clearly fictional; no real public-figure likeness.

### Trim policy
- If 5:00 is exceeded, trim shots 8 (function calling demo) and 11 (English bridge switch) first; they are technical detail repeating points already made.
- Keep shots 1, 4, 10, 14 as they are — those carry the narrative weight.

---

## Storyboard frames (for designer)

To be created in `assets/storyboard_frames/` as 6-up paged PDF, one
key frame per shot.
