import Foundation

/// Mirrors prototype/android/.../llm/PromptLibrary.kt verbatim.
/// 4L LoRA (4l_policy_family_repair_seed10_s1500) trained on this prompt-style.
enum PromptLibrary {

    private static func renderVocab(_ words: [FamilyWord], active: [String]) -> String {
        words.isEmpty ? "(none yet)" : words.map { $0.toPromptLine(active: active) }.joined(separator: "\n")
    }

    private static func activeListLiteral(_ active: [String]) -> String {
        active.map { "\"\($0)\"" }.joined(separator: ", ")
    }

    private static func activeNamesLiteral(_ active: [String]) -> String {
        active.map { Lang.label($0) }.joined(separator: ", ")
    }

    static func objectCard(object: String, family: FamilySetup, vocab: [FamilyWord]) -> String {
        let active = family.householdLanguages
        return """
        Return JSON only. No prose, no markdown fence. Schema:
        {
          "mode": "\(family.mode)",
          "age_band": "\(family.ageBand)",
          "active_languages": [\(activeListLiteral(active))],
          "card": { /* per-language object names + parent prompt + child action */ },
          "next_action": "<one short next step for the parent in \(family.bridge)>",
          "safety": {"child_safe": true, "no_private_data": true}
        }

        The household speaks: \(activeNamesLiteral(active)).
        Object: \(object)
        Family vocabulary (use when natural):
        \(renderVocab(vocab, active: active))
        """
    }

    static func bedtimeStory(keyword: String, family: FamilySetup, vocab: [FamilyWord]) -> String {
        let active = family.householdLanguages
        let paragraphsSchema = active.map { "          \"\($0)\": [\"<para 1>\", \"<para 2>\", \"<para 3>\"]" }.joined(separator: ",\n")
        return """
        Return JSON only. Schema:
        {
          "theme": "<one-word theme>",
          "paragraphs_by_lang": {
        \(paragraphsSchema)
          },
          "age_band": "\(family.ageBand)",
          "child_name": "\(family.childName)",
          "safety": {"child_safe": true, "no_private_data": true}
        }

        Constraints:
        - Each paragraph ≤ 3 sentences. Total reading time ≤ 60 s per language.
        - Paragraphs across languages mirror the same scene order.
        - Use the child's name "\(family.childName)" naturally in 1–2 paragraphs.
        - Child-safe content only.

        Bedtime keyword: \(keyword)
        Active languages: \(activeNamesLiteral(active))
        Bridge language for tone calibration: \(family.bridge)
        Family vocabulary:
        \(renderVocab(vocab, active: active))
        """
    }

    static func dailyPhrase(date: String, family: FamilySetup, recent: [String], vocab: [FamilyWord]) -> String {
        let active = family.householdLanguages
        let phrases = active.map { "          \"\($0)\": \"<a daily-life phrase>\"" }.joined(separator: ",\n")
        let hints = active.map { "          \"\($0)\": \"<short hint for a non-\($0) speaker>\"" }.joined(separator: ",\n")
        return """
        Return JSON only. Schema:
        {
          "date": "\(date)",
          "phrase_by_lang": {
        \(phrases)
          },
          "situation": "<one sentence in \(family.bridge) on when a multilingual family says this>",
          "pronunciation_hints_by_lang": {
        \(hints)
          },
          "mission": "<one short challenge for the family today, ≤ 12 words, in \(family.bridge)>",
          "safety": {"child_safe": true, "no_private_data": true}
        }

        Avoid duplicating phrases used this week: \(recent.joined(separator: " | "))
        Active languages: \(activeNamesLiteral(active))
        Family vocabulary:
        \(renderVocab(vocab, active: active))
        """
    }

    static func pronunciation(target: String, heard: String, family: FamilySetup) -> String {
        """
        A child age \(family.ageBand) just tried to say a target word. The on-device
        speech recognizer transcribed what it heard. Score gently. Output JSON only:

        {
          "target": "\(target)",
          "heard_text": "\(heard)",
          "score_0_3": <int 0..3>,
          "encouragement_in_bridge": "<one warm short sentence in \(family.bridge)>",
          "retry_hint": "<a tiny tip for the parent in \(family.bridge)>"
        }

        Scoring rubric (be generous with toddlers):
        - 0 = totally different word or silence
        - 1 = right syllable count, wrong sounds
        - 2 = recognizable, missing a phoneme
        - 3 = clearly the target

        Target: \(target)
        Recognized: \(heard)
        Child age band: \(family.ageBand)
        Bridge language: \(family.bridge)
        """
    }

    static func mealtimeNarration(detected: String, family: FamilySetup, vocab: [FamilyWord]) -> String {
        let active = family.householdLanguages
        let lines = active.map { "          \"\($0)\": \"<≤ 12-word kid-friendly sentence>\"" }.joined(separator: ",\n")
        return """
        You are running in continuous mealtime mode. The camera detected a new
        object on the table. Return JSON only:

        {
          "detected_object": "\(detected)",
          "one_liner_by_lang": {
        \(lines)
          },
          "child_question_in_bridge": "<one playful question for the child in \(family.bridge)>"
        }

        Constraints:
        - Tone: warm, curious, suitable for \(family.ageBand).
        - No food-allergy advice, no calorie talk, no commercial products.
        - If the detected_object is unsafe for this age, set every one_liner to "—" and explain in the question.

        Detected object: \(detected)
        Active languages: \(activeNamesLiteral(active))
        Family vocabulary: \(renderVocab(vocab, active: active))
        """
    }
}
