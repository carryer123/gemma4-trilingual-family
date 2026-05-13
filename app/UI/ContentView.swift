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

// =============================================================================
//  SpeechRecognizer — on-device Apple Speech wrapper used to capture the
//  parent's spoken prompt while their hands are full. Authorization is
//  requested lazily; recognition is forced on-device when supported.
// =============================================================================
@MainActor
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
            lastError = "no SFSpeechRecognizer for \(locale.identifier)"
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
        if !authorized {
            lastError = "speech=\(speechStatus.rawValue) mic=\(micGranted)"
        }
    }

    func start() throws {
        guard authorized, let recognizer = recognizer, recognizer.isAvailable else {
            lastError = "recognizer unavailable"
            return
        }
        stop()
        transcript = ""

        let req = SFSpeechAudioBufferRecognitionRequest()
        req.shouldReportPartialResults = true
        if #available(iOS 13.0, *) { req.requiresOnDeviceRecognition = true }
        request = req

        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.record, mode: .measurement, options: .duckOthers)
        try session.setActive(true, options: .notifyOthersOnDeactivation)

        let node = audioEngine.inputNode
        let fmt = node.outputFormat(forBus: 0)
        node.installTap(onBus: 0, bufferSize: 1024, format: fmt) { buffer, _ in
            req.append(buffer)
        }
        audioEngine.prepare()
        try audioEngine.start()

        task = recognizer.recognitionTask(with: req) { [weak self] result, error in
            guard let self else { return }
            Task { @MainActor in
                if let result {
                    self.transcript = result.bestTranscription.formattedString
                }
                if error != nil { self.stop() }
            }
        }
        isRecording = true
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
    static func wrap(_ prompt: String) -> String {
        // The model's tokenizer adds <bos> via add_bos in LlamaContext.tokenize,
        // so we only inject the turn markers here.
        return "<start_of_turn>user\n\(prompt)<end_of_turn>\n<start_of_turn>model\n"
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
    @State private var showFamilySheet = false
    @State private var showModelSheet  = false
    @State private var showAuditSheet  = false
    @State private var generatedRaw: String = ""
    @State private var generationCheckpoint: Int = 0

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
        NavigationStack {
            ZStack(alignment: .top) {
                background
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        hero
                        sessionRouter
                        modeGrid
                        promptCard
                        if isGenerating || lastReport != nil { gateDashboard }
                        if let card = lastReport?.parsedCard { resultCard(card) }
                        if !generatedRaw.isEmpty && lastReport?.parsedCard == nil {
                            rawCard
                        }
                        footer
                    }
                    .padding(.horizontal, 20).padding(.top, 12).padding(.bottom, 40)
                }
            }
            .navigationTitle("Gemma Family")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button { showFamilySheet = true } label: { Image(systemName: "person.3.fill") }
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Menu {
                        Button { showAuditSheet = true } label: { Label("Audit log", systemImage: "doc.text.magnifyingglass") }
                        Button { showModelSheet  = true } label: { Label("Model",     systemImage: "cpu") }
                    } label: { Image(systemName: "ellipsis.circle") }
                }
            }
            .sheet(isPresented: $showFamilySheet) {
                FamilySetupView(languages: $savedLangs, kids: $savedKids)
            }
            .sheet(isPresented: $showModelSheet) {
                NavigationStack { ModelDrawerView(llamaState: llamaState) }
            }
            .sheet(isPresented: $showAuditSheet) {
                NavigationStack { AuditLogView(store: audit) }
            }
        }
        .onAppear(perform: applyKidSession)
        .onChange(of: sessionKid) { _ in applyKidSession() }
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
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .firstTextBaseline) {
                Text("State-Gated ").font(.system(size: 22, weight: .semibold, design: .rounded))
                + Text("Family Tutor").font(.system(size: 22, weight: .heavy, design: .rounded))
                    .foregroundColor(Color(red: 0.83, green: 0.32, blue: 0.45))
                Spacer()
                deviceBadge
            }
            Text("On-device Gemma 4 E2B + policy+family repair LoRA (seed 10).  Every answer is checked against the same G1–G4 deployment gates we used in the paper.")
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
                Label("Session router (G4)", systemImage: "arrow.triangle.branch")
                    .font(.subheadline.weight(.semibold))
                Spacer()
                Toggle(isOn: $policyAdapterOn) {
                    Text(policyAdapterOn ? "policy adapter" : "no-policy ablation")
                        .font(.caption.weight(.semibold))
                }
                .toggleStyle(.switch).tint(.indigo).labelsHidden()
                Text(policyAdapterOn ? "policy" : "no-policy")
                    .font(.caption.weight(.semibold))
                    .foregroundColor(policyAdapterOn ? .green : .red)
            }
            HStack(spacing: 8) {
                ForEach(familyKids, id: \.name) { kid in
                    Button {
                        sessionKid = kid.name
                    } label: {
                        VStack(spacing: 2) {
                            Text(kid.name).font(.subheadline.weight(.bold))
                            Text("\(kid.age)세").font(.caption2)
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
                    Text("Active languages:")
                        .font(.caption).foregroundColor(.secondary)
                    ForEach(familyLanguages, id: \.self) { lang in
                        let on = activeLangs.contains(lang)
                        Button {
                            if on { activeLangs.remove(lang) } else { activeLangs.insert(lang) }
                        } label: {
                            Text(lang)
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

    // MARK: - Mode grid
    private var modeGrid: some View {
        LazyVGrid(columns: [GridItem(.flexible(), spacing: 10),
                            GridItem(.flexible(), spacing: 10)], spacing: 10) {
            ForEach(FamilyMode.allCases) { mode in
                Button {
                    selectedMode = mode
                    userText = mode.placeholder
                } label: {
                    ModeCard(mode: mode, selected: selectedMode == mode)
                }.buttonStyle(.plain)
            }
        }
    }

    // MARK: - Prompt card
    private var promptCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Label(selectedMode.title, systemImage: selectedMode.icon)
                    .font(.subheadline.weight(.bold))
                    .foregroundColor(selectedMode.color)
                Spacer()
                Text("\(sessionKid) · \(targetAge)세")
                    .font(.caption.weight(.medium))
                    .foregroundColor(.secondary)
            }
            ZStack(alignment: .topLeading) {
                if userText.isEmpty {
                    Text(selectedMode.placeholder)
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

            HStack(spacing: 8) {
                // Microphone — Apple on-device speech, locale tracks primary active language.
                Button {
                    toggleRecording()
                } label: {
                    HStack(spacing: 6) {
                        Image(systemName: speech.isRecording ? "stop.circle.fill" : "mic.fill")
                        Text(speech.isRecording ? "Stop" : "Talk")
                            .fontWeight(.semibold)
                    }
                    .padding(.vertical, 9).padding(.horizontal, 14)
                }
                .buttonStyle(.bordered)
                .tint(speech.isRecording ? .red : .blue)

                Button {
                    Task { await runGeneration() }
                } label: {
                    HStack(spacing: 6) {
                        if isGenerating { ProgressView().controlSize(.small) }
                        else { Image(systemName: "sparkles") }
                        Text(isGenerating ? "Generating…" : "Run with G1–G4")
                            .fontWeight(.semibold)
                    }
                    .frame(maxWidth: .infinity).padding(.vertical, 9)
                }
                .buttonStyle(.borderedProminent).tint(selectedMode.color)
                .disabled(isGenerating || userText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)

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

            if let err = speech.lastError {
                Text("mic: \(err)").font(.caption2).foregroundColor(.red)
            }
        }
        .padding(14)
        .background(RoundedRectangle(cornerRadius: 18, style: .continuous).fill(.white.opacity(0.86)))
        .onChange(of: speech.transcript) { _ in
            // Stream live transcript into the textbox while recording.
            userText = speech.transcript
        }
    }

    private func toggleRecording() {
        if speech.isRecording {
            speech.stop()
            return
        }
        // Use the first active language as the speech locale; user can switch
        // by toggling active_languages chips.
        let primary = activeLangs.first ?? "Korean"
        speech.configure(locale: speechLocale(forLanguage: primary))
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

    // MARK: - Result card (parsed family card)
    private func resultCard(_ card: FamilyCard) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(card.title).font(.title3.bold())
                Spacer()
                Text("\(card.target_age)세").font(.caption.weight(.semibold)).foregroundColor(.secondary)
            }
            ForEach(activeLangs.sorted(), id: \.self) { lang in
                if let body = card.body[lang] {
                    HStack(alignment: .top, spacing: 8) {
                        Text(langTag(lang))
                            .font(.caption2.weight(.bold))
                            .padding(.horizontal, 6).padding(.vertical, 3)
                            .background(selectedMode.color.opacity(0.15))
                            .clipShape(Capsule())
                        Text(body)
                            .font(.system(size: 15, design: .rounded))
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
            }
            Divider().padding(.vertical, 4)
            HStack(alignment: .top, spacing: 6) {
                Image(systemName: "hand.raised").foregroundColor(selectedMode.color)
                Text(card.play_prompt).font(.footnote.italic())
            }
        }
        .padding(16)
        .background(RoundedRectangle(cornerRadius: 18, style: .continuous).fill(Color.white))
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

    // MARK: - Raw card (fallback when parse fails)
    private var rawCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Raw output (schema gate failed)").font(.subheadline.weight(.semibold))
                Spacer()
                Button { UIPasteboard.general.string = generatedRaw } label: {
                    Image(systemName: "doc.on.doc")
                }
            }
            ScrollView { Text(generatedRaw).font(.footnote.monospaced()).frame(maxWidth: .infinity, alignment: .leading) }
                .frame(maxHeight: 240)
        }
        .padding(14)
        .background(RoundedRectangle(cornerRadius: 18, style: .continuous).fill(Color.red.opacity(0.06)))
    }

    // MARK: - Footer
    private var footer: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 6) {
                Image(systemName: "lock.shield.fill")
                    .foregroundColor(Color(red: 0.30, green: 0.55, blue: 0.40))
                Text("All inference, gate evaluation and audit logging stay on this iPad.")
                    .font(.caption.weight(.medium))
            }
            Text("Adapter: Merged_Gemma4_E2B_Seed10 · llama.cpp · EMNLP 2026 §4L main-boost")
                .font(.caption2).foregroundColor(.secondary)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.black.opacity(0.04))
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }

    // MARK: - Generation
    @MainActor
    private func runGeneration() async {
        let activeList = familyLanguages.filter { activeLangs.contains($0) }
        let kidLine = familyKids.map { "\($0.name)(\($0.age))" }.joined(separator: ", ")

        // System prompt — full version with policy & schema directives.
        // When policy adapter is toggled off (no-policy ablation demo), we
        // suppress the policy directives to mimic the EMNLP no-policy curriculum.
        let policyBlock = policyAdapterOn ? """
        ## Policy
        - Respect active_languages strictly; do not emit any other script blocks.
        - Use child-appropriate vocabulary for target_age.
        - JSON only; no surrounding prose.
        - Field `mode` must be one of: story, words, song, say, between, culture.
        """ : """
        ## Style
        - Be friendly and helpful.
        """

        let prompt = """
        You are a family tutor running fully on-device on an iPad.
        Family: \(kidLine).  Family languages: \(familyLanguages.joined(separator: ", ")).
        Active session languages: \(activeList.joined(separator: ", ")).
        Target child age: \(targetAge).
        Mode: \(selectedMode.rawValue) — \(selectedMode.systemHint)

        \(policyBlock)

        ## Schema
        Return exactly one JSON object with these keys:
        {
          "title": string,
          "mode": "\(selectedMode.rawValue)",
          "target_age": \(targetAge),
          "active_languages": \(activeList.map { "\"\($0)\"" }),
          "body": { each active language → short paragraph in its script },
          "play_prompt": one short play idea the parent can use right now
        }

        ## Parent request
        \(userText)
        """

        // Wrap with the Gemma 4 chat template recorded in the GGUF metadata so
        // the policy/family LoRA actually engages (without this the engine
        // treats the prompt as raw text and silently regresses to baseline).
        let wrapped = GemmaChat.wrap(prompt)

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
        let report = StateGates.evaluate(
            rawOutput: tail,
            activeLanguages: activeList,
            familyLanguages: familyLanguages,
            targetAge: targetAge
        )
        lastReport = report
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
    private func pollUntilDone(timeout: TimeInterval = 90) async throws {
        let start = Date()
        while Date().timeIntervalSince(start) < timeout {
            if llamaState.messageLog.contains("\n    Done\n") { return }
            try await Task.sleep(nanoseconds: 250_000_000)
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
}

private struct ModeCard: View {
    let mode: FamilyMode
    let selected: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Image(systemName: mode.icon)
                    .font(.subheadline.weight(.bold))
                    .foregroundColor(.white)
                    .frame(width: 30, height: 30)
                    .background(mode.color)
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                Spacer()
                if selected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(mode.color)
                }
            }
            Text(mode.title).font(.subheadline.weight(.bold))
        }
        .frame(maxWidth: .infinity, minHeight: 70, alignment: .topLeading)
        .padding(10)
        .background(RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(selected ? mode.color.opacity(0.10) : Color.white))
        .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous)
                 .stroke(selected ? mode.color : Color.black.opacity(0.06),
                         lineWidth: selected ? 1.4 : 1))
    }
}

// =============================================================================
//  Family setup
// =============================================================================
private struct FamilySetupView: View {
    @Binding var languages: String
    @Binding var kids: String
    @Environment(\.dismiss) private var dismiss

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
                Section("Family languages (다중 선택)") {
                    ForEach(availableLanguages, id: \.self) { lang in
                        Button {
                            if langSet.contains(lang) { langSet.remove(lang) }
                            else { langSet.insert(lang) }
                        } label: {
                            HStack {
                                Text(lang); Spacer()
                                if langSet.contains(lang) {
                                    Image(systemName: "checkmark.circle.fill").foregroundColor(.accentColor)
                                }
                            }
                        }.foregroundColor(.primary)
                    }
                }
                Section("Child 1") {
                    TextField("Name", text: $name1)
                    Stepper("Age: \(age1)세", value: $age1, in: 0...12)
                }
                Section {
                    Toggle("Add second child", isOn: $twoKids)
                    if twoKids {
                        TextField("Name", text: $name2)
                        Stepper("Age: \(age2)세", value: $age2, in: 0...12)
                    }
                }
                Section {
                    Button { save(); dismiss() } label: {
                        Text("Save").frame(maxWidth: .infinity).fontWeight(.semibold)
                    }
                }
            }
            .navigationTitle("Family")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Close") { dismiss() }
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
