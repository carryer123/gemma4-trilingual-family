package com.moontech.trilingual.llm

import com.moontech.trilingual.data.FamilySetup
import com.moontech.trilingual.data.FamilyWord
import com.moontech.trilingual.data.Lang

/** Mirrors prototype/PROMPT_LIBRARY.md. Both Kotlin + Swift must stay
 *  byte-aligned. The 4L LoRA was trained on this prompt-style with
 *  `mode` / `active_languages` / `card` / `next_action` / `safety`. */
object PromptLibrary {

    private fun renderVocab(words: List<FamilyWord>, active: List<String>): String =
        if (words.isEmpty()) "(none yet)"
        else words.joinToString("\n") { it.toPromptLine(active) }

    private fun activeListLiteral(active: List<String>): String =
        active.joinToString(", ") { "\"$it\"" }

    private fun activeNamesLiteral(active: List<String>): String =
        active.joinToString(", ") { Lang.label(it) }

    /** Core: object → multilingual family card (4L LoRA trained schema). */
    fun objectCard(objectName: String, family: FamilySetup, vocab: List<FamilyWord>): String {
        val active = family.householdLanguages
        return """
            Return JSON only. No prose, no markdown fence. Schema:
            {
              "mode": "${family.mode}",
              "age_band": "${family.ageBand}",
              "active_languages": [${activeListLiteral(active)}],
              "card": { /* per-language object names + parent prompt + child action */ },
              "next_action": "<one short next step for the parent in ${family.bridge}>",
              "safety": {"child_safe": true, "no_private_data": true}
            }

            The household speaks: ${activeNamesLiteral(active)}.
            Object: $objectName
            Family vocabulary (use when natural):
            ${renderVocab(vocab, active)}
        """.trimIndent()
    }

    /** F1 bedtime story — one short paragraph per active language. */
    fun bedtimeStory(keyword: String, family: FamilySetup, vocab: List<FamilyWord>): String {
        val active = family.householdLanguages
        return """
            Return JSON only. Schema:
            {
              "theme": "<one-word theme>",
              "paragraphs_by_lang": {
                ${active.joinToString(",\n                ") { "\"$it\": [\"<para 1>\", \"<para 2>\", \"<para 3>\"]" }}
              },
              "age_band": "${family.ageBand}",
              "child_name": "${family.childName}",
              "safety": {"child_safe": true, "no_private_data": true}
            }

            Constraints:
            - Each paragraph ≤ 3 sentences. Total reading time ≤ 60 s per language.
            - Paragraphs across languages mirror the same scene order.
            - Use the child's name "${family.childName}" naturally in 1–2 paragraphs.
            - Child-safe content only. No violence, no fear, no commercial brands.

            Bedtime keyword: $keyword
            Active languages: ${activeNamesLiteral(active)}
            Bridge language for tone calibration: ${family.bridge}
            Family vocabulary:
            ${renderVocab(vocab, active)}
        """.trimIndent()
    }

    /** F2 daily phrase. */
    fun dailyPhrase(date: String, family: FamilySetup, recent: List<String>, vocab: List<FamilyWord>): String {
        val active = family.householdLanguages
        return """
            Return JSON only. Schema:
            {
              "date": "$date",
              "phrase_by_lang": {
                ${active.joinToString(",\n                ") { "\"$it\": \"<a daily-life phrase>\"" }}
              },
              "situation": "<one sentence in ${family.bridge} on when a multilingual family says this>",
              "pronunciation_hints_by_lang": {
                ${active.joinToString(",\n                ") { "\"$it\": \"<short hint for a non-$it speaker>\"" }}
              },
              "mission": "<one short challenge for the family today, ≤ 12 words, in ${family.bridge}>",
              "safety": {"child_safe": true, "no_private_data": true}
            }

            Avoid duplicating phrases used this week: ${recent.joinToString(" | ")}
            The phrase must be natural in all active languages, not a literal translation.
            Active languages: ${activeNamesLiteral(active)}
            Family vocabulary:
            ${renderVocab(vocab, active)}
        """.trimIndent()
    }

    fun pronunciation(target: String, heard: String, family: FamilySetup): String = """
        A child age ${family.ageBand} just tried to say a target word. The on-device
        speech recognizer transcribed what it heard. Score gently. Output JSON only:

        {
          "target": "$target",
          "heard_text": "$heard",
          "score_0_3": <int 0..3>,
          "encouragement_in_bridge": "<one warm short sentence in ${family.bridge}>",
          "retry_hint": "<a tiny tip for the parent in ${family.bridge}>"
        }

        Scoring rubric (be generous with toddlers):
        - 0 = totally different word or silence
        - 1 = right syllable count, wrong sounds
        - 2 = recognizable, missing a phoneme
        - 3 = clearly the target

        Target: $target
        Recognized: $heard
        Child age band: ${family.ageBand}
        Bridge language: ${family.bridge}
    """.trimIndent()

    fun mealtimeNarration(detected: String, family: FamilySetup, vocab: List<FamilyWord>): String {
        val active = family.householdLanguages
        return """
            You are running in continuous mealtime mode. The camera detected a new
            object on the table. Return JSON only:

            {
              "detected_object": "$detected",
              "one_liner_by_lang": {
                ${active.joinToString(",\n                ") { "\"$it\": \"<≤ 12-word kid-friendly sentence>\"" }}
              },
              "child_question_in_bridge": "<one playful question for the child in ${family.bridge}>"
            }

            Constraints:
            - Tone: warm, curious, suitable for ${family.ageBand}.
            - No food-allergy advice, no calorie talk, no commercial products.
            - If the detected_object is unsafe for this age, set every one_liner to "—" and explain in the question.

            Detected object: $detected
            Active languages: ${activeNamesLiteral(active)}
            Family vocabulary: ${renderVocab(vocab, active)}
        """.trimIndent()
    }

    fun familyWordSuggest(givenLang: String, givenWord: String, familyNote: String, family: FamilySetup): String {
        val targets = family.householdLanguages.filter { it != givenLang }
        return """
            The parent gave us one word for a family-specific concept in $givenLang.
            Suggest the equivalents in the other household languages. JSON only:

            {
              ${targets.joinToString(",\n              ") { "\"${it}_suggestions\": [\"<top 1>\", \"<top 2>\"]" }},
              "note": "<one-line cultural usage note in ${family.bridge}>"
            }

            Given language: $givenLang
            Given word: $givenWord
            Family note: $familyNote
            Bridge language: ${family.bridge}
        """.trimIndent()
    }
}
