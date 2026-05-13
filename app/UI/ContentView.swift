// Auto-merged: StateGates logic inlined to keep Xcode target build simple.
// Original file: Models/StateGates.swift (kept for reference but not in target).


// =============================================================================
//  StateGates.swift
//  Live G1–G4 deployment-state evaluator for the family-tutor LoRA adapter.
//  Reflects the audit suite documented in our EMNLP 2026 paper:
//    "From False-Green Detection to Gate-Aware Repair: State-Gated Data
//     Curricula for Multilingual LoRA Adapters" (KO/RU/FR/EN, seed 10).
// =============================================================================
//  G1  family-card structure + age policy
//  G2  cross-script discipline (Hangul / Cyrillic / Latin / CJK / Thai…)
//  G3  JSON schema validity (parseable + required keys + enums + no extras)
//  G4  session-language routing (no inactive-language leakage)
// =============================================================================

enum GateBand: String { case green, amber, red }

struct GateReport {
    let g1Structure: Double   // 0…1
    let g1Age:       Double
    let g2Script:    Double
    let g3Schema:    Double
    let g4Routing:   Double
    let band:        GateBand
    let issues:      [String]
    let parsedCard:  FamilyCard?
}

// -----------------------------------------------------------------------------
//  Family card schema (G1 structure + G3 schema)
// -----------------------------------------------------------------------------
struct FamilyCard: Codable {
    let title: String
    let mode: String                  // story | words | song | say | between | culture
    let target_age: Int
    let active_languages: [String]    // ISO names: Korean, English, Русский, Français
    let body: [String: String]        // per-language paragraph
    let play_prompt: String
}

// -----------------------------------------------------------------------------
//  Unicode script bucketing
// -----------------------------------------------------------------------------
enum ScriptKind: String {
    case hangul, cyrillic, latin, han, hiragana, katakana, thai, arabic, other
}

func scriptFor(_ scalar: Unicode.Scalar) -> ScriptKind {
    let v = scalar.value
    switch v {
    case 0xAC00...0xD7A3, 0x1100...0x11FF, 0x3130...0x318F: return .hangul
    case 0x0400...0x04FF, 0x0500...0x052F: return .cyrillic
    case 0x0041...0x005A, 0x0061...0x007A,
         0x00C0...0x00FF, 0x0100...0x024F: return .latin           // basic + diacritics
    case 0x4E00...0x9FFF, 0x3400...0x4DBF: return .han
    case 0x3040...0x309F:                  return .hiragana
    case 0x30A0...0x30FF, 0x31F0...0x31FF: return .katakana
    case 0x0E00...0x0E7F:                  return .thai
    case 0x0600...0x06FF, 0x0750...0x077F: return .arabic
    default:                               return .other
    }
}

func scriptRatios(_ text: String) -> [ScriptKind: Double] {
    var counts: [ScriptKind: Int] = [:]
    var total = 0
    for scalar in text.unicodeScalars where !scalar.properties.isWhitespace {
        let kind = scriptFor(scalar)
        if kind == .other { continue }
        counts[kind, default: 0] += 1
        total += 1
    }
    guard total > 0 else { return [:] }
    var ratios: [ScriptKind: Double] = [:]
    for (k, c) in counts { ratios[k] = Double(c) / Double(total) }
    return ratios
}

// -----------------------------------------------------------------------------
//  Language ↔ expected script
// -----------------------------------------------------------------------------
func expectedScript(forLanguage lang: String) -> ScriptKind {
    switch lang {
    case "Korean":               return .hangul
    case "Русский":              return .cyrillic
    case "中文":                 return .han
    case "日本語":               return .hiragana
    case "Tiếng Việt", "English",
         "Français", "Español",
         "Türkçe", "O'zbek":     return .latin
    case "ภาษาไทย":              return .thai
    case "Монгол":               return .cyrillic
    default:                     return .latin
    }
}

// -----------------------------------------------------------------------------
//  JSON extraction — robust to leading/trailing prose
// -----------------------------------------------------------------------------
func extractJSONObject(from text: String) -> String? {
    var depth = 0
    var start: String.Index? = nil
    for idx in text.indices {
        let c = text[idx]
        if c == "{" {
            if depth == 0 { start = idx }
            depth += 1
        } else if c == "}" {
            depth -= 1
            if depth == 0, let s = start {
                let end = text.index(after: idx)
                return String(text[s..<end])
            }
        }
    }
    return nil
}

// -----------------------------------------------------------------------------
//  Soft / forgiving card parser
// -----------------------------------------------------------------------------
//  Strict JSON often fails because the model truncates mid-string, omits a
//  closing brace, or writes natural prose around the JSON. We never want the
//  user to see raw `"title": "..."` text in the result panel — so this parser
//  pulls the fields out regardless and the resultCard renders the colored
//  per-language tiles even when the model didn't close its JSON.
// -----------------------------------------------------------------------------
// Block-tag parser. Splits model output on `=== <language> ===` headers (or
// looser variants like `### Korean ###`, `[Korean]`, `## Korean`) and bins
// each block into a per-language body. This is the parser the new prompt is
// designed for; it always produces a card as long as one language header is
// present.
func parseLanguageBlocks(from raw: String,
                         activeLanguages: [String],
                         targetAge: Int,
                         mode: String) -> FamilyCard? {

    var cleaned = raw
        .replacingOccurrences(of: "<|turn>", with: "")
        .replacingOccurrences(of: "<turn|>", with: "")
        .replacingOccurrences(of: "<bos>",   with: "")
        .replacingOccurrences(of: "<eos>",   with: "")
    if let r = cleaned.range(of: "\nDone") { cleaned = String(cleaned[..<r.lowerBound]) }
    cleaned = cleaned.trimmingCharacters(in: .whitespacesAndNewlines)

    // Header: capture ANY label inside `=== ... ===`, `## ... ##`, `**...**`,
    // `[ ... ]`, or `<lang>:` at line start, then fuzzy-map the captured text
    // to one of the canonical active languages. Models routinely substitute
    // localized names (Russian / Russe / 러시아어) or use bare ASCII names where
    // the prompt asked for `Русский`, so a substring map is required.
    let headerPattern = #"(?m)^\s*(?:={2,}\s*([^=\n]+?)\s*={2,}|#{2,}\s*([^#\n]+?)\s*#*|\[\s*([^\]\n]+?)\s*\]|\*\*\s*([^*\n]+?)\s*\*\*|([\p{L}][\p{L} ]{1,30}?)\s*:)\s*$"#

    guard let regex = try? NSRegularExpression(pattern: headerPattern, options: []) else {
        return nil
    }
    let ns = cleaned as NSString
    let matches = regex.matches(in: cleaned, options: [], range: NSRange(location: 0, length: ns.length))
    guard !matches.isEmpty else { return nil }

    func canonical(for label: String) -> String? {
        let needle = label.lowercased().trimmingCharacters(in: .whitespacesAndNewlines)
        // Per-canonical aliases (lowercased).
        let aliases: [String: [String]] = [
            "Korean":  ["korean", "ko", "kor", "한국어", "한국말", "韓国語", "корейский", "coréen", "coreen"],
            "English": ["english", "en", "eng", "영어", "английский", "anglais", "ingles", "inglés"],
            "Русский": ["русский", "ru", "rus", "russian", "러시아어", "russe", "russisch", "ruso"],
            "Français":["français", "francais", "fr", "fra", "french", "프랑스어", "французский", "francés"],
            "中文":    ["中文", "zh", "zho", "chinese", "중국어", "китайский", "chinois"],
            "日本語":  ["日本語", "ja", "jpn", "japanese", "일본어", "японский", "japonais"],
            "Español": ["español", "espanol", "es", "spa", "spanish", "스페인어", "испанский", "espagnol"],
            "Türkçe":  ["türkçe", "turkce", "tr", "tur", "turkish", "터키어", "튀르키예어", "турецкий", "turc"],
        ]
        // Try active langs first; only those get mapped back.
        for canon in activeLanguages {
            if let pool = aliases[canon], pool.contains(where: { needle == $0 || needle.contains($0) }) {
                return canon
            }
            if needle == canon.lowercased() { return canon }
        }
        return nil
    }

    // Collect (range, canonicalLang) for each successful header match.
    struct Header { let location: Int; let length: Int; let lang: String }
    var headers: [Header] = []
    for m in matches {
        var captured = ""
        for g in 1...5 {
            let r = m.range(at: g)
            if r.location != NSNotFound, r.length > 0 {
                captured = ns.substring(with: r)
                break
            }
        }
        guard !captured.isEmpty, let canon = canonical(for: captured) else { continue }
        headers.append(Header(location: m.range.location, length: m.range.length, lang: canon))
    }
    guard !headers.isEmpty else { return nil }

    var body: [String: String] = [:]
    for i in 0..<headers.count {
        let h = headers[i]
        let blockStart = h.location + h.length
        let blockEnd = i + 1 < headers.count ? headers[i + 1].location : ns.length
        guard blockEnd > blockStart else { continue }
        let block = ns.substring(with: NSRange(location: blockStart, length: blockEnd - blockStart))
            .trimmingCharacters(in: .whitespacesAndNewlines)
        if !block.isEmpty, body[h.lang] == nil {
            body[h.lang] = block
        }
    }
    guard !body.isEmpty else { return nil }

    return FamilyCard(
        title: "",
        mode: mode,
        target_age: targetAge,
        active_languages: activeLanguages,
        body: body,
        play_prompt: ""
    )
}

func softParseCard(from raw: String,
                   activeLanguages: [String],
                   familyLanguages: [String],
                   targetAge: Int,
                   mode: String) -> FamilyCard? {

    func escape(_ s: String) -> String {
        NSRegularExpression.escapedPattern(for: s)
    }

    // Strip chat-template scaffolding + the LlamaState "Done" trailer.
    var cleaned = raw
        .replacingOccurrences(of: "<|turn>", with: "")
        .replacingOccurrences(of: "<turn|>", with: "")
        .replacingOccurrences(of: "<bos>",   with: "")
        .replacingOccurrences(of: "<eos>",   with: "")
    if let r = cleaned.range(of: "\nDone") { cleaned = String(cleaned[..<r.lowerBound]) }

    // ------------------------------------------------------------------ value
    // Pull the value of a `"key": "..."` pair, tolerant to truncated strings.
    // When the closing quote is missing (model cut off), we still return the
    // text we got. `stopKeys` defines other keys at the same level that should
    // terminate the value greedily if a closing quote isn't found.
    func value(forKey key: String, in scope: String, stopKeys: [String]) -> String? {
        let openPat = "\"\(escape(key))\"\\s*:\\s*\""
        guard let openRange = scope.range(of: openPat, options: .regularExpression)
            else { return nil }
        let after = scope[openRange.upperBound...]

        var endIdx = after.endIndex

        // Stop at any other known sibling key.
        for k in stopKeys {
            let stop = "\"\\s*,\\s*\"\(escape(k))\""
            if let r = after.range(of: stop, options: .regularExpression),
               r.lowerBound < endIdx { endIdx = r.lowerBound }
            // Or the simpler boundary: `","<k>"`
            let stop2 = "\",\\s*\"\(escape(k))\""
            if let r = after.range(of: stop2, options: .regularExpression),
               r.lowerBound < endIdx { endIdx = r.lowerBound }
        }
        // End of object boundary.
        for closer in ["\"\\s*\\}", "\"\\s*\\}\\s*,"] {
            if let r = after.range(of: closer, options: .regularExpression),
               r.lowerBound < endIdx { endIdx = r.lowerBound }
        }
        // If a proper closing quote exists before any sibling marker, prefer it.
        // We approximate by scanning for the first un-escaped quote and using
        // its position only if it's earlier than everything above.
        var i = after.startIndex
        while i < endIdx {
            let c = after[i]
            if c == "\\" {
                // Skip the backslash + the escaped character.
                let nxt = after.index(after: i)
                if nxt < endIdx {
                    i = after.index(after: nxt)
                } else {
                    i = endIdx
                }
                continue
            }
            if c == "\"" { endIdx = i; break }
            i = after.index(after: i)
        }

        var val = String(after[..<endIdx])
        val = val.replacingOccurrences(of: "\\\"", with: "\"")
                 .replacingOccurrences(of: "\\n",  with: "\n")
                 .replacingOccurrences(of: "\\t",  with: " ")
                 .trimmingCharacters(in: .whitespacesAndNewlines)
        return val.isEmpty ? nil : val
    }

    // Scope body lookups so we don't accidentally hit "Korean" inside
    // `active_languages`.
    var bodyScope = cleaned
    if let bodyOpen = cleaned.range(of: "\"body\"\\s*:\\s*\\{",
                                    options: .regularExpression) {
        bodyScope = String(cleaned[bodyOpen.upperBound...])
    }

    let otherLangs = familyLanguages
    var body: [String: String] = [:]
    for lang in familyLanguages {
        let stops = otherLangs.filter { $0 != lang } + ["play_prompt"]
        if let v = value(forKey: lang, in: bodyScope, stopKeys: stops) {
            body[lang] = v
        }
    }

    let title = value(forKey: "title", in: cleaned,
                      stopKeys: ["mode","target_age","active_languages","body","play_prompt"]) ?? ""
    let play  = value(forKey: "play_prompt", in: cleaned, stopKeys: []) ?? ""

    // Last-resort fallback: if not one body field came out but the model did
    // emit natural prose (no JSON scaffolding), put the prose under the parent
    // language so something still renders.
    if body.isEmpty {
        let prose = cleaned.trimmingCharacters(in: .whitespacesAndNewlines)
        let looksLikeJSON = prose.contains("\"title\"") || prose.contains("\"body\"")
        if !looksLikeJSON, !prose.isEmpty, let first = activeLanguages.first {
            body[first] = prose
        }
    }

    guard !body.isEmpty else { return nil }

    return FamilyCard(
        title: title.isEmpty ? "Your story" : title,
        mode: mode,
        target_age: targetAge,
        active_languages: activeLanguages,
        body: body,
        play_prompt: play
    )
}

// -----------------------------------------------------------------------------
//  Age-policy heuristic
// -----------------------------------------------------------------------------
//  Per EMNLP §G1: structural validity + age-appropriate sentence length and
//  vocabulary complexity. We approximate with a sentence-length budget by
//  target age and a simple-vocabulary ratio.
// -----------------------------------------------------------------------------
struct AgePolicy {
    let maxSentenceWords: Int
    let preferredTokenChars: Int
    static func forAge(_ age: Int) -> AgePolicy {
        switch age {
        case 0...2:  return .init(maxSentenceWords: 8,  preferredTokenChars: 5)
        case 3...4:  return .init(maxSentenceWords: 12, preferredTokenChars: 6)
        case 5...6:  return .init(maxSentenceWords: 16, preferredTokenChars: 7)
        default:     return .init(maxSentenceWords: 22, preferredTokenChars: 9)
        }
    }
}

private func sentences(_ text: String) -> [String] {
    var out: [String] = []
    var current = ""
    for ch in text {
        current.append(ch)
        if ch == "." || ch == "!" || ch == "?" || ch == "。" || ch == "？" || ch == "！" {
            let trimmed = current.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty { out.append(trimmed) }
            current = ""
        }
    }
    let trimmed = current.trimmingCharacters(in: .whitespacesAndNewlines)
    if !trimmed.isEmpty { out.append(trimmed) }
    return out
}

private func wordCount(_ s: String) -> Int {
    s.split(whereSeparator: { $0.isWhitespace || $0 == "," || $0 == "、" }).count
}

// -----------------------------------------------------------------------------
//  Main evaluator
// -----------------------------------------------------------------------------
enum StateGates {

    static func evaluate(rawOutput: String,
                         activeLanguages: [String],
                         familyLanguages: [String],
                         targetAge: Int) -> GateReport {

        var issues: [String] = []

        // ------------------------------------------------------------ G3 schema
        var g3 = 0.0
        var card: FamilyCard? = nil
        if let jsonStr = extractJSONObject(from: rawOutput),
           let data = jsonStr.data(using: .utf8) {
            do {
                card = try JSONDecoder().decode(FamilyCard.self, from: data)
                g3 = 1.0
            } catch {
                if let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    let required: Set<String> = ["title", "mode", "target_age",
                                                 "active_languages", "body", "play_prompt"]
                    let present = required.intersection(obj.keys)
                    g3 = Double(present.count) / Double(required.count)
                    issues.append("G3: missing keys \(required.subtracting(obj.keys))")
                } else {
                    issues.append("G3: JSON could not be parsed")
                }
            }
        } else {
            issues.append("G3: no JSON object found in output")
        }

        // ------------------------------------------------------------ G1 struct
        let g1Struct: Double = card != nil ? 1.0 : g3

        // ------------------------------------------------------------ G1 age
        var g1Age = 1.0
        if let card {
            let policy = AgePolicy.forAge(targetAge)
            var violations = 0
            var total = 0
            for (_, body) in card.body {
                for s in sentences(body) {
                    total += 1
                    if wordCount(s) > policy.maxSentenceWords { violations += 1 }
                }
            }
            if total > 0 {
                g1Age = 1.0 - Double(violations) / Double(total)
                if violations > 0 {
                    issues.append("G1-age: \(violations)/\(total) sentences exceed \(policy.maxSentenceWords)-word budget for age \(targetAge)")
                }
            }
        }

        // ------------------------------------------------------------ G2 script
        var g2Hits = 0
        var g2Checks = 0
        if let card {
            for lang in activeLanguages {
                guard let body = card.body[lang] else { continue }
                let ratios = scriptRatios(body)
                let want = expectedScript(forLanguage: lang)
                let primary = ratios[want] ?? 0
                let foreignMax = ratios
                    .filter { $0.key != want && $0.key != .latin }
                    .values.max() ?? 0
                g2Checks += 1
                if primary >= 0.85 && foreignMax <= 0.10 {
                    g2Hits += 1
                } else {
                    issues.append(String(format: "G2: %@ body has primary=%.0f%% foreign=%.0f%%",
                                         lang, primary*100, foreignMax*100))
                }
            }
        }
        let g2: Double = g2Checks > 0 ? Double(g2Hits) / Double(g2Checks) : 1.0

        // ------------------------------------------------------------ G4 routing
        var g4: Double = 1.0
        if let card {
            let inactive = Set(familyLanguages).subtracting(activeLanguages)
            let inactiveScripts: Set<ScriptKind> = Set(inactive.map(expectedScript(forLanguage:)))
            let activeScripts:   Set<ScriptKind> = Set(activeLanguages.map(expectedScript(forLanguage:)))
            // Only flag scripts that are exclusive to an inactive language.
            let exclusivelyInactive = inactiveScripts.subtracting(activeScripts)
            if !exclusivelyInactive.isEmpty {
                let allBody = card.body.values.joined(separator: "\n")
                let ratios = scriptRatios(allBody)
                let leak = ratios
                    .filter { exclusivelyInactive.contains($0.key) }
                    .values.max() ?? 0
                if leak > 0.05 {
                    g4 = max(0.0, 1.0 - leak * 4.0)
                    issues.append(String(format: "G4: %.0f%% of output is in an inactive script (active=%@)",
                                         leak*100, activeLanguages.joined(separator: "/")))
                }
            }
        } else {
            // No card → cannot route → fail soft
            g4 = 0.5
        }

        // ------------------------------------------------------------ band
        let minScore = [g1Struct, g1Age, g2, g3, g4].min() ?? 0
        let band: GateBand
        switch minScore {
        case 0.95...1.0: band = .green
        case 0.75..<0.95: band = .amber
        default: band = .red
        }

        return GateReport(
            g1Structure: g1Struct,
            g1Age:       g1Age,
            g2Script:    g2,
            g3Schema:    g3,
            g4Routing:   g4,
            band:        band,
            issues:      issues,
            parsedCard:  card
        )
    }
}

// -----------------------------------------------------------------------------
//  Audit capsule (exportable)
// -----------------------------------------------------------------------------
struct AuditEntry: Codable {
    let timestamp: Date
    let mode: String
    let promptDigest: String          // first 200 chars
    let activeLanguages: [String]
    let targetAge: Int
    let g1Structure: Double
    let g1Age: Double
    let g2Script: Double
    let g3Schema: Double
    let g4Routing: Double
    let band: String
    let issues: [String]
    let adapterTag: String            // "policy_family_seed10" by default
}

@MainActor
final class AuditLogStore: ObservableObject {
    @Published var entries: [AuditEntry] = []

    func append(_ entry: AuditEntry) {
        entries.append(entry)
    }

    func export() -> URL? {
        let enc = JSONEncoder()
        enc.outputFormatting = [.prettyPrinted, .sortedKeys]
        enc.dateEncodingStrategy = .iso8601
        guard let data = try? enc.encode(entries) else { return nil }
        let url = FileManager.default
            .urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("audit_capsule.json")
        try? data.write(to: url)
        return url
    }
}

import SwiftUI
import UniformTypeIdentifiers
import Speech
import AVFoundation
import Vision
import UIKit

// =============================================================================
//  SpeechRecognizer — on-device Apple Speech wrapper used to capture the
//  parent's spoken prompt while their hands are full. Authorization is
//  requested lazily; recognition is forced on-device when supported.
// =============================================================================
@MainActor
// =============================================================================
//  Per-language TTS — Apple AVSpeechSynthesizer with the matching voice.
// =============================================================================
final class FamilyTTS: NSObject, ObservableObject, AVSpeechSynthesizerDelegate {
    @Published var speakingLang: String? = nil
    private let synth = AVSpeechSynthesizer()
    override init() {
        super.init()
        synth.delegate = self
    }
    // Per-language explicit voice identifier (parent-picked in Settings).
    // Empty value means "Auto — best available".
    private func storedID(for language: String) -> String {
        UserDefaults.standard.string(forKey: "tts.voice.\(language)") ?? ""
    }
    func setVoiceID(_ id: String, for language: String) {
        UserDefaults.standard.set(id, forKey: "tts.voice.\(language)")
        objectWillChange.send()
    }
    func voiceID(for language: String) -> String { storedID(for: language) }
    func speak(_ text: String, language: String) {
        if speakingLang == language {
            synth.stopSpeaking(at: .immediate)
            speakingLang = nil
            return
        }
        if synth.isSpeaking { synth.stopSpeaking(at: .immediate) }
        let utt = AVSpeechUtterance(string: text)
        let bcp47 = ttsBCP47(forLanguage: language)
        let pickedID = storedID(for: language)
        if !pickedID.isEmpty,
           let v = AVSpeechSynthesisVoice(identifier: pickedID) {
            utt.voice = v
        } else {
            utt.voice = bestVoice(forBCP47: bcp47)
        }
        utt.rate = AVSpeechUtteranceDefaultSpeechRate * 0.92
        utt.pitchMultiplier = 1.05
        speakingLang = language
        synth.speak(utt)
    }
    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer,
                                       didFinish utterance: AVSpeechUtterance) {
        Task { @MainActor in self.speakingLang = nil }
    }
    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer,
                                       didCancel utterance: AVSpeechUtterance) {
        Task { @MainActor in self.speakingLang = nil }
    }
}

// Pick the highest-quality installed voice that matches the language. If the
// user downloaded an Enhanced/Premium voice for ANY region of that language
// (e.g. Kate Enhanced is en-GB while we asked for en-US), prefer it over the
// default Compact en-US voice. Falls back to any voice for the base language.
func bestVoice(forBCP47 bcp47: String) -> AVSpeechSynthesisVoice? {
    let prefix = String(bcp47.prefix(2))
    let all = AVSpeechSynthesisVoice.speechVoices()
        .filter { $0.language.hasPrefix(prefix) }
    if all.isEmpty { return AVSpeechSynthesisVoice(language: prefix) }

    // Ranking: Siri-class voices > Premium > Enhanced > Default. Siri voices
    // ship with identifiers containing "siri" (e.g.
    // `com.apple.voice.premium.en-US.Aaron-siri`) and produce far more
    // natural prosody than the Compact pool the default fallback uses.
    func qualityRank(_ v: AVSpeechSynthesisVoice) -> Int {
        let isSiri = v.identifier.localizedCaseInsensitiveContains("siri")
        switch v.quality {
        case .premium:  return isSiri ? 5 : 4
        case .enhanced: return isSiri ? 3 : 2
        default:        return 1
        }
    }
    let sorted = all.sorted { a, b in
        let qa = qualityRank(a), qb = qualityRank(b)
        if qa != qb { return qa > qb }
        let exactA = (a.language == bcp47) ? 1 : 0
        let exactB = (b.language == bcp47) ? 1 : 0
        return exactA > exactB
    }
    return sorted.first
}

func ttsBCP47(forLanguage lang: String) -> String {
    switch lang {
    case "Korean":    return "ko-KR"
    case "English":   return "en-US"
    case "Русский":   return "ru-RU"
    case "Français":  return "fr-FR"
    case "中文":       return "zh-CN"
    case "日本語":     return "ja-JP"
    case "Tiếng Việt": return "vi-VN"
    case "Español":   return "es-ES"
    case "Türkçe":    return "tr-TR"
    case "Монгол":    return "mn-MN"
    case "ภาษาไทย":   return "th-TH"
    case "O'zbek":    return "uz-UZ"
    default:          return "en-US"
    }
}

final class SpeechRecognizer: NSObject, ObservableObject {
    @Published var transcript: String = ""
    @Published var isRecording: Bool = false
    @Published var authorized: Bool = false
    @Published var lastError: String? = nil

    private var recognizer: SFSpeechRecognizer?
    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var task: SFSpeechRecognitionTask?
    private let audioEngine = AVAudioEngine()

    func configure(locale: Locale) {
        recognizer = SFSpeechRecognizer(locale: locale)
        if recognizer == nil {
            lastError = "no recognizer for \(locale.identifier)"
        } else {
            lastError = nil
        }
    }

    func requestAuthorization() async {
        let speechStatus: SFSpeechRecognizerAuthorizationStatus = await withCheckedContinuation { c in
            SFSpeechRecognizer.requestAuthorization { c.resume(returning: $0) }
        }
        let micGranted: Bool = await withCheckedContinuation { c in
            AVAudioApplication.requestRecordPermission { c.resume(returning: $0) }
        }
        authorized = (speechStatus == .authorized) && micGranted
        let statusName: String
        switch speechStatus {
        case .authorized: statusName = "ok"
        case .denied:     statusName = "denied"
        case .restricted: statusName = "restricted"
        case .notDetermined: statusName = "notDetermined"
        @unknown default: statusName = "?(\(speechStatus.rawValue))"
        }
        if !authorized {
            lastError = "auth: speech=\(statusName) mic=\(micGranted ? "ok" : "denied")"
        } else {
            lastError = nil
        }
    }

    func start() throws {
        guard authorized else {
            lastError = "not authorized yet — tap Talk again to retry"
            return
        }
        guard let recognizer = recognizer else {
            lastError = "no recognizer configured"
            return
        }
        guard recognizer.isAvailable else {
            lastError = "recognizer offline (try Wi-Fi or different locale)"
            return
        }
        stop()
        transcript = ""

        let req = SFSpeechAudioBufferRecognitionRequest()
        req.shouldReportPartialResults = true
        // Do NOT pin on-device — for locales like ru-RU the on-device asset is
        // often missing, and SFSpeech silently reports "No speech detected".
        // Let the system choose; it prefers on-device when available and falls
        // back to Apple's server otherwise.
        req.requiresOnDeviceRecognition = false
        if #available(iOS 16.0, *) { req.addsPunctuation = true }
        request = req

        // Match Apple's "SpeakToMe" sample code exactly. `.record/.measurement`
        // is the documented combo for SFSpeechAudioBufferRecognitionRequest —
        // anything else has consistently produced either OSStatus -50 or
        // kAFAssistantErrorDomain 216 on this iPad.
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(.record, mode: .measurement, options: .duckOthers)
            try session.setActive(true, options: .notifyOthersOnDeactivation)
        } catch {
            lastError = "audio session: \(error.localizedDescription)"
            throw error
        }

        let node = audioEngine.inputNode
        node.removeTap(onBus: 0)
        let fmt = node.outputFormat(forBus: 0)
        guard fmt.sampleRate > 0 else {
            lastError = "mic format invalid (sr=0)"
            return
        }
        node.installTap(onBus: 0, bufferSize: 1024, format: fmt) { buffer, _ in
            req.append(buffer)
        }
        audioEngine.prepare()
        do {
            try audioEngine.start()
        } catch {
            lastError = "engine start: \(error.localizedDescription)"
            throw error
        }

        task = recognizer.recognitionTask(with: req) { [weak self] result, error in
            guard let self else { return }
            Task { @MainActor in
                if let result {
                    self.transcript = result.bestTranscription.formattedString
                }
                if let error {
                    self.lastError = "recognize: \(error.localizedDescription)"
                    self.stop()
                }
            }
        }
        isRecording = true
        lastError = "listening · \(recognizer.locale.identifier) · \(Int(fmt.sampleRate))Hz"
    }

    func stop() {
        if audioEngine.isRunning {
            audioEngine.stop()
            audioEngine.inputNode.removeTap(onBus: 0)
        }
        request?.endAudio()
        request = nil
        task?.cancel()
        task = nil
        isRecording = false
    }
}

// Map a family-language label to a SFSpeechRecognizer locale.
func speechLocale(forLanguage lang: String) -> Locale {
    switch lang {
    case "Korean":   return Locale(identifier: "ko-KR")
    case "English":  return Locale(identifier: "en-US")
    case "Русский":  return Locale(identifier: "ru-RU")
    case "Français": return Locale(identifier: "fr-FR")
    case "中文":      return Locale(identifier: "zh-CN")
    case "日本語":    return Locale(identifier: "ja-JP")
    case "Tiếng Việt": return Locale(identifier: "vi-VN")
    case "Español":   return Locale(identifier: "es-ES")
    case "Türkçe":    return Locale(identifier: "tr-TR")
    default:          return Locale(identifier: "en-US")
    }
}

// =============================================================================
//  Gemma 4 chat template — wrap a single-turn user prompt into the format
//  recorded in the GGUF metadata so that policy/family LoRA behaviour is
//  triggered. Without this wrapper the engine treats the prompt as raw
//  completion text and silently regresses to baseline behaviour.
// =============================================================================
enum GemmaChat {
    /// Wrap a single-turn user prompt in Gemma 4's actual chat tokens.
    /// Verified against the GGUF tokenizer: `<|turn>` = id 105 (turn start),
    /// `<turn|>` = id 106 (turn end / EOS). The `<bos>` token is injected by
    /// LlamaContext.tokenize(add_bos: true), so we only emit the turn markers.
    static func wrap(_ prompt: String) -> String {
        return "<|turn>user\n\(prompt)<turn|>\n<|turn>model\n"
    }
}

// =============================================================================
//  Gemma Family — State-Gated Multilingual Tutor (iPad)
// -----------------------------------------------------------------------------
//  Implements the deployment side of the EMNLP 2026 paper:
//    "From False-Green Detection to Gate-Aware Repair: State-Gated Data
//     Curricula for Multilingual LoRA Adapters" (Lee et al., 2026).
//
//  Model:  gemma4_e2b_policy.Q4_K_M.gguf   (Merged_Gemma4_E2B_Seed10, 3.2 GB)
//          common loss 0.6673, G3 100%, G4 100%, app-constrained band GREEN.
//
//  Runtime gates G1–G4 evaluated on every generation and shown in the UI.
//  Engine: llama.cpp via LlamaState (unchanged).  All inference on-device.
// =============================================================================

struct ContentView: View {
    @StateObject var llamaState = LlamaState()
    @StateObject var audit = AuditLogStore()
    @StateObject var speech = SpeechRecognizer()
    @StateObject var tts = FamilyTTS()
    @StateObject var library = LibraryStore()
    @StateObject var words = WordStore()
    @StateObject var loc = Localization()
    @State var selectedTab: AppTab = .today
    @State var visitorMode: VisitorMode = .none

    // -- family configuration -------------------------------------------------
    @AppStorage("family.langs") private var savedLangs = "Korean,English,Русский,Français"
    @AppStorage("family.kids")  private var savedKids  = "Aria:2,Maxim:4"

    // -- runtime state --------------------------------------------------------
    @State private var sessionKid: String = "Aria"
    @State private var activeLangs: Set<String> = ["Korean", "English", "Русский"]
    @State private var targetAge: Int = 2
    @State private var selectedMode: FamilyMode = .story
    @State private var userText: String = ""
    @State private var isGenerating = false
    @State private var lastReport: GateReport? = nil
    @State private var policyAdapterOn = true
    @State private var micLang: String = "Korean"
    @State private var showFamilySheet = false
    @State private var showModelSheet  = false
    @State private var showAuditSheet  = false
    @State private var generatedRaw: String = ""
    @State private var generationCheckpoint: Int = 0
    @State private var showVerifyDetails: Bool = false
    @State private var showDebugRaw: Bool = false

    private var familyLanguages: [String] {
        savedLangs.split(separator: ",").map {
            String($0).trimmingCharacters(in: .whitespaces)
        }.filter { !$0.isEmpty }
    }
    private var familyKids: [(name: String, age: Int)] {
        savedKids.split(separator: ",").compactMap { raw in
            let p = raw.split(separator: ":")
            guard p.count == 2, let a = Int(p[1]) else { return nil }
            return (String(p[0]).trimmingCharacters(in: .whitespaces), a)
        }
    }

    var body: some View {
        TabView(selection: $selectedTab) {
            todayTab
                .tabItem { Label(loc.t(.today), systemImage: "sparkles") }
                .tag(AppTab.today)
            LibraryTab(store: library, tts: tts)
                .tabItem { Label(loc.t(.library), systemImage: "books.vertical.fill") }
                .tag(AppTab.library)
            PhrasebookTab(activeLangs: Array(activeLangs),
                          familyLanguages: familyLanguages,
                          tts: tts)
                .tabItem { Label(loc.t(.phrasebook), systemImage: "text.bubble.fill") }
                .tag(AppTab.phrasebook)
            TranslateTab(activeLangs: Array(activeLangs),
                         familyLanguages: familyLanguages,
                         tts: tts, llamaState: llamaState)
                .tabItem { Label(loc.t(.translate), systemImage: "character.bubble") }
                .tag(AppTab.translate)
            WordWallTab(store: words, tts: tts)
                .tabItem { Label(loc.t(.words), systemImage: "rectangle.stack.fill") }
                .tag(AppTab.words)
            CameraTab(activeLangs: Array(activeLangs),
                      familyLanguages: familyLanguages,
                      tts: tts, llamaState: llamaState)
                .tabItem { Label(loc.t(.camera), systemImage: "camera.fill") }
                .tag(AppTab.camera)
            FamilyTab(savedLangs: $savedLangs,
                      savedKids: $savedKids,
                      visitorMode: $visitorMode,
                      activeLangs: $activeLangs,
                      familyLanguages: familyLanguages,
                      llamaState: llamaState,
                      audit: audit,
                      tts: tts,
                      policyAdapterOn: $policyAdapterOn)
                .tabItem { Label(loc.t(.family), systemImage: "person.3.fill") }
                .tag(AppTab.family)
        }
        .tint(Color(red: 0.83, green: 0.32, blue: 0.45))
        .environmentObject(loc)
        .onAppear(perform: applyKidSession)
        .onChange(of: sessionKid) { _ in applyKidSession() }
    }

    // Globe menu — appears in each tab's toolbar so language can be switched
    // from anywhere in the app.
    @ToolbarContentBuilder private var uiLanguageMenu: some ToolbarContent {
        ToolbarItem(placement: .navigationBarTrailing) {
            Menu {
                ForEach(Localization.supported, id: \.code) { lang in
                    Button {
                        loc.lang = lang.code
                    } label: {
                        Label("\(lang.flag) \(lang.label)",
                              systemImage: loc.lang == lang.code ? "checkmark" : "")
                    }
                }
            } label: {
                Text(Localization.supported.first(where: { $0.code == loc.lang })?.flag ?? "🌐")
            }
        }
    }

    private var todayTab: some View {
        NavigationStack {
            ZStack(alignment: .top) {
                background
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        hero
                        if visitorMode != .none { visitorBanner }
                        sessionRouter
                        modeGrid
                        promptCard
                        if isGenerating {
                            generatingHero
                        } else if let card = lastReport?.parsedCard {
                            resultCard(card)
                        } else if !generatedRaw.isEmpty && lastReport?.parsedCard == nil {
                            retryCard
                        }
                    }
                    .padding(.horizontal, 20).padding(.top, 12).padding(.bottom, 40)
                }
            }
            .navigationTitle("Trio")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { uiLanguageMenu }
        }
    }

    private func applyKidSession() {
        if let kid = familyKids.first(where: { $0.name == sessionKid }) {
            targetAge = kid.age
        }
        // Default active set: Korean + English + the third family language.
        let core: [String] = ["Korean", "English"]
        let extras = familyLanguages.filter { !core.contains($0) }
        let third = extras.first
        activeLangs = Set(core + (third.map { [$0] } ?? []))
        if !activeLangs.contains(micLang) {
            micLang = familyLanguages.first(where: { activeLangs.contains($0) }) ?? "Korean"
        }
    }

    // MARK: - Background
    private var background: some View {
        LinearGradient(
            colors: [
                Color(red: 0.99, green: 0.94, blue: 0.93),
                Color(red: 0.94, green: 0.96, blue: 1.00),
                Color(red: 0.97, green: 0.93, blue: 1.00)
            ],
            startPoint: .topLeading, endPoint: .bottomTrailing
        ).ignoresSafeArea()
    }

    // MARK: - Hero
    private var hero: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline) {
                Text("Trio").font(.system(size: 28, weight: .heavy, design: .rounded))
                    .foregroundColor(Color(red: 0.83, green: 0.32, blue: 0.45))
                Text(loc.t(.family))
                    .font(.system(size: 22, weight: .semibold, design: .rounded))
                    .foregroundColor(.primary.opacity(0.85))
                Spacer()
                deviceBadge
            }
            Text(loc.t(.heroSubtitle))
                .font(.footnote).foregroundColor(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 22, style: .continuous).fill(.white.opacity(0.78)))
    }

    private var deviceBadge: some View {
        HStack(spacing: 4) {
            Image(systemName: "wifi.slash").font(.caption2.weight(.bold))
            Text("on-device").font(.caption2.weight(.bold))
        }
        .padding(.horizontal, 8).padding(.vertical, 4)
        .background(Color(red: 0.30, green: 0.65, blue: 0.45).opacity(0.18))
        .foregroundColor(Color(red: 0.13, green: 0.50, blue: 0.32))
        .clipShape(Capsule())
    }

    // MARK: - Session router
    private var sessionRouter: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Label(loc.t(.whosUsing), systemImage: "person.crop.circle")
                    .font(.subheadline.weight(.semibold))
                    .foregroundColor(.secondary)
                Spacer()
            }
            HStack(spacing: 8) {
                ForEach(familyKids, id: \.name) { kid in
                    Button {
                        sessionKid = kid.name
                    } label: {
                        VStack(spacing: 2) {
                            Text(kid.name).font(.subheadline.weight(.bold))
                            Text(loc.ageLabel(kid.age)).font(.caption2)
                        }
                        .padding(.horizontal, 14).padding(.vertical, 8)
                        .background(sessionKid == kid.name
                                    ? Color.indigo.opacity(0.15) : Color.white)
                        .overlay(RoundedRectangle(cornerRadius: 14)
                            .stroke(sessionKid == kid.name ? Color.indigo : Color.black.opacity(0.1),
                                    lineWidth: 1.3))
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
                Spacer()
            }
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 6) {
                    Text(loc.t(.activeLanguages) + ":")
                        .font(.caption).foregroundColor(.secondary)
                    ForEach(familyLanguages, id: \.self) { lang in
                        let on = activeLangs.contains(lang)
                        Button {
                            if on { activeLangs.remove(lang) } else { activeLangs.insert(lang) }
                        } label: {
                            Text(loc.langName(lang))
                                .font(.caption.weight(.semibold))
                                .padding(.horizontal, 10).padding(.vertical, 6)
                                .background(on ? Color.indigo : Color.white)
                                .foregroundColor(on ? .white : .primary)
                                .overlay(Capsule().stroke(on ? .clear : Color.black.opacity(0.12), lineWidth: 1))
                                .clipShape(Capsule())
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
        .padding(14)
        .background(RoundedRectangle(cornerRadius: 18, style: .continuous).fill(.white.opacity(0.86)))
    }

    // MARK: - Mode chips (horizontal, compact)
    private var modeGrid: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(FamilyMode.allCases) { mode in
                    Button {
                        selectedMode = mode
                        userText = loc.placeholder(for: mode)
                    } label: {
                        ModeChip(mode: mode, selected: selectedMode == mode)
                    }.buttonStyle(.plain)
                }
            }
        }
    }

    // MARK: - Prompt card
    private var promptCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Label(loc.title(for: selectedMode), systemImage: selectedMode.icon)
                    .font(.subheadline.weight(.bold))
                    .foregroundColor(selectedMode.color)
                Spacer()
                Text(sessionKid)
                    .font(.caption.weight(.medium))
                    .foregroundColor(.secondary)
                Picker("age", selection: $targetAge) {
                    ForEach(0...12, id: \.self) { age in Text(loc.ageLabel(age)).tag(age) }
                }
                .pickerStyle(.menu).labelsHidden().font(.caption)
            }
            ZStack(alignment: .topLeading) {
                if userText.isEmpty {
                    Text(loc.placeholder(for: selectedMode))
                        .foregroundColor(.secondary.opacity(0.65))
                        .padding(.horizontal, 12).padding(.vertical, 10)
                }
                TextEditor(text: $userText)
                    .scrollContentBackground(.hidden)
                    .padding(.horizontal, 8).padding(.vertical, 4)
                    .frame(minHeight: 90)
            }
            .background(Color.white)
            .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.black.opacity(0.08), lineWidth: 1))
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))

            // Voice input is handled by the iOS keyboard's built-in dictation
            // mic key — tap the text box above, then the microphone key on
            // the keyboard. This is what every consumer iPad app uses and
            // bypasses all the audio-engine / SFSpeech failure modes.
            HStack(spacing: 6) {
                Image(systemName: "keyboard").font(.caption2).foregroundColor(.secondary)
                Text(loc.t(.dictateHint))
                    .font(.caption2).foregroundColor(.secondary)
                Spacer()
            }

            HStack(spacing: 8) {
                Button {
                    Task { await runGeneration() }
                } label: {
                    HStack(spacing: 6) {
                        if isGenerating { ProgressView().controlSize(.small) }
                        else { Image(systemName: "sparkles") }
                        Text(isGenerating ? generatingTitle : modeActionLabel)
                            .fontWeight(.semibold)
                    }
                    .frame(maxWidth: .infinity).padding(.vertical, 9)
                }
                .buttonStyle(.borderedProminent).tint(selectedMode.color)
                .disabled(isGenerating || userText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || !llamaState.isModelLoaded)

                Button {
                    Task {
                        await llamaState.clear()
                        lastReport = nil
                        generatedRaw = ""
                    }
                } label: {
                    Image(systemName: "arrow.counterclockwise")
                        .padding(.vertical, 9).padding(.horizontal, 12)
                }
                .buttonStyle(.bordered)
            }

        }
        .padding(14)
        .background(RoundedRectangle(cornerRadius: 18, style: .continuous).fill(.white.opacity(0.86)))
    }

    private func toggleRecording() {
        if speech.isRecording {
            speech.stop()
            return
        }
        // Use the language the parent explicitly picked in the chip row.
        // Falls back to the first active language if micLang got out of sync.
        let chosen = activeLangs.contains(micLang)
            ? micLang
            : (familyLanguages.first(where: { activeLangs.contains($0) }) ?? "Korean")
        speech.configure(locale: speechLocale(forLanguage: chosen))
        Task {
            if !speech.authorized {
                await speech.requestAuthorization()
            }
            do { try speech.start() }
            catch { speech.lastError = String(describing: error) }
        }
    }

    // MARK: - Gate dashboard
    private var gateDashboard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Label("Deployment gates", systemImage: "shield.lefthalf.filled")
                    .font(.subheadline.weight(.semibold))
                Spacer()
                if let band = lastReport?.band {
                    Text(band.rawValue.uppercased())
                        .font(.caption.weight(.heavy))
                        .padding(.horizontal, 9).padding(.vertical, 4)
                        .background(color(forBand: band).opacity(0.18))
                        .foregroundColor(color(forBand: band))
                        .clipShape(Capsule())
                }
            }
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible()),
                                GridItem(.flexible()), GridItem(.flexible()),
                                GridItem(.flexible())], spacing: 8) {
                gateBadge("G1·str",  lastReport?.g1Structure)
                gateBadge("G1·age",  lastReport?.g1Age)
                gateBadge("G2·script", lastReport?.g2Script)
                gateBadge("G3·schema", lastReport?.g3Schema)
                gateBadge("G4·route",  lastReport?.g4Routing)
            }
            if let issues = lastReport?.issues, !issues.isEmpty {
                VStack(alignment: .leading, spacing: 3) {
                    ForEach(issues, id: \.self) { issue in
                        Text("• \(issue)")
                            .font(.caption2).foregroundColor(.secondary)
                    }
                }
            }
        }
        .padding(14)
        .background(RoundedRectangle(cornerRadius: 18, style: .continuous).fill(.white.opacity(0.86)))
    }

    private func gateBadge(_ name: String, _ value: Double?) -> some View {
        let v = value ?? 0
        let band: GateBand = v >= 0.95 ? .green : (v >= 0.75 ? .amber : .red)
        return VStack(spacing: 2) {
            Text(name).font(.caption2.weight(.semibold)).foregroundColor(.secondary)
            Text(value == nil ? "—" : String(format: "%.0f%%", v*100))
                .font(.callout.weight(.bold))
                .foregroundColor(color(forBand: band))
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
        .background(color(forBand: band).opacity(0.12))
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
    }

    private func color(forBand b: GateBand) -> Color {
        switch b {
        case .green: return Color(red: 0.20, green: 0.62, blue: 0.40)
        case .amber: return Color(red: 0.78, green: 0.55, blue: 0.15)
        case .red:   return Color(red: 0.80, green: 0.25, blue: 0.30)
        }
    }

    // MARK: - Result card (parsed family card) — parent/child facing
    private func resultCard(_ card: FamilyCard) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            // Title row + age + verified pill (collapsible details)
            HStack(alignment: .firstTextBaseline) {
                Text(card.title.isEmpty ? loc.title(for: selectedMode) : card.title)
                    .font(.system(size: 22, weight: .heavy, design: .rounded))
                Spacer()
                if let band = lastReport?.band {
                    Button { showVerifyDetails.toggle() } label: {
                        HStack(spacing: 4) {
                            Image(systemName: badgeIcon(for: band))
                            Text(badgeLabel(for: band))
                                .font(.caption.weight(.bold))
                        }
                        .padding(.horizontal, 9).padding(.vertical, 5)
                        .background(color(forBand: band).opacity(0.14))
                        .foregroundColor(color(forBand: band))
                        .clipShape(Capsule())
                    }
                }
            }

            // Per-language paragraphs, big, warm
            VStack(alignment: .leading, spacing: 14) {
                ForEach(sortedLanguages(card), id: \.self) { lang in
                    if let body = card.body[lang] {
                        VStack(alignment: .leading, spacing: 6) {
                            HStack(spacing: 8) {
                                Text(langFlag(lang)).font(.title2)
                                Text(loc.langName(lang))
                                    .font(.caption.weight(.bold))
                                    .foregroundColor(selectedMode.color)
                                Button {
                                    tts.speak(body, language: lang)
                                } label: {
                                    Image(systemName: tts.speakingLang == lang
                                          ? "stop.circle.fill" : "play.circle.fill")
                                        .font(.system(size: 30))
                                        .foregroundColor(selectedMode.color)
                                }
                                .buttonStyle(.plain)
                                Spacer()
                            }
                            Text(body)
                                .font(.system(size: 17, design: .rounded))
                                .lineSpacing(3)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .textSelection(.enabled)
                        }
                    }
                }
            }

            // Play prompt callout
            if !card.play_prompt.isEmpty {
                HStack(alignment: .top, spacing: 10) {
                    Image(systemName: "sparkles")
                        .foregroundColor(selectedMode.color)
                    Text(card.play_prompt)
                        .font(.system(size: 15, design: .rounded).italic())
                        .foregroundColor(.primary.opacity(0.85))
                    Spacer()
                }
                .padding(12)
                .background(selectedMode.color.opacity(0.07))
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            }

            // Collapsible verify details (the EMNLP gates — hidden by default)
            if showVerifyDetails {
                verifyDetailsPanel
            }
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .fill(Color.white)
                .shadow(color: .black.opacity(0.05), radius: 14, x: 0, y: 6)
        )
    }

    private var verifyDetailsPanel: some View {
        VStack(alignment: .leading, spacing: 8) {
            Divider()
            HStack {
                Text("How we checked this answer")
                    .font(.caption.weight(.semibold))
                    .foregroundColor(.secondary)
                Spacer()
            }
            HStack(spacing: 6) {
                tinyGate("Structure", lastReport?.g1Structure)
                tinyGate("Age",       lastReport?.g1Age)
                tinyGate("Script",    lastReport?.g2Script)
                tinyGate("Schema",    lastReport?.g3Schema)
                tinyGate("Routing",   lastReport?.g4Routing)
            }
            if let issues = lastReport?.issues, !issues.isEmpty {
                ForEach(issues, id: \.self) { Text("· \($0)")
                    .font(.caption2)
                    .foregroundColor(.secondary)
                }
            }
        }
    }

    private func tinyGate(_ name: String, _ v: Double?) -> some View {
        let value = v ?? 0
        let c: Color = value >= 0.95 ? .green : (value >= 0.75 ? .orange : .red)
        return VStack(spacing: 1) {
            Text(name).font(.caption2.weight(.semibold)).foregroundColor(.secondary)
            Text(v == nil ? "—" : "\(Int(value*100))")
                .font(.caption.weight(.bold))
                .foregroundColor(c)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 5)
        .background(c.opacity(0.10))
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
    }

    private func badgeIcon(for b: GateBand) -> String {
        switch b {
        case .green: return "checkmark.seal.fill"
        case .amber: return "exclamationmark.triangle.fill"
        case .red:   return "xmark.seal.fill"
        }
    }
    private func badgeLabel(for b: GateBand) -> String {
        switch b {
        case .green: return "kid-safe"
        case .amber: return "review"
        case .red:   return "check"
        }
    }

    private func sortedLanguages(_ card: FamilyCard) -> [String] {
        // Show in family-language order (so parent always sees their language first).
        familyLanguages.filter { card.body[$0] != nil }
    }

    private func langFlag(_ s: String) -> String {
        switch s {
        case "Korean":   return "🇰🇷"
        case "English":  return "🇺🇸"
        case "Русский":  return "🇷🇺"
        case "Français": return "🇫🇷"
        case "中文":      return "🇨🇳"
        case "日本語":    return "🇯🇵"
        case "Tiếng Việt": return "🇻🇳"
        case "Español":   return "🇪🇸"
        case "Türkçe":    return "🇹🇷"
        case "Монгол":    return "🇲🇳"
        case "ภาษาไทย":   return "🇹🇭"
        default: return "🌐"
        }
    }

    private func langTag(_ s: String) -> String {
        switch s {
        case "Korean":  return "KO"
        case "English": return "EN"
        case "Русский": return "RU"
        case "Français":return "FR"
        case "中文":     return "ZH"
        case "日本語":   return "JA"
        default:        return String(s.prefix(2)).uppercased()
        }
    }

    // MARK: - Retry card (when the answer didn't come out cleanly)
    // Shown when the model returned natural language (e.g. a real bedtime
    // story) instead of the strict JSON schema. We display the story as-is —
    // refusing to show good content just because G3 schema failed was the
    // single worst UX bug. Gates are still recorded; the small badge surfaces
    // that the structure check didn't pass, without hiding the story.
    private var retryCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: selectedMode.icon)
                    .font(.title2).foregroundColor(selectedMode.color)
                VStack(alignment: .leading, spacing: 2) {
                    Text(storyTitle(from: generatedRaw) ?? loc.title(for: selectedMode))
                        .font(.headline)
                    Text("\(loc.t(.madeOnIPad)) · \(loc.ageLabel(targetAge))")
                        .font(.caption).foregroundColor(.secondary)
                }
                Spacer()
                Text(loc.t(.freeForm))
                    .font(.caption2.weight(.semibold))
                    .padding(.horizontal, 8).padding(.vertical, 3)
                    .background(Color.orange.opacity(0.18))
                    .foregroundColor(.orange)
                    .clipShape(Capsule())
            }

            ScrollView {
                Text(cleanedStory(generatedRaw))
                    .font(.body)
                    .lineSpacing(4)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .textSelection(.enabled)
            }
            .frame(maxHeight: 360)

            HStack {
                Button {
                    Task { await runGeneration() }
                } label: {
                    Label(loc.t(.makeAnother), systemImage: "sparkles")
                        .fontWeight(.semibold)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 9)
                }
                .buttonStyle(.borderedProminent)
                .tint(selectedMode.color)

                Button { showDebugRaw.toggle() } label: {
                    Image(systemName: showDebugRaw ? "eye.slash" : "eye")
                }
                .buttonStyle(.bordered)
            }
            if showDebugRaw {
                ScrollView {
                    Text(generatedRaw)
                        .font(.footnote.monospaced())
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .textSelection(.enabled)
                }
                .frame(maxHeight: 200)
                .padding(8)
                .background(Color.black.opacity(0.04))
                .clipShape(RoundedRectangle(cornerRadius: 10))
            }
        }
        .padding(16)
        .background(RoundedRectangle(cornerRadius: 20, style: .continuous)
            .fill(.white.opacity(0.92)))
    }

    // Strip Gemma 4 chat-template scaffolding and the LlamaState "Done" trailer
    // so the parent sees only the model's actual prose.
    private func cleanedStory(_ s: String) -> String {
        var t = s
        for marker in ["<|turn>", "<turn|>", "<bos>", "<eos>", "model\n", "user\n"] {
            t = t.replacingOccurrences(of: marker, with: "")
        }
        // Drop everything from the "Done" trailer onward.
        if let r = t.range(of: "\nDone") { t = String(t[..<r.lowerBound]) }
        return t.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    // Pull a "title" field out of partial/loose JSON if the model emitted one,
    // otherwise fall back to the first non-empty line.
    private func storyTitle(from raw: String) -> String? {
        if let m = raw.range(of: "\"title\"\\s*:\\s*\"([^\"]+)\"",
                             options: .regularExpression) {
            let chunk = raw[m]
            if let q1 = chunk.firstIndex(of: ":"),
               let v1 = chunk[q1...].firstIndex(of: "\""),
               let v2 = chunk[chunk.index(after: v1)...].firstIndex(of: "\"") {
                return String(chunk[chunk.index(after: v1)..<v2])
            }
        }
        let line = cleanedStory(raw)
            .split(separator: "\n", maxSplits: 1).first.map(String.init) ?? ""
        return line.isEmpty ? nil : String(line.prefix(80))
    }

    // MARK: - Generating hero (shows while LLM is producing tokens)
    private var generatingHero: some View {
        HStack(spacing: 14) {
            ProgressView().controlSize(.regular)
            VStack(alignment: .leading, spacing: 4) {
                Text(generatingTitle)
                    .font(.headline)
                Text("Made on this iPad. Nothing is sent to a server.")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            Spacer()
        }
        .padding(18)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 20, style: .continuous)
            .fill(.white.opacity(0.92)))
    }

    private var generatingTitle: String {
        switch selectedMode {
        case .story:   return loc.t(.makingStory)
        case .words:   return loc.t(.makingWords)
        case .song:    return loc.t(.makingSong)
        case .say:     return loc.t(.makingSay)
        case .between: return loc.t(.makingBetween)
        case .culture: return loc.t(.makingCulture)
        }
    }

    private var modeActionLabel: String {
        switch selectedMode {
        case .story:   return loc.t(.actStory)
        case .words:   return loc.t(.actWords)
        case .song:    return loc.t(.actSong)
        case .say:     return loc.t(.actSay)
        case .between: return loc.t(.actBetween)
        case .culture: return loc.t(.actCulture)
        }
    }

    // MARK: - Footer
    private var footer: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 6) {
                Image(systemName: "lock.shield.fill")
                    .foregroundColor(Color(red: 0.30, green: 0.55, blue: 0.40))
                Text(loc.t(.madeOnIPad))
                    .font(.caption.weight(.medium))
            }
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.black.opacity(0.04))
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }

    // MARK: - Generation
    @MainActor
    private func runGeneration() async {
        guard llamaState.isModelLoaded else {
            generatedRaw = "No model loaded yet.\n\nCopy gemma4_e2b_policy.Q4_K_M.gguf into the app's Documents folder, then relaunch — or open the Model drawer (top-right gear) and tap the file to load it."
            return
        }
        let activeList = familyLanguages.filter { activeLangs.contains($0) }
        let kidLine = familyKids.map { "\($0.name)(\($0.age))" }.joined(separator: ", ")

        // Slim system prompt — every extra token costs prefill time on iPad.
        // Schema is compact; if policy adapter is off we drop the rules entirely
        // to mimic the EMNLP no-policy curriculum.
        let bodyKeys = activeList.map { "\"\($0)\":\"…\"" }.joined(separator: ",")
        let langCSV  = activeList.joined(separator: ",")
        // Drop JSON. The model wastes tokens on scaffolding and truncates mid-
        // body. Block-tagged plain text is what every multilingual children's
        // app uses internally (Lingokids, Mondly Kids etc.) — easy to model,
        // trivial to parse.
        let langBlocks = activeList.map { "=== \($0) ===\n<short \($0) text here>" }.joined(separator: "\n\n")
        let prompt = """
        You are writing for a child age \(targetAge) in the \(selectedMode.rawValue) mode.
        Write THREE short blocks, one per language, separated by `=== <language> ===` headers.
        Each block must be 2–4 short sentences. Do not translate word-for-word; write naturally in each language.
        Languages: \(langCSV).

        Format exactly:
        \(langBlocks)

        Topic: \(userText)
        """

        // Wrap with the Gemma 4 chat template recorded in the GGUF metadata so
        // the policy/family LoRA actually engages (without this the engine
        // treats the prompt as raw text and silently regresses to baseline).
        let wrapped = GemmaChat.wrap(prompt)

        // Wipe messageLog so a stale "Done" from a prior run can't satisfy
        // pollUntilDone immediately. (KV cache + is_done are reset inside
        // LlamaContext.completion_init.)
        await llamaState.clear()

        // Record current messageLog length so we can extract this generation only.
        generationCheckpoint = llamaState.messageLog.count
        isGenerating = true
        lastReport = nil
        generatedRaw = ""

        await llamaState.complete(text: wrapped)
        // complete() detaches a streaming task; poll briefly until "Done" appears.
        try? await pollUntilDone()
        isGenerating = false

        let tail = String(llamaState.messageLog.dropFirst(generationCheckpoint + wrapped.count))
        generatedRaw = tail
        let strict = StateGates.evaluate(
            rawOutput: tail,
            activeLanguages: activeList,
            familyLanguages: familyLanguages,
            targetAge: targetAge
        )
        // New primary parser: split on `=== <language> ===` headers. Falls
        // back to soft JSON parsing then to free-text only if blocks aren't
        // found. This is the path the prompt is now optimized for.
        let displayCard =
            parseLanguageBlocks(from: tail,
                                activeLanguages: activeList,
                                targetAge: targetAge,
                                mode: selectedMode.rawValue)
            ?? strict.parsedCard
            ?? softParseCard(from: tail,
                             activeLanguages: activeList,
                             familyLanguages: familyLanguages,
                             targetAge: targetAge,
                             mode: selectedMode.rawValue)
        let report = GateReport(
            g1Structure: strict.g1Structure,
            g1Age:       strict.g1Age,
            g2Script:    strict.g2Script,
            g3Schema:    strict.g3Schema,
            g4Routing:   strict.g4Routing,
            band:        strict.band,
            issues:      strict.issues,
            parsedCard:  displayCard
        )
        lastReport = report
        if let card = displayCard {
            library.add(card: card)
            words.ingest(card: card)
        }
        let entry = AuditEntry(
            timestamp: Date(),
            mode: selectedMode.rawValue,
            promptDigest: String(userText.prefix(200)),
            activeLanguages: activeList,
            targetAge: targetAge,
            g1Structure: report.g1Structure,
            g1Age:       report.g1Age,
            g2Script:    report.g2Script,
            g3Schema:    report.g3Schema,
            g4Routing:   report.g4Routing,
            band:        report.band.rawValue,
            issues:      report.issues,
            adapterTag:  policyAdapterOn ? "policy_family_seed10" : "no_policy_demo"
        )
        audit.append(entry)
    }

    /// Polls `messageLog` for the trailing "Done" marker emitted by LlamaState
    /// when its detached streaming task finishes.  Cheap — no internal API
    /// changes — and matches the existing LlamaState behavior.
    private func pollUntilDone(timeout: TimeInterval = 120) async throws {
        let start = Date()
        // LlamaState emits "\nDone\n" after the streaming task terminates.
        // We accept any "Done" line, leading-spaces tolerant.
        while Date().timeIntervalSince(start) < timeout {
            let log = llamaState.messageLog
            if log.range(of: "\\n\\s*Done\\s*\\n",
                         options: .regularExpression) != nil {
                return
            }
            try await Task.sleep(nanoseconds: 250_000_000)
        }
    }

    // Banner that appears in Today when a Visitor mode is selected (e.g.
    // grandmother is over for dinner — we surface RU and reorder cards).
    @ViewBuilder private var visitorBanner: some View {
        HStack(spacing: 10) {
            Image(systemName: "person.crop.circle.badge.plus")
                .foregroundColor(.indigo)
            VStack(alignment: .leading, spacing: 1) {
                Text(visitorMode.title(loc)).font(.subheadline.weight(.bold))
                Text(visitorMode.subtitle(loc)).font(.caption).foregroundColor(.secondary)
            }
            Spacer()
            Button(loc.t(.end)) { visitorMode = .none }
                .buttonStyle(.bordered).controlSize(.small)
        }
        .padding(12)
        .background(Color.indigo.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }
}

// =============================================================================
//  UI language (chrome localization) — keys and translations for the four
//  family-target locales. Changing this does NOT change the generated content
//  language; that's controlled by activeLangs. Affects buttons, tabs, hints.
// =============================================================================
enum LocKey: String, CaseIterable, Hashable {
    case today, library, phrasebook, words, camera, family
    case heroSubtitle, dictateHint, tapWord, takePhoto
    case visitorMode, whosHere, activeLanguages
    case visitorNone, visitorGrandmother, visitorAunt, visitorDad, visitorMom
    case grandmotherDesc, auntDesc, dadDesc, momDesc
    case editFamily, modelLabel, historyLabel, safetyMode, system
    case nothingSavedYet, savedHint, noWordsYet, wordsAutoHint
    case wordWallTitle
    case morning, meal, bath, play, bedtime, praise, apology, greeting
    case actStory, actWords, actSong, actSay, actBetween, actCulture
    case tStory, tWords, tSong, tSay, tBetween, tCulture
    case makingStory, makingWords, makingSong, makingSay, makingBetween, makingCulture
    case end, uiLanguage
    case modelMissing, askKid, askKidHint
    case familyLangsSection, child1, child2, nameLabel, ageStepper, addSecondChild, done, save
    case whosUsing, freeForm, makeAnother, madeOnIPad
    case allFilter, voiceSection, voicePickerHint, autoVoice
    case translate, translateHint, translateButton, translating, translateClear
}

final class Localization: ObservableObject {
    @AppStorage("ui.lang") var lang: String = "ko" {
        didSet { objectWillChange.send() }
    }
    static let supported: [(code: String, label: String, flag: String)] = [
        ("ko", "한국어",   "🇰🇷"),
        ("en", "English",  "🇺🇸"),
        ("ru", "Русский",  "🇷🇺"),
        ("fr", "Français", "🇫🇷"),
    ]
    func t(_ key: LocKey) -> String {
        return Self.dict[lang]?[key] ?? Self.dict["en"]?[key] ?? key.rawValue
    }
    func ageLabel(_ n: Int) -> String {
        switch lang {
        case "ko": return "\(n)세"
        case "ru": return "\(n) лет"
        case "fr": return "\(n) ans"
        default:   return "Age \(n)"
        }
    }
    // Localized display name for a family language identifier. The identifier
    // itself ("Korean", "English", "Русский", "Français") is the canonical key
    // the model uses for body lookup — we must NOT change the identifier, only
    // how we present it to the parent.
    func langName(_ key: String) -> String {
        switch (lang, key) {
        case ("ko", "Korean"):  return "한국어"
        case ("ko", "English"): return "영어"
        case ("ko", "Русский"): return "러시아어"
        case ("ko", "Français"):return "프랑스어"
        case ("ko", "中文"):    return "중국어"
        case ("ko", "日本語"):  return "일본어"
        case ("ko", "Tiếng Việt"): return "베트남어"
        case ("ko", "Español"): return "스페인어"
        case ("ko", "Türkçe"):  return "튀르키예어"
        case ("ko", "Монгол"):  return "몽골어"
        case ("ko", "ภาษาไทย"): return "태국어"

        case ("en", "Korean"):  return "Korean"
        case ("en", "English"): return "English"
        case ("en", "Русский"): return "Russian"
        case ("en", "Français"):return "French"
        case ("en", "中文"):    return "Chinese"
        case ("en", "日本語"):  return "Japanese"
        case ("en", "Tiếng Việt"): return "Vietnamese"
        case ("en", "Español"): return "Spanish"
        case ("en", "Türkçe"):  return "Turkish"
        case ("en", "Монгол"):  return "Mongolian"
        case ("en", "ภาษาไทย"): return "Thai"

        case ("ru", "Korean"):  return "Корейский"
        case ("ru", "English"): return "Английский"
        case ("ru", "Русский"): return "Русский"
        case ("ru", "Français"):return "Французский"
        case ("ru", "中文"):    return "Китайский"
        case ("ru", "日本語"):  return "Японский"
        case ("ru", "Tiếng Việt"): return "Вьетнамский"
        case ("ru", "Español"): return "Испанский"
        case ("ru", "Türkçe"):  return "Турецкий"
        case ("ru", "Монгол"):  return "Монгольский"
        case ("ru", "ภาษาไทย"): return "Тайский"

        case ("fr", "Korean"):  return "Coréen"
        case ("fr", "English"): return "Anglais"
        case ("fr", "Русский"): return "Russe"
        case ("fr", "Français"):return "Français"
        case ("fr", "中文"):    return "Chinois"
        case ("fr", "日本語"):  return "Japonais"
        case ("fr", "Tiếng Việt"): return "Vietnamien"
        case ("fr", "Español"): return "Espagnol"
        case ("fr", "Türkçe"):  return "Turc"
        case ("fr", "Монгол"):  return "Mongol"
        case ("fr", "ภาษาไทย"): return "Thaï"

        default: return key
        }
    }
    // Short mode title (used on chips & headers).
    func title(for mode: FamilyMode) -> String {
        switch mode {
        case .story:   return t(.tStory)
        case .words:   return t(.tWords)
        case .song:    return t(.tSong)
        case .say:     return t(.tSay)
        case .between: return t(.tBetween)
        case .culture: return t(.tCulture)
        }
    }
    // Mode-specific placeholders for the prompt text box.
    func placeholder(for mode: FamilyMode) -> String {
        switch (lang, mode) {
        case ("ko", .story):   return "잠 안 자려는 토끼와 별 친구 이야기"
        case ("ko", .words):   return "오늘 산책에서 본 빨간 단풍잎"
        case ("ko", .song):    return "양치 시간을 즐겁게 만드는 짧은 노래"
        case ("ko", .say):     return "이제 놀이 그만, 손 씻으러 가자 — 부드럽게"
        case ("ko", .between): return "러시아어 쓰는 할머니께 낮잠 시간 안내"
        case ("ko", .culture): return "추석에 송편을 만드는 이유를 아이 눈높이로"

        case ("en", .story):   return "A bunny who won't sleep and a friendly star"
        case ("en", .words):   return "A red maple leaf we saw on today's walk"
        case ("en", .song):    return "A tiny song that makes tooth-brushing fun"
        case ("en", .say):     return "Time to stop playing and wash hands — gently"
        case ("en", .between): return "A note to a Russian-speaking grandma about nap time"
        case ("en", .culture): return "Why we make songpyeon on Chuseok, at a child's level"

        case ("ru", .story):   return "Зайчик, который не хочет спать, и звёздочка-друг"
        case ("ru", .words):   return "Красный кленовый лист с сегодняшней прогулки"
        case ("ru", .song):    return "Короткая песенка, чтобы чистить зубки было весело"
        case ("ru", .say):     return "Пора заканчивать игру и мыть ручки — мягко"
        case ("ru", .between): return "Записка корейской бабушке про дневной сон"
        case ("ru", .culture): return "Почему на Чусок делают сонпхён — простыми словами"

        case ("fr", .story):   return "Un lapin qui ne veut pas dormir et une étoile amie"
        case ("fr", .words):   return "La feuille d'érable rouge vue à la promenade"
        case ("fr", .song):    return "Une petite chanson pour rendre le brossage rigolo"
        case ("fr", .say):     return "Fini de jouer, on lave les mains — doucement"
        case ("fr", .between): return "Un mot à la grand-mère coréenne sur la sieste"
        case ("fr", .culture): return "Pourquoi on fait du songpyeon à Chuseok, pour un enfant"
        default: return ""
        }
    }
    private static let dict: [String: [LocKey: String]] = [
        "ko": [
            .today:"오늘", .library:"보관함", .phrasebook:"회화집",
            .words:"단어", .camera:"카메라", .family:"가족",
            .heroSubtitle:"세 가지 언어, 한 가족 — 순간을 골라 함께 만들어요.",
            .dictateHint:"입력창을 탭한 다음 키보드의 🎙 키를 눌러 받아쓰세요.",
            .tapWord:"단어를 탭하세요:",
            .takePhoto:"사진 찍기",
            .visitorMode:"방문자 모드", .whosHere:"누가 와 있나요",
            .activeLanguages:"사용 중인 언어",
            .visitorNone:"없음",
            .visitorGrandmother:"할머니가 오셨어요",
            .visitorAunt:"이모가 방문 중",
            .visitorDad:"아빠 시간",
            .visitorMom:"엄마 시간",
            .grandmotherDesc:"러시아어 우선, 한국어 자막.",
            .auntDesc:"할머니와 동일 — 러시아어 위주.",
            .dadDesc:"한국어 우선, 영어 보조.",
            .momDesc:"러시아어 우선, 영어 보조.",
            .editFamily:"가족 · 자녀 편집",
            .modelLabel:"모델", .historyLabel:"히스토리",
            .safetyMode:"안전 모드", .system:"시스템",
            .nothingSavedYet:"아직 저장된 것이 없어요",
            .savedHint:"오늘 탭에서 생성한 카드를 만들면 여기에 자동 저장돼요.",
            .noWordsYet:"아직 단어가 없어요",
            .wordsAutoHint:"이야기를 만들 때마다 단어가 자동으로 쌓여요.",
            .wordWallTitle:"단어 벽",
            .morning:"아침", .meal:"식사", .bath:"목욕", .play:"놀이",
            .bedtime:"잠자리", .praise:"칭찬", .apology:"사과", .greeting:"인사",
            .actStory:"이야기 만들기", .actWords:"단어 카드", .actSong:"노래 짓기",
            .actSay:"표현 알려줘", .actBetween:"가족 메모", .actCulture:"오늘의 문화",
            .makingStory:"이야기 만드는 중…", .makingWords:"단어 카드 그리는 중…",
            .makingSong:"노래 작곡 중…", .makingSay:"적절한 말 고르는 중…",
            .makingBetween:"메모 쓰는 중…", .makingCulture:"오늘의 순간 고르는 중…",
            .end:"종료", .uiLanguage:"화면 언어",
            .modelMissing:"모델이 로드되지 않았어요",
            .askKid:"오늘 어떤 이야기를 만들까요?",
            .askKidHint:"예: 자기 싫어하는 토끼와 별 친구",
            .tStory:"잠자리 이야기", .tWords:"단어 카드", .tSong:"짧은 노래",
            .tSay:"부모 말투로", .tBetween:"가족 메모", .tCulture:"오늘의 문화",
            .familyLangsSection:"가족 언어 (여러 개 선택)",
            .child1:"자녀 1", .child2:"자녀 2", .nameLabel:"이름",
            .ageStepper:"나이", .addSecondChild:"둘째 추가",
            .done:"완료", .save:"저장",
            .whosUsing:"누가 쓰고 있어요", .freeForm:"자유 형식",
            .makeAnother:"하나 더 만들기",
            .madeOnIPad:"이 아이패드에서 만들었어요. 서버로 전송되지 않아요.",
            .allFilter:"전체", .voiceSection:"음성 (TTS)",
            .voicePickerHint:"각 언어마다 설치된 음성을 골라요. Siri/Premium이 가장 자연스러워요.",
            .autoVoice:"자동 (최고 품질)",
            .translate:"번역",
            .translateHint:"어떤 언어로 적어도 돼요. 활성화된 3개 언어로 번역하고 짧은 설명도 같이 줘요.",
            .translateButton:"번역하기",
            .translating:"번역 중…",
            .translateClear:"지우기",
        ],
        "en": [
            .today:"Today", .library:"Library", .phrasebook:"Phrasebook",
            .words:"Words", .camera:"Camera", .family:"Family",
            .heroSubtitle:"Three languages, one family — pick a moment and we'll make it together.",
            .dictateHint:"Tap the text box, then press 🎙 on the keyboard to dictate.",
            .tapWord:"Tap a word:",
            .takePhoto:"Take photo",
            .visitorMode:"Visitor mode", .whosHere:"Who's here",
            .activeLanguages:"Active languages",
            .visitorNone:"None",
            .visitorGrandmother:"Grandmother is here",
            .visitorAunt:"Aunt is visiting",
            .visitorDad:"Dad time",
            .visitorMom:"Mom time",
            .grandmotherDesc:"Russian first, Korean caption underneath.",
            .auntDesc:"Same as grandmother — Russian-led.",
            .dadDesc:"Korean primary, English secondary.",
            .momDesc:"Russian primary, English secondary.",
            .editFamily:"Edit family & kids",
            .modelLabel:"Model", .historyLabel:"History",
            .safetyMode:"Safety mode", .system:"System",
            .nothingSavedYet:"Nothing saved yet",
            .savedHint:"Generated cards from Today are saved here automatically.",
            .noWordsYet:"No words yet",
            .wordsAutoHint:"Words are added automatically each time you make a story.",
            .wordWallTitle:"Word Wall",
            .morning:"Morning", .meal:"Meal", .bath:"Bath", .play:"Play",
            .bedtime:"Bedtime", .praise:"Praise", .apology:"Apology", .greeting:"Greeting",
            .actStory:"Make a story", .actWords:"Word card", .actSong:"Make a song",
            .actSay:"Say it", .actBetween:"Family note", .actCulture:"Today's culture",
            .makingStory:"Making your story…", .makingWords:"Drawing word cards…",
            .makingSong:"Composing a tiny song…", .makingSay:"Finding the words…",
            .makingBetween:"Writing a quick note…", .makingCulture:"Picking today's moment…",
            .end:"End", .uiLanguage:"App language",
            .modelMissing:"No model loaded yet",
            .askKid:"What shall we make today?",
            .askKidHint:"e.g. a rabbit who won't sleep and a star friend",
            .tStory:"Bedtime story", .tWords:"Word card", .tSong:"Tiny song",
            .tSay:"Say it kindly", .tBetween:"Family note", .tCulture:"Today's culture",
            .familyLangsSection:"Family languages (multi-select)",
            .child1:"Child 1", .child2:"Child 2", .nameLabel:"Name",
            .ageStepper:"Age", .addSecondChild:"Add second child",
            .done:"Done", .save:"Save",
            .whosUsing:"Who's using this", .freeForm:"free form",
            .makeAnother:"Make another",
            .madeOnIPad:"Made on this iPad. Nothing is sent to a server.",
            .allFilter:"All", .voiceSection:"Voice (TTS)",
            .voicePickerHint:"Choose an installed voice per language. Siri/Premium sound most natural.",
            .autoVoice:"Auto (best available)",
            .translate:"Translate",
            .translateHint:"Type in any language. We render it in all three active languages with a short note.",
            .translateButton:"Translate",
            .translating:"Translating…",
            .translateClear:"Clear",
        ],
        "ru": [
            .today:"Сегодня", .library:"Библиотека", .phrasebook:"Разговорник",
            .words:"Слова", .camera:"Камера", .family:"Семья",
            .heroSubtitle:"Три языка, одна семья — выберите момент, и мы создадим его вместе.",
            .dictateHint:"Коснитесь поля, затем нажмите 🎙 на клавиатуре для диктовки.",
            .tapWord:"Коснитесь слова:",
            .takePhoto:"Сделать фото",
            .visitorMode:"Режим гостя", .whosHere:"Кто пришёл",
            .activeLanguages:"Активные языки",
            .visitorNone:"Нет",
            .visitorGrandmother:"Пришла бабушка",
            .visitorAunt:"Тётя в гостях",
            .visitorDad:"Время с папой",
            .visitorMom:"Время с мамой",
            .grandmotherDesc:"Сначала русский, корейский — подпись.",
            .auntDesc:"Так же, как с бабушкой — русский ведущий.",
            .dadDesc:"Корейский основной, английский — вспомогательный.",
            .momDesc:"Русский основной, английский — вспомогательный.",
            .editFamily:"Изменить семью и детей",
            .modelLabel:"Модель", .historyLabel:"История",
            .safetyMode:"Режим безопасности", .system:"Система",
            .nothingSavedYet:"Пока ничего не сохранено",
            .savedHint:"Карточки из «Сегодня» сохраняются здесь автоматически.",
            .noWordsYet:"Пока нет слов",
            .wordsAutoHint:"Слова добавляются автоматически с каждой историей.",
            .wordWallTitle:"Стена слов",
            .morning:"Утро", .meal:"Еда", .bath:"Купание", .play:"Игра",
            .bedtime:"Сон", .praise:"Похвала", .apology:"Извинение", .greeting:"Приветствие",
            .actStory:"Сочинить историю", .actWords:"Карточка слов", .actSong:"Сочинить песенку",
            .actSay:"Как сказать", .actBetween:"Семейная записка", .actCulture:"Культура дня",
            .makingStory:"Сочиняем историю…", .makingWords:"Рисуем карточки…",
            .makingSong:"Сочиняем песенку…", .makingSay:"Подбираем слова…",
            .makingBetween:"Пишем записку…", .makingCulture:"Выбираем момент дня…",
            .end:"Закончить", .uiLanguage:"Язык приложения",
            .modelMissing:"Модель ещё не загружена",
            .askKid:"Что сегодня создадим?",
            .askKidHint:"например: зайчик, который не хочет спать, и звёздочка-подружка",
            .tStory:"Сказка на ночь", .tWords:"Карточка слов", .tSong:"Песенка",
            .tSay:"Скажи мягко", .tBetween:"Семейная записка", .tCulture:"Культура дня",
            .familyLangsSection:"Языки семьи (несколько)",
            .child1:"Ребёнок 1", .child2:"Ребёнок 2", .nameLabel:"Имя",
            .ageStepper:"Возраст", .addSecondChild:"Добавить второго",
            .done:"Готово", .save:"Сохранить",
            .whosUsing:"Кто пользуется", .freeForm:"свободная форма",
            .makeAnother:"Сделать ещё",
            .madeOnIPad:"Создано на этом iPad. Ничего не отправляется на сервер.",
            .allFilter:"Все", .voiceSection:"Голос (TTS)",
            .voicePickerHint:"Выберите голос для каждого языка. Siri/Premium звучат естественнее.",
            .autoVoice:"Авто (лучший доступный)",
            .translate:"Перевод",
            .translateHint:"Можно писать на любом языке. Покажем перевод на все три активных языка с короткой заметкой.",
            .translateButton:"Перевести",
            .translating:"Переводим…",
            .translateClear:"Очистить",
        ],
        "fr": [
            .today:"Aujourd'hui", .library:"Bibliothèque", .phrasebook:"Phrases",
            .words:"Mots", .camera:"Caméra", .family:"Famille",
            .heroSubtitle:"Trois langues, une famille — choisis un moment, on le crée ensemble.",
            .dictateHint:"Touchez le champ, puis appuyez sur 🎙 du clavier pour dicter.",
            .tapWord:"Tapez un mot :",
            .takePhoto:"Prendre une photo",
            .visitorMode:"Mode visiteur", .whosHere:"Qui est là",
            .activeLanguages:"Langues actives",
            .visitorNone:"Aucun",
            .visitorGrandmother:"Mamie est là",
            .visitorAunt:"Tatie en visite",
            .visitorDad:"Temps papa",
            .visitorMom:"Temps maman",
            .grandmotherDesc:"Russe d'abord, sous-titre coréen.",
            .auntDesc:"Comme mamie — russe en tête.",
            .dadDesc:"Coréen principal, anglais secondaire.",
            .momDesc:"Russe principal, anglais secondaire.",
            .editFamily:"Modifier famille et enfants",
            .modelLabel:"Modèle", .historyLabel:"Historique",
            .safetyMode:"Mode sécurité", .system:"Système",
            .nothingSavedYet:"Rien d'enregistré pour l'instant",
            .savedHint:"Les cartes générées dans Aujourd'hui sont enregistrées ici.",
            .noWordsYet:"Aucun mot pour l'instant",
            .wordsAutoHint:"Les mots s'ajoutent à chaque histoire.",
            .wordWallTitle:"Mur de mots",
            .morning:"Matin", .meal:"Repas", .bath:"Bain", .play:"Jeu",
            .bedtime:"Coucher", .praise:"Encouragement", .apology:"Excuse", .greeting:"Salutation",
            .actStory:"Faire une histoire", .actWords:"Carte de mots", .actSong:"Faire une chanson",
            .actSay:"Comment dire", .actBetween:"Note familiale", .actCulture:"Culture du jour",
            .makingStory:"On crée l'histoire…", .makingWords:"On dessine les cartes…",
            .makingSong:"On compose…", .makingSay:"On trouve les mots…",
            .makingBetween:"On écrit la note…", .makingCulture:"On choisit le moment…",
            .end:"Terminer", .uiLanguage:"Langue de l'app",
            .modelMissing:"Modèle non chargé",
            .askKid:"Qu'est-ce qu'on crée aujourd'hui ?",
            .askKidHint:"ex : un lapin qui ne veut pas dormir et son ami l'étoile",
            .tStory:"Histoire du soir", .tWords:"Carte de mots", .tSong:"Petite chanson",
            .tSay:"Dis-le doucement", .tBetween:"Note famille", .tCulture:"Culture du jour",
            .familyLangsSection:"Langues de la famille (plusieurs)",
            .child1:"Enfant 1", .child2:"Enfant 2", .nameLabel:"Prénom",
            .ageStepper:"Âge", .addSecondChild:"Ajouter un second enfant",
            .done:"OK", .save:"Enregistrer",
            .whosUsing:"Qui utilise", .freeForm:"forme libre",
            .makeAnother:"En faire un autre",
            .madeOnIPad:"Créé sur cet iPad. Rien n'est envoyé au serveur.",
            .allFilter:"Tout", .voiceSection:"Voix (TTS)",
            .voicePickerHint:"Choisissez une voix par langue. Siri/Premium sonnent le plus naturel.",
            .autoVoice:"Auto (meilleure dispo)",
            .translate:"Traduire",
            .translateHint:"Écrivez dans n'importe quelle langue. On rend les trois langues actives avec une petite note.",
            .translateButton:"Traduire",
            .translating:"Traduction…",
            .translateClear:"Effacer",
        ],
    ]
}

// =============================================================================
//  Tab + Visitor enums
// =============================================================================
enum AppTab: Hashable { case today, library, phrasebook, translate, words, camera, family }

enum VisitorMode: String, CaseIterable, Identifiable {
    case none, grandmother, aunt, dadOnly, momOnly
    var id: String { rawValue }
    func title(_ loc: Localization) -> String {
        switch self {
        case .none:        return loc.t(.visitorNone)
        case .grandmother: return loc.t(.visitorGrandmother)
        case .aunt:        return loc.t(.visitorAunt)
        case .dadOnly:     return loc.t(.visitorDad)
        case .momOnly:     return loc.t(.visitorMom)
        }
    }
    func subtitle(_ loc: Localization) -> String {
        switch self {
        case .none:        return ""
        case .grandmother: return loc.t(.grandmotherDesc)
        case .aunt:        return loc.t(.auntDesc)
        case .dadOnly:     return loc.t(.dadDesc)
        case .momOnly:     return loc.t(.momDesc)
        }
    }
}

// =============================================================================
//  Library — saved generations
// =============================================================================
struct LibraryItem: Codable, Identifiable {
    let id: UUID
    let savedAt: Date
    let mode: String
    let title: String
    let body: [String: String]
    let activeLanguages: [String]
    let targetAge: Int
}

@MainActor
final class LibraryStore: ObservableObject {
    @Published var items: [LibraryItem] = []
    private let key = "library.items.v1"
    init() { load() }
    func add(card: FamilyCard) {
        let item = LibraryItem(id: UUID(), savedAt: Date(),
                               mode: card.mode, title: card.title,
                               body: card.body,
                               activeLanguages: card.active_languages,
                               targetAge: card.target_age)
        items.insert(item, at: 0)
        save()
    }
    func remove(_ item: LibraryItem) {
        items.removeAll { $0.id == item.id }
        save()
    }
    private func save() {
        if let data = try? JSONEncoder().encode(items) {
            UserDefaults.standard.set(data, forKey: key)
        }
    }
    private func load() {
        guard let data = UserDefaults.standard.data(forKey: key),
              let arr = try? JSONDecoder().decode([LibraryItem].self, from: data)
        else { return }
        items = arr
    }
}

// =============================================================================
//  Word Wall — auto-extracted single words / short phrases
// =============================================================================
struct WordItem: Codable, Identifiable, Hashable {
    let id: UUID
    let language: String
    let text: String
    let context: String   // sentence this came from
    let addedAt: Date
}

@MainActor
final class WordStore: ObservableObject {
    @Published var items: [WordItem] = []
    private let key = "words.items.v1"
    init() { load() }
    func ingest(card: FamilyCard) {
        for (lang, body) in card.body {
            let tokens = body
                .components(separatedBy: CharacterSet.whitespacesAndNewlines.union(.punctuationCharacters))
                .filter { $0.count >= 2 && $0.count <= 12 }
            // Take a few salient tokens per body (first 3).
            for token in tokens.prefix(3) {
                if items.contains(where: { $0.language == lang && $0.text == token }) { continue }
                items.insert(WordItem(id: UUID(), language: lang, text: token,
                                      context: body, addedAt: Date()), at: 0)
            }
        }
        save()
    }
    func remove(_ item: WordItem) {
        items.removeAll { $0.id == item.id }
        save()
    }
    private func save() {
        if let data = try? JSONEncoder().encode(items) {
            UserDefaults.standard.set(data, forKey: key)
        }
    }
    private func load() {
        guard let data = UserDefaults.standard.data(forKey: key),
              let arr = try? JSONDecoder().decode([WordItem].self, from: data)
        else { return }
        items = arr
    }
}

// =============================================================================
//  Phrasebook — pre-curated daily phrases (KO / EN / RU / FR)
// =============================================================================
struct Phrase: Identifiable, Hashable {
    let id = UUID()
    let category: String
    let translations: [String: String]   // language → text
}

enum Phrasebook {
    static let categories = ["Morning", "Meal", "Bath", "Play", "Bedtime",
                             "Praise", "Apology", "Greeting"]
    static let phrases: [Phrase] = [
        // ───────────────── Morning
        .init(category: "Morning", translations: [
            "Korean":"잘 잤어?", "English":"Did you sleep well?",
            "Русский":"Хорошо спал(а)?", "Français":"Tu as bien dormi ?"
        ]),
        .init(category: "Morning", translations: [
            "Korean":"이 닦자.", "English":"Let's brush our teeth.",
            "Русский":"Почистим зубки.", "Français":"On se brosse les dents."
        ]),
        .init(category: "Morning", translations: [
            "Korean":"옷 입자.", "English":"Let's get dressed.",
            "Русский":"Давай оденемся.", "Français":"On s'habille."
        ]),
        // ───────────────── Meal
        .init(category: "Meal", translations: [
            "Korean":"맛있게 먹어.", "English":"Enjoy your meal.",
            "Русский":"Приятного аппетита.", "Français":"Bon appétit."
        ]),
        .init(category: "Meal", translations: [
            "Korean":"한 입만 더.", "English":"One more bite.",
            "Русский":"Ещё кусочек.", "Français":"Encore une bouchée."
        ]),
        .init(category: "Meal", translations: [
            "Korean":"물 마실래?", "English":"Want some water?",
            "Русский":"Хочешь водички?", "Français":"Tu veux de l'eau ?"
        ]),
        // ───────────────── Bath
        .init(category: "Bath", translations: [
            "Korean":"목욕할 시간이야.", "English":"It's bath time.",
            "Русский":"Пора купаться.", "Français":"C'est l'heure du bain."
        ]),
        .init(category: "Bath", translations: [
            "Korean":"따뜻해?", "English":"Is it warm?",
            "Русский":"Тёплая?", "Français":"C'est chaud ?"
        ]),
        // ───────────────── Play
        .init(category: "Play", translations: [
            "Korean":"같이 놀자.", "English":"Let's play together.",
            "Русский":"Давай играть вместе.", "Français":"On joue ensemble."
        ]),
        .init(category: "Play", translations: [
            "Korean":"네 차례야.", "English":"Your turn.",
            "Русский":"Твоя очередь.", "Français":"À ton tour."
        ]),
        .init(category: "Play", translations: [
            "Korean":"정리하자.", "English":"Let's clean up.",
            "Русский":"Давай уберём.", "Français":"On range."
        ]),
        // ───────────────── Bedtime
        .init(category: "Bedtime", translations: [
            "Korean":"잘 자.", "English":"Good night.",
            "Русский":"Спокойной ночи.", "Français":"Bonne nuit."
        ]),
        .init(category: "Bedtime", translations: [
            "Korean":"불 끌게.", "English":"I'll turn off the light.",
            "Русский":"Я выключу свет.", "Français":"J'éteins la lumière."
        ]),
        .init(category: "Bedtime", translations: [
            "Korean":"꿈에서 만나자.", "English":"See you in dreams.",
            "Русский":"Увидимся во сне.", "Français":"On se voit dans les rêves."
        ]),
        // ───────────────── Praise
        .init(category: "Praise", translations: [
            "Korean":"잘했어!", "English":"Well done!",
            "Русский":"Молодец!", "Français":"Bravo !"
        ]),
        .init(category: "Praise", translations: [
            "Korean":"너무 멋지다.", "English":"You're amazing.",
            "Русский":"Ты потрясающий(ая).", "Français":"Tu es génial(e)."
        ]),
        // ───────────────── Apology
        .init(category: "Apology", translations: [
            "Korean":"미안해.", "English":"I'm sorry.",
            "Русский":"Прости.", "Français":"Pardon."
        ]),
        .init(category: "Apology", translations: [
            "Korean":"괜찮아?", "English":"Are you okay?",
            "Русский":"Ты в порядке?", "Français":"Ça va ?"
        ]),
        // ───────────────── Greeting
        .init(category: "Greeting", translations: [
            "Korean":"안녕하세요.", "English":"Hello.",
            "Русский":"Здравствуйте.", "Français":"Bonjour."
        ]),
        .init(category: "Greeting", translations: [
            "Korean":"할머니, 보고 싶었어요.", "English":"Grandma, I missed you.",
            "Русский":"Бабушка, я скучал(а).", "Français":"Mamie, tu m'as manqué."
        ]),
        .init(category: "Greeting", translations: [
            "Korean":"감사합니다.", "English":"Thank you.",
            "Русский":"Спасибо.", "Français":"Merci."
        ]),
    ]
}

// =============================================================================
//  Library tab
// =============================================================================
struct LibraryTab: View {
    @ObservedObject var store: LibraryStore
    @ObservedObject var tts: FamilyTTS
    @EnvironmentObject var loc: Localization
    var body: some View {
        NavigationStack {
            Group {
                if store.items.isEmpty {
                    ContentUnavailableView(loc.t(.nothingSavedYet),
                        systemImage: "books.vertical",
                        description: Text(loc.t(.savedHint)))
                } else {
                    List {
                        ForEach(store.items) { item in
                            LibraryRow(item: item, tts: tts)
                        }
                        .onDelete { idx in
                            for i in idx { store.remove(store.items[i]) }
                        }
                    }
                }
            }
            .navigationTitle(loc.t(.library))
        }
    }
}

private struct LibraryRow: View {
    let item: LibraryItem
    @ObservedObject var tts: FamilyTTS
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(item.title.isEmpty ? item.mode.capitalized : item.title)
                    .font(.headline)
                Spacer()
                Text(item.savedAt, style: .date)
                    .font(.caption2).foregroundColor(.secondary)
            }
            ForEach(item.activeLanguages.filter { item.body[$0] != nil }, id: \.self) { lang in
                HStack(alignment: .top, spacing: 10) {
                    Text(flagFor(lang)).font(.title3)
                    Button {
                        tts.speak(item.body[lang] ?? "", language: lang)
                    } label: {
                        Image(systemName: tts.speakingLang == lang
                              ? "stop.circle.fill" : "play.circle.fill")
                            .font(.system(size: 28))
                            .foregroundColor(.indigo)
                    }
                    .buttonStyle(.plain)
                    Text(item.body[lang] ?? "")
                        .font(.callout)
                    Spacer()
                }
            }
        }
        .padding(.vertical, 4)
    }
}

private func flagFor(_ s: String) -> String {
    switch s {
    case "Korean":  return "🇰🇷"
    case "English": return "🇺🇸"
    case "Русский": return "🇷🇺"
    case "Français":return "🇫🇷"
    case "中文":    return "🇨🇳"
    case "日本語":  return "🇯🇵"
    case "Español": return "🇪🇸"
    default: return "🌐"
    }
}

// =============================================================================
//  Phrasebook tab
// =============================================================================
struct PhrasebookTab: View {
    let activeLangs: [String]
    let familyLanguages: [String]
    @ObservedObject var tts: FamilyTTS
    @EnvironmentObject var loc: Localization
    @State private var category: String = "Morning"
    private func localized(_ raw: String) -> String {
        switch raw {
        case "Morning":  return loc.t(.morning)
        case "Meal":     return loc.t(.meal)
        case "Bath":     return loc.t(.bath)
        case "Play":     return loc.t(.play)
        case "Bedtime":  return loc.t(.bedtime)
        case "Praise":   return loc.t(.praise)
        case "Apology":  return loc.t(.apology)
        case "Greeting": return loc.t(.greeting)
        default: return raw
        }
    }
    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 0) {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(Phrasebook.categories, id: \.self) { c in
                            Button { category = c } label: {
                                Text(localized(c))
                                    .font(.callout.weight(.semibold))
                                    .padding(.horizontal, 12).padding(.vertical, 7)
                                    .background(category == c ? Color.indigo : Color.white)
                                    .foregroundColor(category == c ? .white : .primary)
                                    .overlay(Capsule().stroke(Color.black.opacity(0.12), lineWidth: 1))
                                    .clipShape(Capsule())
                            }.buttonStyle(.plain)
                        }
                    }.padding(.horizontal, 16).padding(.vertical, 10)
                }
                List(Phrasebook.phrases.filter { $0.category == category }) { phrase in
                    VStack(alignment: .leading, spacing: 8) {
                        ForEach(familyLanguages.filter { activeLangs.contains($0) }, id: \.self) { lang in
                            if let line = phrase.translations[lang] {
                                HStack(spacing: 10) {
                                    Text(flagFor(lang)).font(.title3)
                                    Button {
                                        tts.speak(line, language: lang)
                                    } label: {
                                        Image(systemName: tts.speakingLang == lang
                                              ? "stop.circle.fill" : "play.circle.fill")
                                            .font(.system(size: 30)).foregroundColor(.indigo)
                                    }.buttonStyle(.plain)
                                    Text(line).font(.body)
                                    Spacer()
                                }
                            }
                        }
                    }
                    .padding(.vertical, 4)
                }
                .listStyle(.plain)
            }
            .navigationTitle(loc.t(.phrasebook))
        }
    }
}

// =============================================================================
//  Word Wall tab
// =============================================================================
struct WordWallTab: View {
    @ObservedObject var store: WordStore
    @ObservedObject var tts: FamilyTTS
    @EnvironmentObject var loc: Localization
    @State private var filter: String = "All"
    private var langs: [String] {
        ["All"] + Array(Set(store.items.map { $0.language })).sorted()
    }
    private var filtered: [WordItem] {
        filter == "All" ? store.items : store.items.filter { $0.language == filter }
    }
    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                if !store.items.isEmpty {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 8) {
                            ForEach(langs, id: \.self) { l in
                                Button { filter = l } label: {
                                    Text(l == "All" ? loc.t(.allFilter) : "\(flagFor(l)) \(loc.langName(l))")
                                        .font(.callout.weight(.semibold))
                                        .padding(.horizontal, 11).padding(.vertical, 6)
                                        .background(filter == l ? Color.indigo : Color.white)
                                        .foregroundColor(filter == l ? .white : .primary)
                                        .overlay(Capsule().stroke(Color.black.opacity(0.12), lineWidth: 1))
                                        .clipShape(Capsule())
                                }.buttonStyle(.plain)
                            }
                        }.padding(.horizontal, 16).padding(.vertical, 10)
                    }
                }
                if filtered.isEmpty {
                    ContentUnavailableView(loc.t(.noWordsYet),
                        systemImage: "rectangle.stack",
                        description: Text(loc.t(.wordsAutoHint)))
                } else {
                    ScrollView {
                        LazyVGrid(columns: [GridItem(.adaptive(minimum: 150), spacing: 10)],
                                  spacing: 10) {
                            ForEach(filtered) { w in
                                VStack(alignment: .leading, spacing: 6) {
                                    Text(flagFor(w.language)).font(.title3)
                                    HStack(spacing: 8) {
                                        Text(w.text).font(.title3.weight(.bold))
                                        Button {
                                            tts.speak(w.text, language: w.language)
                                        } label: {
                                            Image(systemName: tts.speakingLang == w.language
                                                  ? "stop.circle.fill" : "play.circle.fill")
                                                .font(.system(size: 28)).foregroundColor(.indigo)
                                        }.buttonStyle(.plain)
                                    }
                                    Text(w.context).font(.caption2).foregroundColor(.secondary).lineLimit(2)
                                }
                                .padding(12)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(RoundedRectangle(cornerRadius: 14).fill(Color.white))
                                .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.black.opacity(0.08), lineWidth: 1))
                            }
                        }
                        .padding(16)
                    }
                }
            }
            .navigationTitle(loc.t(.wordWallTitle))
        }
    }
}

// =============================================================================
//  Camera tab — Vision label + Gemma translation
// =============================================================================
@MainActor
final class TranslateEngine: ObservableObject {
    @Published var input: String = ""
    @Published var results: [String: String] = [:]
    @Published var rawOutput: String = ""
    @Published var isWorking: Bool = false

    // One-shot example built per language so the small model has a concrete
    // template. Without this, short inputs ("아기") cause Gemma E2B to drop
    // the Note line and sometimes skip an entire language block.
    private func exampleBlock(for lang: String) -> String {
        switch lang {
        case "Korean":
            return "=== Korean ===\nTranslation: 안녕\nNote: 또래나 친한 사이에 쓰는 가벼운 인사예요. 어른께는 \"안녕하세요\"라고 해야 해요."
        case "English":
            return "=== English ===\nTranslation: Hi\nNote: A casual everyday greeting. \"Hello\" is slightly more neutral; \"Hey\" is more familiar."
        case "Русский":
            return "=== Русский ===\nTranslation: Привет\nNote: Неформальное приветствие для друзей и сверстников. Старшим говорят \"Здравствуйте\"."
        case "Français":
            return "=== Français ===\nTranslation: Salut\nNote: Salutation familière entre amis ou collègues proches. Avec un inconnu on dit plutôt \"Bonjour\"."
        case "中文":
            return "=== 中文 ===\nTranslation: 你好\nNote: 通用问候，适合大多数场合。和熟人之间也可以说\"嗨\"。"
        case "日本語":
            return "=== 日本語 ===\nTranslation: こんにちは\nNote: 日中の標準的なあいさつ。親しい相手には「やっほー」なども使えます。"
        default:
            return "=== \(lang) ===\nTranslation: <translation>\nNote: <2–3 sentences of context>"
        }
    }

    func run(activeLangs: [String], llamaState: LlamaState) async {
        guard llamaState.isModelLoaded,
              !input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        else { return }
        isWorking = true
        results = [:]
        rawOutput = ""
        defer { isWorking = false }

        // Sequential per-language calls. Gemma E2B was unreliable when asked
        // to produce a multi-block trilingual response in one shot (it would
        // skip languages or drop the Note line). One call per target language
        // is bulletproof — and the parent watches the cards stream in.
        for target in activeLangs {
            let block = await translateOne(target: target, llamaState: llamaState)
            results[target] = block
            rawOutput += "\n=== \(target) ===\n\(block)\n"
        }
    }

    // Single-language translation. Returns the first non-empty line as the
    // translation and any remaining lines as the explanatory note.
    private func translateOne(target: String,
                              llamaState: LlamaState) async -> String {
        let prompt = """
        Translate the following text into \(target).

        Reply with exactly TWO lines:
        Line 1 — the natural translation only (no labels, no quotes).
        Line 2 — a 2–3 sentence note in \(target) (NOT in English) explaining tone, register, when to use it, or any cultural context a learner would miss.

        Text: \(input)
        """
        let wrapped = "<|turn>user\n\(prompt)<turn|>\n<|turn>model\n"
        await llamaState.clear()
        let checkpoint = llamaState.messageLog.count
        await llamaState.complete(text: wrapped)
        let start = Date()
        while Date().timeIntervalSince(start) < 45 {
            if llamaState.messageLog.range(of: "\\n\\s*Done\\s*\\n",
                                           options: .regularExpression) != nil { break }
            try? await Task.sleep(nanoseconds: 200_000_000)
        }
        let tail = String(llamaState.messageLog.dropFirst(min(checkpoint + wrapped.count,
                                                              llamaState.messageLog.count)))
        return cleanedSingleBlock(tail)
    }

    private func cleanedSingleBlock(_ raw: String) -> String {
        var s = raw
            .replacingOccurrences(of: "<|turn>", with: "")
            .replacingOccurrences(of: "<turn|>", with: "")
            .replacingOccurrences(of: "<bos>",   with: "")
            .replacingOccurrences(of: "<eos>",   with: "")
        if let r = s.range(of: "\nDone") { s = String(s[..<r.lowerBound]) }
        return s.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

// Pulls the "Translation:" / "Note:" fields out of a block. Model may write
// them in the target language (번역 / 메모, Перевод / Заметка, etc.), so we
// fall back to splitting on the first blank line if labels aren't present.
func splitTranslationAndNote(_ block: String) -> (translation: String, note: String) {
    let labels = ["Translation", "translation", "번역", "Перевод", "Traduction", "翻译", "翻訳"]
    let noteLabels = ["Note", "note", "메모", "Заметка", "Note culturelle", "주석", "Замечание"]

    // Strip a leading label even if it's missing the colon, or has extra
    // whitespace / dashes. The TTS must never read "번역" or "Translation"
    // aloud — that's why we're stripping aggressively.
    func stripLeadingLabel(_ s: String, _ pool: [String]) -> String {
        var out = s.trimmingCharacters(in: .whitespacesAndNewlines)
        for label in pool {
            for trailer in [":", " :", " -", "–", "—", ""] {
                let pat = "\(label)\(trailer)"
                if out.lowercased().hasPrefix(pat.lowercased()) {
                    out = String(out.dropFirst(pat.count))
                        .trimmingCharacters(in: .whitespacesAndNewlines)
                    break
                }
            }
        }
        return out
    }

    var translation = ""
    var note = ""
    for tLabel in labels {
        if let r = block.range(of: "\(tLabel):", options: .caseInsensitive) {
            let after = block[r.upperBound...]
            for nLabel in noteLabels {
                if let nr = after.range(of: "\(nLabel):", options: .caseInsensitive) {
                    translation = String(after[..<nr.lowerBound]).trimmingCharacters(in: .whitespacesAndNewlines)
                    note = String(after[nr.upperBound...]).trimmingCharacters(in: .whitespacesAndNewlines)
                    return (stripLeadingLabel(translation, labels),
                            stripLeadingLabel(note, noteLabels))
                }
            }
            translation = String(after).trimmingCharacters(in: .whitespacesAndNewlines)
            return (stripLeadingLabel(translation, labels), "")
        }
    }
    // Fallback: first line = translation, rest = note (with any leading label
    // still stripped in case the model wrote "번역 부드럽게" without a colon).
    let lines = block.split(separator: "\n", maxSplits: 1, omittingEmptySubsequences: true)
    if lines.count == 2 {
        return (stripLeadingLabel(String(lines[0]), labels),
                stripLeadingLabel(String(lines[1]), noteLabels))
    }
    return (stripLeadingLabel(block, labels), "")
}

struct TranslateTab: View {
    let activeLangs: [String]
    let familyLanguages: [String]
    @ObservedObject var tts: FamilyTTS
    @ObservedObject var llamaState: LlamaState
    @EnvironmentObject var loc: Localization
    @StateObject private var engine = TranslateEngine()
    @State private var showRaw = false
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    Text(loc.t(.translateHint))
                        .font(.footnote).foregroundColor(.secondary)
                        .fixedSize(horizontal: false, vertical: true)

                    ZStack(alignment: .topLeading) {
                        if engine.input.isEmpty {
                            Text(loc.placeholder(for: .say))
                                .foregroundColor(.secondary.opacity(0.5))
                                .padding(.horizontal, 12).padding(.vertical, 10)
                        }
                        TextEditor(text: $engine.input)
                            .scrollContentBackground(.hidden)
                            .padding(.horizontal, 8).padding(.vertical, 4)
                            .frame(minHeight: 110)
                    }
                    .background(Color.white)
                    .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.black.opacity(0.08), lineWidth: 1))
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))

                    HStack(spacing: 8) {
                        Button {
                            Task { await engine.run(activeLangs: activeLangs,
                                                    llamaState: llamaState) }
                        } label: {
                            HStack(spacing: 6) {
                                if engine.isWorking { ProgressView().controlSize(.small) }
                                else { Image(systemName: "character.bubble.fill") }
                                Text(engine.isWorking ? loc.t(.translating)
                                                       : loc.t(.translateButton))
                                    .fontWeight(.semibold)
                            }
                            .frame(maxWidth: .infinity).padding(.vertical, 10)
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(engine.isWorking
                                  || engine.input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                                  || !llamaState.isModelLoaded)

                        Button {
                            engine.input = ""
                            engine.results = [:]
                        } label: {
                            Label(loc.t(.translateClear), systemImage: "trash")
                        }.buttonStyle(.bordered)
                    }

                    if !engine.rawOutput.isEmpty {
                        Button {
                            showRaw.toggle()
                        } label: {
                            Label(showRaw ? "Hide raw" : "Show raw model output",
                                  systemImage: showRaw ? "eye.slash" : "eye")
                                .font(.caption)
                        }.buttonStyle(.bordered)
                        if showRaw {
                            ScrollView {
                                Text(engine.rawOutput)
                                    .font(.footnote.monospaced())
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .textSelection(.enabled)
                            }
                            .frame(maxHeight: 240)
                            .padding(8)
                            .background(Color.black.opacity(0.04))
                            .clipShape(RoundedRectangle(cornerRadius: 10))
                        }
                    }
                    if !engine.results.isEmpty {
                        VStack(spacing: 12) {
                            ForEach(familyLanguages.filter { activeLangs.contains($0) }, id: \.self) { lang in
                                if let text = engine.results[lang] {
                                    let parts = splitTranslationAndNote(text)
                                    HStack(alignment: .top, spacing: 10) {
                                        Text(flagFor(lang)).font(.title2)
                                        Button {
                                            tts.speak(parts.translation, language: lang)
                                        } label: {
                                            Image(systemName: tts.speakingLang == lang
                                                  ? "stop.circle.fill" : "play.circle.fill")
                                                .font(.system(size: 30)).foregroundColor(.indigo)
                                        }.buttonStyle(.plain)
                                        VStack(alignment: .leading, spacing: 4) {
                                            Text(loc.langName(lang))
                                                .font(.caption.weight(.bold))
                                                .foregroundColor(.secondary)
                                            Text(parts.translation)
                                                .font(.title3.weight(.semibold))
                                                .textSelection(.enabled)
                                            if !parts.note.isEmpty {
                                                Text(parts.note)
                                                    .font(.footnote)
                                                    .foregroundColor(.secondary)
                                                    .textSelection(.enabled)
                                            }
                                        }
                                        Spacer()
                                    }
                                    .padding(12)
                                    .background(RoundedRectangle(cornerRadius: 14).fill(Color.white))
                                    .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.black.opacity(0.08), lineWidth: 1))
                                }
                            }
                        }
                    }
                }
                .padding(16)
            }
            .navigationTitle(loc.t(.translate))
        }
    }
}

struct CameraTab: View {
    let activeLangs: [String]
    let familyLanguages: [String]
    @ObservedObject var tts: FamilyTTS
    @ObservedObject var llamaState: LlamaState
    @EnvironmentObject var loc: Localization
    @StateObject private var cam = CameraLabeler()
    var body: some View {
        NavigationStack {
            VStack(spacing: 12) {
                if let img = cam.preview {
                    Image(uiImage: img)
                        .resizable().scaledToFit()
                        .frame(maxHeight: 340)
                        .clipShape(RoundedRectangle(cornerRadius: 18))
                        .padding(.horizontal, 16)
                } else {
                    RoundedRectangle(cornerRadius: 18)
                        .fill(Color.black.opacity(0.06))
                        .frame(height: 280)
                        .overlay(
                            VStack(spacing: 6) {
                                Image(systemName: "camera.fill")
                                    .font(.system(size: 36))
                                    .foregroundColor(.secondary)
                                Text(loc.t(.takePhoto))
                                    .font(.caption).foregroundColor(.secondary)
                            })
                        .padding(.horizontal, 16)
                }
                if !cam.labels.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text(loc.t(.tapWord)).font(.caption.weight(.bold)).foregroundColor(.secondary)
                            Spacer()
                            if cam.isTranslating {
                                ProgressView().controlSize(.small)
                            }
                        }
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 6) {
                                ForEach(cam.labels, id: \.self) { label in
                                    let on = (cam.selectedLabel == label)
                                    Button {
                                        Task {
                                            await cam.translate(word: label,
                                                                into: activeLangs,
                                                                llamaState: llamaState)
                                        }
                                    } label: {
                                        Text(label)
                                            .font(.callout.weight(.semibold))
                                            .padding(.horizontal, 11).padding(.vertical, 6)
                                            .background(on ? Color.indigo : Color.indigo.opacity(0.10))
                                            .foregroundColor(on ? .white : .primary)
                                            .clipShape(Capsule())
                                    }
                                    .buttonStyle(.plain)
                                    .disabled(cam.isTranslating)
                                }
                            }
                        }
                    }.padding(.horizontal, 16)
                }
                if !cam.translations.isEmpty, let selected = cam.selectedLabel {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("\"\(selected)\"")
                            .font(.title3.weight(.bold))
                            .foregroundColor(.indigo)
                        ForEach(familyLanguages.filter { activeLangs.contains($0) }, id: \.self) { lang in
                            if let t = cam.translations[lang] {
                                HStack(spacing: 10) {
                                    Text(flagFor(lang)).font(.title3)
                                    Button {
                                        tts.speak(t, language: lang)
                                    } label: {
                                        Image(systemName: tts.speakingLang == lang
                                              ? "stop.circle.fill" : "play.circle.fill")
                                            .font(.system(size: 32)).foregroundColor(.indigo)
                                    }.buttonStyle(.plain)
                                    Text(t).font(.title3)
                                    Spacer()
                                }
                            }
                        }
                    }.padding(.horizontal, 16)
                }
                Spacer()
                Button {
                    cam.showPicker = true
                } label: {
                    Label(loc.t(.takePhoto), systemImage: "camera.viewfinder")
                        .fontWeight(.semibold)
                        .frame(maxWidth: .infinity).padding(.vertical, 10)
                }
                .buttonStyle(.borderedProminent)
                .padding(.horizontal, 16).padding(.bottom, 16)
            }
            .sheet(isPresented: $cam.showPicker) {
                ImagePicker(image: $cam.preview, onPicked: cam.processPicked)
            }
            .navigationTitle(loc.t(.camera))
        }
    }
}

private struct FlowText: View {
    let items: [String]
    init(_ items: [String]) { self.items = items }
    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 6) {
                ForEach(items, id: \.self) { Text($0)
                    .font(.callout.weight(.semibold))
                    .padding(.horizontal, 10).padding(.vertical, 5)
                    .background(Color.indigo.opacity(0.10))
                    .clipShape(Capsule())
                }
            }
        }
    }
}

@MainActor
final class CameraLabeler: ObservableObject {
    @Published var preview: UIImage? = nil
    @Published var labels: [String] = []          // English labels from Vision
    @Published var translations: [String: String] = [:]   // lang → "word: short description"
    @Published var selectedLabel: String? = nil
    @Published var isTranslating: Bool = false
    @Published var showPicker: Bool = false

    func processPicked(_ img: UIImage) {
        preview = img
        labels = []
        translations = [:]
        selectedLabel = nil
        guard let cg = img.cgImage else { return }
        let request = VNClassifyImageRequest()
        let handler = VNImageRequestHandler(cgImage: cg, options: [:])
        DispatchQueue.global(qos: .userInitiated).async {
            try? handler.perform([request])
            let obs = (request.results ?? [])
                .filter { $0.confidence > 0.2 }
                .prefix(6)
                .map { $0.identifier.replacingOccurrences(of: "_", with: " ") }
            DispatchQueue.main.async {
                self.labels = Array(obs)
            }
        }
    }

    func translate(word: String,
                   into activeLangs: [String],
                   llamaState: LlamaState) async {
        guard llamaState.isModelLoaded else { return }
        selectedLabel = word
        translations = [:]
        isTranslating = true
        defer { isTranslating = false }

        let blocks = activeLangs
            .map { "=== \($0) ===\n<word in \($0)>: <one short sentence a young child would understand>" }
            .joined(separator: "\n\n")
        let prompt = """
        The English word is "\(word)". For each language below, write the matching word followed by ": " and then ONE short, kid-friendly sentence (under 12 words) explaining it.

        Format exactly:
        \(blocks)
        """
        let wrapped = "<|turn>user\n\(prompt)<turn|>\n<|turn>model\n"
        await llamaState.clear()
        let checkpoint = llamaState.messageLog.count
        await llamaState.complete(text: wrapped)
        let start = Date()
        while Date().timeIntervalSince(start) < 60 {
            if llamaState.messageLog.range(of: "\\n\\s*Done\\s*\\n",
                                           options: .regularExpression) != nil { break }
            try? await Task.sleep(nanoseconds: 250_000_000)
        }
        let tail = String(llamaState.messageLog.dropFirst(min(checkpoint + wrapped.count,
                                                              llamaState.messageLog.count)))
        if let card = parseLanguageBlocks(from: tail,
                                          activeLanguages: activeLangs,
                                          targetAge: 4,
                                          mode: "label") {
            translations = card.body
        }
    }
}

struct ImagePicker: UIViewControllerRepresentable {
    @Binding var image: UIImage?
    let onPicked: (UIImage) -> Void
    func makeCoordinator() -> Coord { Coord(self) }
    func makeUIViewController(context: Context) -> UIImagePickerController {
        let p = UIImagePickerController()
        p.sourceType = UIImagePickerController.isSourceTypeAvailable(.camera) ? .camera : .photoLibrary
        p.delegate = context.coordinator
        return p
    }
    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}
    final class Coord: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let parent: ImagePicker
        init(_ p: ImagePicker) { self.parent = p }
        func imagePickerController(_ picker: UIImagePickerController,
                                   didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey : Any]) {
            if let img = info[.originalImage] as? UIImage {
                parent.image = img
                parent.onPicked(img)
            }
            picker.dismiss(animated: true)
        }
        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            picker.dismiss(animated: true)
        }
    }
}

// =============================================================================
//  Family tab
// =============================================================================
struct FamilyTab: View {
    @Binding var savedLangs: String
    @Binding var savedKids: String
    @Binding var visitorMode: VisitorMode
    @Binding var activeLangs: Set<String>
    let familyLanguages: [String]
    @ObservedObject var llamaState: LlamaState
    @ObservedObject var audit: AuditLogStore
    @ObservedObject var tts: FamilyTTS
    @Binding var policyAdapterOn: Bool
    @EnvironmentObject var loc: Localization
    @State private var showFamilySetup = false
    @State private var showAuditSheet = false
    @State private var showModelSheet = false
    var body: some View {
        NavigationStack {
            Form {
                Section(loc.t(.uiLanguage)) {
                    Picker(loc.t(.uiLanguage), selection: $loc.lang) {
                        ForEach(Localization.supported, id: \.code) { lang in
                            Text("\(lang.flag) \(lang.label)").tag(lang.code)
                        }
                    }
                }
                Section(loc.t(.visitorMode)) {
                    Picker(loc.t(.whosHere), selection: $visitorMode) {
                        ForEach(VisitorMode.allCases) { Text($0.title(loc)).tag($0) }
                    }
                    if visitorMode != .none {
                        Text(visitorMode.subtitle(loc)).font(.caption).foregroundColor(.secondary)
                    }
                }
                Section(loc.t(.activeLanguages)) {
                    ForEach(familyLanguages, id: \.self) { lang in
                        Toggle("\(flagFor(lang)) \(loc.langName(lang))",
                               isOn: Binding(
                                get: { activeLangs.contains(lang) },
                                set: { on in
                                    if on { activeLangs.insert(lang) } else { activeLangs.remove(lang) }
                                }))
                    }
                }
                Section(loc.t(.family)) {
                    Button { showFamilySetup = true } label: {
                        Label(loc.t(.editFamily), systemImage: "person.crop.circle.badge.plus")
                    }
                }
                Section {
                    ForEach(familyLanguages.filter { activeLangs.contains($0) }, id: \.self) { lang in
                        VoicePickerRow(language: lang, tts: tts)
                    }
                } header: {
                    Text(loc.t(.voiceSection))
                } footer: {
                    Text(loc.t(.voicePickerHint)).font(.caption2)
                }
                Section(loc.t(.system)) {
                    Button { showModelSheet = true } label: {
                        Label(loc.t(.modelLabel), systemImage: "cpu")
                    }
                    Button { showAuditSheet = true } label: {
                        Label(loc.t(.historyLabel), systemImage: "clock.arrow.circlepath")
                    }
                    Toggle(loc.t(.safetyMode), isOn: $policyAdapterOn)
                }
            }
            .navigationTitle(loc.t(.family))
            .sheet(isPresented: $showFamilySetup) {
                FamilySetupView(languages: $savedLangs, kids: $savedKids)
            }
            .sheet(isPresented: $showModelSheet) {
                NavigationStack { ModelDrawerView(llamaState: llamaState) }
            }
            .sheet(isPresented: $showAuditSheet) {
                NavigationStack { AuditLogView(store: audit) }
            }
        }
    }
}

// =============================================================================
//  Mode descriptor
// =============================================================================
enum FamilyMode: String, CaseIterable, Identifiable {
    case story, words, song, say, between, culture

    var id: String { rawValue }

    var title: String {
        switch self {
        case .story:   return "Bedtime story"
        case .words:   return "Word card"
        case .song:    return "Tiny song"
        case .say:     return "Say it to my child"
        case .between: return "Caregiver note"
        case .culture: return "Today's culture beat"
        }
    }
    var icon: String {
        switch self {
        case .story:   return "moon.stars.fill"
        case .words:   return "abc"
        case .song:    return "music.note"
        case .say:     return "bubble.left.and.bubble.right.fill"
        case .between: return "person.2.wave.2.fill"
        case .culture: return "globe.asia.australia.fill"
        }
    }
    var color: Color {
        switch self {
        case .story:   return Color(red: 0.55, green: 0.35, blue: 0.85)
        case .words:   return Color(red: 0.20, green: 0.55, blue: 0.85)
        case .song:    return Color(red: 0.95, green: 0.55, blue: 0.30)
        case .say:     return Color(red: 0.30, green: 0.65, blue: 0.50)
        case .between: return Color(red: 0.85, green: 0.35, blue: 0.55)
        case .culture: return Color(red: 0.55, green: 0.45, blue: 0.30)
        }
    }
    var placeholder: String {
        switch self {
        case .story:   return "잠 안 자려는 토끼와 별 친구 이야기"
        case .words:   return "오늘 산책에서 본 빨간 단풍잎"
        case .song:    return "양치 시간을 즐겁게 만드는 짧은 노래"
        case .say:     return "이제 놀이 그만, 손 씻으러 가자 — 부드럽게"
        case .between: return "러시아어 쓰는 할머니께 아이 낮잠 시간 안내"
        case .culture: return "추석에 송편을 만드는 이유를 아이 눈높이로"
        }
    }
    var systemHint: String {
        switch self {
        case .story:
            return "Write a calm, soothing bedtime story (≤200 words total across active languages, alternating)."
        case .words:
            return "Pick one focus noun, give 3 short example sentences per active language."
        case .song:
            return "Write a 4–8 line rhyming song with simple repetition."
        case .say:
            return "Rewrite the parent intent as gentle child-directed speech in each active language."
        case .between:
            return "Write a short caregiver-to-caregiver note: greeting, the fact, the ask, the time."
        case .culture:
            return "Share one cultural moment in 3–5 short lines per active language plus a play idea."
        }
    }

    var actionLabel: String {
        switch self {
        case .story:   return "Make story"
        case .words:   return "Make word card"
        case .song:    return "Make song"
        case .say:     return "Rewrite for child"
        case .between: return "Write note"
        case .culture: return "Today's moment"
        }
    }
}

private struct ModeChip: View {
    let mode: FamilyMode
    let selected: Bool
    @EnvironmentObject var loc: Localization

    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: mode.icon)
                .font(.subheadline.weight(.semibold))
            Text(loc.title(for: mode))
                .font(.subheadline.weight(.semibold))
                .lineLimit(1)
        }
        .padding(.horizontal, 12).padding(.vertical, 8)
        .background(selected ? mode.color : Color.white)
        .foregroundColor(selected ? .white : .primary)
        .overlay(
            Capsule().stroke(
                selected ? Color.clear : Color.black.opacity(0.10),
                lineWidth: 1
            )
        )
        .clipShape(Capsule())
    }
}

// =============================================================================
//  Family setup
// =============================================================================
private struct VoicePickerRow: View {
    let language: String
    @ObservedObject var tts: FamilyTTS
    @EnvironmentObject var loc: Localization
    private var voices: [AVSpeechSynthesisVoice] {
        let prefix = String(ttsBCP47(forLanguage: language).prefix(2))
        return AVSpeechSynthesisVoice.speechVoices()
            .filter { $0.language.hasPrefix(prefix) }
            .sorted { a, b in
                func score(_ v: AVSpeechSynthesisVoice) -> Int {
                    let siri = v.identifier.localizedCaseInsensitiveContains("siri")
                    let q: Int = {
                        switch v.quality { case .premium: return 3
                                          case .enhanced: return 2
                                          default: return 1 }
                    }()
                    return q * 2 + (siri ? 1 : 0)
                }
                return score(a) > score(b)
            }
    }
    private func tag(for v: AVSpeechSynthesisVoice) -> String {
        let siri = v.identifier.localizedCaseInsensitiveContains("siri") ? " · Siri" : ""
        let q: String
        switch v.quality {
        case .premium:  q = "Premium"
        case .enhanced: q = "Enhanced"
        default:        q = "Compact"
        }
        return "\(v.name) (\(q)\(siri))"
    }
    var body: some View {
        let current = tts.voiceID(for: language)
        VStack(alignment: .leading, spacing: 4) {
            Text("\(flagFor(language)) \(loc.langName(language))")
                .font(.subheadline.weight(.semibold))
            Picker("", selection: Binding(
                get: { current },
                set: { tts.setVoiceID($0, for: language) })
            ) {
                Text(loc.t(.autoVoice)).tag("")
                ForEach(voices, id: \.identifier) { v in
                    Text(tag(for: v)).tag(v.identifier)
                }
            }
            .labelsHidden()
            .pickerStyle(.menu)
        }
    }
}

private struct FamilySetupView: View {
    @Binding var languages: String
    @Binding var kids: String
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject var loc: Localization

    @State private var langSet: Set<String> = []
    @State private var name1 = "Aria";  @State private var age1 = 2
    @State private var name2 = "Maxim"; @State private var age2 = 4
    @State private var twoKids = true

    private let availableLanguages = [
        "Korean", "English", "Русский", "Français", "中文", "日本語",
        "Tiếng Việt", "Español", "Türkçe", "Монгол", "ภาษาไทย"
    ]

    var body: some View {
        NavigationStack {
            Form {
                Section(loc.t(.familyLangsSection)) {
                    ForEach(availableLanguages, id: \.self) { lang in
                        Button {
                            if langSet.contains(lang) { langSet.remove(lang) }
                            else { langSet.insert(lang) }
                        } label: {
                            HStack {
                                Text("\(flagFor(lang)) \(loc.langName(lang))"); Spacer()
                                if langSet.contains(lang) {
                                    Image(systemName: "checkmark.circle.fill").foregroundColor(.accentColor)
                                }
                            }
                        }.foregroundColor(.primary)
                    }
                }
                Section(loc.t(.child1)) {
                    TextField(loc.t(.nameLabel), text: $name1)
                    Stepper("\(loc.t(.ageStepper)): \(loc.ageLabel(age1))", value: $age1, in: 0...12)
                }
                Section {
                    Toggle(loc.t(.addSecondChild), isOn: $twoKids)
                    if twoKids {
                        TextField(loc.t(.nameLabel), text: $name2)
                        Stepper("\(loc.t(.ageStepper)): \(loc.ageLabel(age2))", value: $age2, in: 0...12)
                    }
                }
                Section {
                    Button { save(); dismiss() } label: {
                        Text(loc.t(.save)).frame(maxWidth: .infinity).fontWeight(.semibold)
                    }
                }
            }
            .navigationTitle(loc.t(.family))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(loc.t(.done)) { dismiss() }
                }
            }
            .onAppear {
                langSet = Set(languages.split(separator: ",")
                              .map { String($0).trimmingCharacters(in: .whitespaces) })
                let list = kids.split(separator: ",").map { String($0) }
                if let first = list.first {
                    let p = first.split(separator: ":")
                    if p.count == 2 { name1 = String(p[0]); age1 = Int(p[1]) ?? 2 }
                }
                if list.count >= 2 {
                    let p = list[1].split(separator: ":")
                    if p.count == 2 {
                        name2 = String(p[0]); age2 = Int(p[1]) ?? 4
                        twoKids = true
                    }
                } else { twoKids = false }
            }
        }
    }

    private func save() {
        languages = langSet.sorted().joined(separator: ",")
        var list = ["\(name1.trimmingCharacters(in: .whitespaces)):\(age1)"]
        if twoKids { list.append("\(name2.trimmingCharacters(in: .whitespaces)):\(age2)") }
        kids = list.joined(separator: ",")
    }
}

// =============================================================================
//  Audit log viewer + export
// =============================================================================
private struct AuditLogView: View {
    @ObservedObject var store: AuditLogStore
    @Environment(\.dismiss) private var dismiss
    @State private var exportURL: URL? = nil

    var body: some View {
        List {
            if store.entries.isEmpty {
                Text("No audit entries yet.  Run a generation first.")
                    .foregroundColor(.secondary)
            } else {
                ForEach(store.entries.reversed(), id: \.timestamp) { e in
                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            Text(e.mode).font(.subheadline.weight(.bold))
                            Spacer()
                            Text(e.band.uppercased())
                                .font(.caption.weight(.heavy))
                                .padding(.horizontal, 6).padding(.vertical, 2)
                                .background(colorFor(band: e.band).opacity(0.18))
                                .foregroundColor(colorFor(band: e.band))
                                .clipShape(Capsule())
                        }
                        Text(e.promptDigest).font(.footnote).foregroundColor(.secondary)
                        HStack(spacing: 8) {
                            scoreBadge("G1s", e.g1Structure)
                            scoreBadge("G1a", e.g1Age)
                            scoreBadge("G2",  e.g2Script)
                            scoreBadge("G3",  e.g3Schema)
                            scoreBadge("G4",  e.g4Routing)
                        }
                        Text("adapter: \(e.adapterTag) · age \(e.targetAge) · \(e.activeLanguages.joined(separator: "/"))")
                            .font(.caption2).foregroundColor(.secondary)
                    }
                    .padding(.vertical, 4)
                }
            }
        }
        .navigationTitle("Audit capsule")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Button("Export") {
                    if let url = store.export() { exportURL = url }
                }
            }
            ToolbarItem(placement: .navigationBarLeading) {
                Button("Close") { dismiss() }
            }
        }
        .sheet(item: $exportURL) { url in
            ShareSheet(items: [url])
        }
    }

    private func scoreBadge(_ name: String, _ v: Double) -> some View {
        let color = v >= 0.95 ? Color.green : (v >= 0.75 ? .orange : .red)
        return Text("\(name) \(Int(v*100))")
            .font(.caption2.weight(.bold))
            .padding(.horizontal, 5).padding(.vertical, 2)
            .background(color.opacity(0.18))
            .foregroundColor(color)
            .clipShape(Capsule())
    }

    private func colorFor(band: String) -> Color {
        switch band {
        case "green": return Color(red: 0.20, green: 0.62, blue: 0.40)
        case "amber": return Color(red: 0.80, green: 0.55, blue: 0.15)
        default:      return Color(red: 0.80, green: 0.25, blue: 0.30)
        }
    }
}

extension URL: Identifiable { public var id: String { absoluteString } }

private struct ShareSheet: UIViewControllerRepresentable {
    let items: [Any]
    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: items, applicationActivities: nil)
    }
    func updateUIViewController(_ controller: UIActivityViewController, context: Context) {}
}

// =============================================================================
//  Model drawer — unchanged engine surface
// =============================================================================
private struct ModelDrawerView: View {
    @ObservedObject var llamaState: LlamaState
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        List {
            Section("Gemma 4 model file (.gguf)") {
                LoadCustomButton(llamaState: llamaState)
                Text("Copy gemma4_e2b_policy.Q4_K_M.gguf into Files → On My iPad, then load it here.  The 3.2 GB model stays outside the app bundle.")
                    .font(.caption).foregroundColor(.secondary)
            }
            if !llamaState.downloadedModels.isEmpty {
                Section("Loaded models") {
                    ForEach(llamaState.downloadedModels) { m in
                        DownloadButton(llamaState: llamaState, modelName: m.name,
                                       modelUrl: m.url, filename: m.filename)
                    }.onDelete(perform: delete)
                }
            }
            if !llamaState.undownloadedModels.isEmpty {
                Section("Optional test models") {
                    ForEach(llamaState.undownloadedModels) { m in
                        DownloadButton(llamaState: llamaState, modelName: m.name,
                                       modelUrl: m.url, filename: m.filename)
                    }
                }
            }
        }
        .listStyle(.insetGrouped)
        .navigationTitle("Model")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) { Button("Done") { dismiss() } }
        }
    }

    private func delete(at offsets: IndexSet) {
        offsets.forEach { offset in
            let m = llamaState.downloadedModels[offset]
            let url = FileManager.default
                .urls(for: .documentDirectory, in: .userDomainMask)[0]
                .appendingPathComponent(m.filename)
            try? FileManager.default.removeItem(at: url)
        }
        llamaState.downloadedModels.remove(atOffsets: offsets)
    }
}

#Preview {
    ContentView()
}
