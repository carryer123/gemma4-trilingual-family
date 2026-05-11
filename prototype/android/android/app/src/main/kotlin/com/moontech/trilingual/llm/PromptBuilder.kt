package com.moontech.trilingual.llm

object PromptBuilder {
    /**
     * Trilingual KO/RU/EN object-card prompt.
     * Output schema enforced (JSON-only) so TrilingualCard.parseOrNull can take it.
     */
    fun objectCard(objectName: String, ageBand: String, bridge: String): String = """
        You are an offline trilingual family tutor for a household where Korean,
        Russian and English are all spoken. Output ONE JSON object only — no
        prose, no markdown fence — matching exactly this schema:

        {
          "object": "<the object name>",
          "korean": "<Korean word with Hangul>",
          "russian": "<Russian word with Cyrillic>",
          "english": "<English word>",
          "l1_note": "<one sentence in $bridge explaining when a $bridge-L1 parent should switch script>",
          "pronunciation_aid": "<short cross-script pronunciation aid for the parent>",
          "age_band": "$ageBand",
          "safety_flag": "ok|review|block"
        }

        Object to teach: $objectName
        Bridge language for the parent reading this card: $bridge
        Child age band: $ageBand
    """.trimIndent()
}
