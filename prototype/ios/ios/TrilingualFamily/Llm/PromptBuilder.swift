import Foundation

enum PromptBuilder {
    /// Mirrors com.example.trilingual.llm.PromptBuilder.objectCard on Android
    /// — keep both in sync verbatim so card schema is identical across platforms.
    static func objectCard(object: String, ageBand: String, bridge: String) -> String {
        """
        You are an offline trilingual family tutor for a household where Korean,
        Russian and English are all spoken. Output ONE JSON object only — no
        prose, no markdown fence — matching exactly this schema:

        {
          "object": "<the object name>",
          "korean": "<Korean word with Hangul>",
          "russian": "<Russian word with Cyrillic>",
          "english": "<English word>",
          "l1_note": "<one sentence in \(bridge) explaining when a \(bridge)-L1 parent should switch script>",
          "pronunciation_aid": "<short cross-script pronunciation aid for the parent>",
          "age_band": "\(ageBand)",
          "safety_flag": "ok|review|block"
        }

        Object to teach: \(object)
        Bridge language for the parent reading this card: \(bridge)
        Child age band: \(ageBand)
        """
    }
}
