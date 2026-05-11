import Foundation

/// Family setup, persisted across sessions (UserDefaults).
struct FamilySetup: Codable, Equatable {
    var childName: String = "the child"
    var ageBand: String = "0-2"          // 0-2 | 3-5 | 6-8
    var mode: String = "baby_0_2"        // baby_0_2 | child_3_6 | parent_bridge
    var bridge: String = "en"            // any of the 3 active languages
    var householdLanguages: [String] = ["ko", "ru", "en"]  // any 3 of {ko,ru,en,fr}
}

struct FamilyWord: Codable, Identifiable, Hashable {
    var id = UUID()
    var ko: String = ""
    var ru: String = ""
    var en: String = ""
    var fr: String = ""
    var emoji: String = ""
    var note: String = ""

    func toPromptLine(active: [String]) -> String {
        let parts: [String] = active.compactMap { code in
            switch code {
            case "ko": return ko.isEmpty ? nil : ko
            case "ru": return ru.isEmpty ? nil : ru
            case "en": return en.isEmpty ? nil : en
            case "fr": return fr.isEmpty ? nil : fr
            default: return nil
            }
        }
        let head = emoji.isEmpty ? "" : "\(emoji) "
        let tail = note.isEmpty ? "" : " — \(note)"
        return "- \(head)\(parts.joinToString(" / "))\(tail)"
    }
}

struct Safety: Codable, Hashable {
    var childSafe: Bool = true
    var noPrivateData: Bool = true
    enum CodingKeys: String, CodingKey {
        case childSafe = "child_safe"
        case noPrivateData = "no_private_data"
    }
}

/// Core 4L family card — matches probes_v4_4l_audit.jsonl required keys.
struct FamilyCard: Codable {
    let mode: String?
    let ageBand: String?
    let activeLanguages: [String]?
    let card: AnyCodable?
    let nextAction: String?
    let safety: Safety?
    enum CodingKeys: String, CodingKey {
        case mode, card, safety
        case ageBand = "age_band"
        case activeLanguages = "active_languages"
        case nextAction = "next_action"
    }
}

struct BedtimeStory: Codable {
    let theme: String?
    let paragraphsByLang: [String: [String]]?
    let ageBand: String?
    let childName: String?
    let safety: Safety?
    enum CodingKeys: String, CodingKey {
        case theme, safety
        case paragraphsByLang = "paragraphs_by_lang"
        case ageBand = "age_band"
        case childName = "child_name"
    }
}

struct DailyPhrase: Codable {
    let date: String?
    let phraseByLang: [String: String]?
    let situation: String?
    let pronunciationHintsByLang: [String: String]?
    let mission: String?
    let safety: Safety?
    enum CodingKeys: String, CodingKey {
        case date, situation, mission, safety
        case phraseByLang = "phrase_by_lang"
        case pronunciationHintsByLang = "pronunciation_hints_by_lang"
    }
}

struct PronunciationVerdict: Codable {
    let target: String?
    let heardText: String?
    let score: Int?
    let encouragement: String?
    let retryHint: String?
    enum CodingKeys: String, CodingKey {
        case target
        case heardText = "heard_text"
        case score = "score_0_3"
        case encouragement = "encouragement_in_bridge"
        case retryHint = "retry_hint"
    }
}

struct MealtimeNarration: Codable {
    let detectedObject: String?
    let oneLinerByLang: [String: String]?
    let childQuestion: String?
    enum CodingKeys: String, CodingKey {
        case detectedObject = "detected_object"
        case oneLinerByLang = "one_liner_by_lang"
        case childQuestion = "child_question_in_bridge"
    }
}

/// Type-erased value so the model can hand back any shape inside `card`.
struct AnyCodable: Codable {
    let value: Any
    init(_ value: Any) { self.value = value }
    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if let v = try? c.decode(String.self) { value = v }
        else if let v = try? c.decode(Bool.self) { value = v }
        else if let v = try? c.decode(Double.self) { value = v }
        else if let v = try? c.decode([String: AnyCodable].self) { value = v.mapValues { $0.value } }
        else if let v = try? c.decode([AnyCodable].self) { value = v.map { $0.value } }
        else if c.decodeNil() { value = NSNull() }
        else { value = NSNull() }
    }
    func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        switch value {
        case let v as String: try c.encode(v)
        case let v as Bool: try c.encode(v)
        case let v as Double: try c.encode(v)
        default: try c.encodeNil()
        }
    }
}

enum Schemas {
    static func parse<T: Decodable>(_ raw: String, as type: T.Type = T.self) -> T? {
        guard let s = raw.firstIndex(of: "{"),
              let e = raw.lastIndex(of: "}"),
              s < e else { return nil }
        let json = String(raw[s...e])
        return try? JSONDecoder().decode(T.self, from: Data(json.utf8))
    }
}

enum Lang {
    static let all = ["ko", "ru", "en", "fr"]
    static let labels: [String: String] = ["ko": "한국어", "ru": "Русский", "en": "English", "fr": "Français"]
    static let ttsTag: [String: String] = ["ko": "ko-KR", "ru": "ru-RU", "en": "en-US", "fr": "fr-FR"]
    static func label(_ code: String) -> String { labels[code] ?? code.uppercased() }
}

private extension Array where Element == String {
    func joinToString(_ sep: String) -> String { joined(separator: sep) }
}
