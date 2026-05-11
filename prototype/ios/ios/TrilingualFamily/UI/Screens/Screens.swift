import SwiftUI

private struct ScreenScaffold<Body: View>: View {
    let title: String
    let body_: () -> Body
    init(_ title: String, @ViewBuilder body: @escaping () -> Body) { self.title = title; self.body_ = body }
    var body: some View {
        NavigationStack {
            ScrollView { VStack(alignment: .leading, spacing: 12) { body_() }.padding() }
                .navigationTitle(title)
        }
    }
}

private struct CardBox<Body: View>: View {
    let body_: () -> Body
    init(@ViewBuilder body: @escaping () -> Body) { self.body_ = body }
    var body: some View {
        VStack(alignment: .leading, spacing: 6) { body_() }
            .padding()
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(RoundedRectangle(cornerRadius: 12).fill(Color.secondary.opacity(0.08)))
    }
}

private func ttsLangFor(_ s: String) -> TtsManager.Lang {
    for u in s.unicodeScalars {
        if (0xAC00...0xD7AF).contains(u.value) { return .ko }
        if (0x0400...0x04FF).contains(u.value) { return .ru }
    }
    if s.contains(where: { "àâäçéèêëîïôöùûüÿœæ".contains($0) }) { return .fr }
    return .en
}

private func detectSpeechLang(_ s: String) -> SpeechManager.Lang {
    for u in s.unicodeScalars {
        if (0xAC00...0xD7AF).contains(u.value) { return .ko }
        if (0x0400...0x04FF).contains(u.value) { return .ru }
    }
    return .en
}

// MARK: - Family setup
struct FamilySetupScreen: View {
    @StateObject private var state = AppState.shared
    var onDone: () -> Void
    @State private var name = ""
    @State private var age = "0-2"
    @State private var bridge = "en"
    @State private var langs: [String] = ["ko", "ru", "en"]

    var body: some View {
        ScreenScaffold("👋 Tell me about your family") {
            Text("Stays on this phone. Nothing leaves the device.").font(.caption)
            TextField("child's name (or nickname)", text: $name).textFieldStyle(.roundedBorder)

            Text("Child age band").font(.subheadline)
            HStack {
                ForEach(["0-2", "3-5", "6-8"], id: \.self) { a in
                    Button(a) { age = a }.buttonStyle(.bordered).tint(age == a ? .accentColor : .secondary)
                }
            }

            Text("Languages at home (pick exactly 3)").font(.subheadline)
            HStack {
                ForEach(Lang.all, id: \.self) { code in
                    let on = langs.contains(code)
                    Button(Lang.label(code)) {
                        if on { langs.removeAll { $0 == code } }
                        else if langs.count < 3 { langs.append(code) }
                    }
                    .buttonStyle(.bordered).tint(on ? .accentColor : .secondary)
                }
            }

            Text("Bridge language (parent narration)").font(.subheadline)
            HStack {
                ForEach(langs, id: \.self) { code in
                    Button(Lang.label(code)) { bridge = code }
                        .buttonStyle(.bordered).tint(bridge == code ? .accentColor : .secondary)
                }
            }

            Button("start") {
                guard langs.count == 3, langs.contains(bridge) else { return }
                let mode = (age == "0-2") ? "baby_0_2" : (age == "3-5" ? "child_3_6" : "parent_bridge")
                state.family.childName = name.isEmpty ? "the child" : name
                state.family.ageBand = age; state.family.mode = mode
                state.family.bridge = bridge; state.family.householdLanguages = langs
                state.saveFamily()
                onDone()
            }
            .buttonStyle(.borderedProminent)
            .disabled(langs.count != 3 || !langs.contains(bridge))
        }
        .onAppear {
            name = state.family.childName == "the child" ? "" : state.family.childName
            age = state.family.ageBand
            bridge = state.family.bridge
            langs = state.family.householdLanguages
        }
    }
}

// MARK: - Object → family card
struct ObjectCardScreen: View {
    @EnvironmentObject var llm: LlmStore
    @StateObject private var state = AppState.shared
    @State private var input = "apple"
    @State private var card: FamilyCard?
    @State private var busy = false
    @State private var cameraOn = false
    var body: some View {
        ScreenScaffold("📷 Object → Card") {
            Text("Languages: " + state.family.householdLanguages.map(Lang.label).joined(separator: " · "))
                .font(.caption)
            TextField("object (or use camera)", text: $input).textFieldStyle(.roundedBorder)
            HStack {
                Button(cameraOn ? "stop camera" : "use camera") { cameraOn.toggle() }.buttonStyle(.bordered)
                Button(busy ? "thinking…" : "generate card") {
                    busy = true
                    Task {
                        let raw = (try? await llm.generate(prompt: PromptLibrary.objectCard(
                            object: input, family: state.family, vocab: state.vocab))) ?? ""
                        card = Schemas.parse(raw); busy = false
                    }
                }
                .buttonStyle(.borderedProminent).disabled(busy)
            }
            if cameraOn {
                CameraPreviewView(onLabel: { input = $0 }, isPaused: false)
                    .frame(height: 280).clipShape(RoundedRectangle(cornerRadius: 12))
                Text("Live label → \"\(input)\"").font(.caption)
            }
            if let c = card {
                CardBox {
                    Text("mode: \(c.mode ?? "") · age: \(c.ageBand ?? "")")
                    Text("active: \(c.activeLanguages?.joined(separator: " / ") ?? "")")
                    Divider()
                    if case .some(let v) = c.card?.value as? [String: Any] {
                        ForEach(Array(v.keys.sorted()), id: \.self) { k in
                            Text("\(k): \(String(describing: v[k] ?? ""))")
                        }
                    }
                    Text("next: \(c.nextAction ?? "")")
                    if let s = c.safety {
                        Text("safe: \(s.childSafe) · privacy: \(s.noPrivateData)").font(.caption)
                    }
                    if let dict = c.card?.value as? [String: Any] {
                        let active = c.activeLanguages ?? state.family.householdLanguages
                        let phrases: [String: String] = active.reduce(into: [:]) { acc, code in
                            if let s = dict[code] as? String { acc[code] = s }
                        }
                        if !phrases.isEmpty {
                            Button("🔊 read aloud (\(active.joined(separator: " → ")))") {
                                Task { await TtsManager.shared.speakActive(phrases, active: active) }
                            }.buttonStyle(.borderedProminent)
                        }
                    }
                }
            }
        }
    }
}

// MARK: - F1 bedtime story
struct BedtimeStoryScreen: View {
    @EnvironmentObject var llm: LlmStore
    @StateObject private var state = AppState.shared
    @State private var keyword = "the moon"
    @State private var story: BedtimeStory?
    @State private var busy = false
    var body: some View {
        ScreenScaffold("🌙 Bedtime Story") {
            TextField("topic / object", text: $keyword).textFieldStyle(.roundedBorder)
            Button(busy ? "weaving…" : "make a 60-second story") {
                busy = true
                Task {
                    let raw = (try? await llm.generate(prompt: PromptLibrary.bedtimeStory(
                        keyword: keyword, family: state.family, vocab: state.vocab))) ?? ""
                    story = Schemas.parse(raw); busy = false
                }
            }
            .buttonStyle(.borderedProminent).disabled(busy)
            if let s = story {
                ForEach(state.family.householdLanguages, id: \.self) { code in
                    paragraphCard(Lang.label(code), paras: s.paragraphsByLang?[code] ?? [])
                }
                Button("🔊 read aloud (\(state.family.householdLanguages.joined(separator: " → ")))") {
                    Task {
                        for code in state.family.householdLanguages {
                            for p in s.paragraphsByLang?[code] ?? [] {
                                await TtsManager.shared.speakOne(p, lang: TtsManager.Lang.forCode(code))
                            }
                        }
                    }
                }.buttonStyle(.borderedProminent)
            }
        }
    }
    private func paragraphCard(_ lang: String, paras: [String]) -> some View {
        Group {
            if !paras.isEmpty {
                CardBox { Text(lang).font(.title3.bold()); ForEach(paras, id: \.self) { Text($0) } }
            }
        }
    }
}

// MARK: - F2 daily phrase
struct DailyPhraseScreen: View {
    @EnvironmentObject var llm: LlmStore
    @StateObject private var state = AppState.shared
    @State private var phrase: DailyPhrase?
    @State private var busy = false
    var body: some View {
        ScreenScaffold("📱 Today's Phrase") {
            Button(busy ? "picking…" : "today's phrase") {
                busy = true
                Task {
                    let date = ISO8601DateFormatter.string(from: Date(), timeZone: .current, formatOptions: [.withFullDate])
                    let raw = (try? await llm.generate(prompt: PromptLibrary.dailyPhrase(
                        date: date, family: state.family, recent: state.recentDailyKorean, vocab: state.vocab))) ?? ""
                    let p: DailyPhrase? = Schemas.parse(raw)
                    phrase = p
                    if let first = state.family.householdLanguages.first,
                       let s = p?.phraseByLang?[first], !s.isEmpty {
                        state.recentDailyKorean.insert(s, at: 0)
                        state.recentDailyKorean = Array(state.recentDailyKorean.prefix(7))
                        state.saveRecent()
                    }
                    busy = false
                }
            }
            .buttonStyle(.borderedProminent).disabled(busy)
            if let p = phrase {
                CardBox {
                    ForEach(state.family.householdLanguages, id: \.self) { code in
                        Text("\(Lang.label(code))  \(p.phraseByLang?[code] ?? "")")
                    }
                    Divider()
                    Text("Situation: \(p.situation ?? "")")
                    Text("Mission: \(p.mission ?? "")").font(.headline)
                    let hints = state.family.householdLanguages.map { "\($0.uppercased()) \(p.pronunciationHintsByLang?[$0] ?? "")" }.joined(separator: " · ")
                    Text("Pronounce: \(hints)").font(.caption)
                    Button("🔊 read aloud") {
                        Task { await TtsManager.shared.speakActive(p.phraseByLang ?? [:], active: state.family.householdLanguages) }
                    }.buttonStyle(.borderedProminent)
                }
            }
        }
    }
}

// MARK: - F3 family word list
struct FamilyWordScreen: View {
    @EnvironmentObject var llm: LlmStore
    @StateObject private var state = AppState.shared
    @State private var ko = ""; @State private var ru = ""; @State private var en = ""; @State private var fr = ""; @State private var note = ""
    var body: some View {
        let active = state.family.householdLanguages
        ScreenScaffold("👤 Our Family's Words") {
            Text("Saved on this phone only. Used in every prompt:").font(.subheadline)
            ForEach(state.vocab) { w in
                CardBox {
                    Text(w.toPromptLine(active: active)).font(.title3)
                    if !w.note.isEmpty { Text(w.note).font(.caption) }
                }
            }
            Divider()
            if active.contains("ko") { TextField("KO", text: $ko).textFieldStyle(.roundedBorder) }
            if active.contains("ru") { TextField("RU", text: $ru).textFieldStyle(.roundedBorder) }
            if active.contains("en") { TextField("EN", text: $en).textFieldStyle(.roundedBorder) }
            if active.contains("fr") { TextField("FR", text: $fr).textFieldStyle(.roundedBorder) }
            TextField("note (optional)", text: $note).textFieldStyle(.roundedBorder)
            Button("save to family vocab") {
                guard ![ko, ru, en, fr].allSatisfy({ $0.isEmpty }) else { return }
                state.vocab.append(FamilyWord(ko: ko, ru: ru, en: en, fr: fr, note: note))
                state.saveVocab()
                ko = ""; ru = ""; en = ""; fr = ""; note = ""
            }.buttonStyle(.borderedProminent)
        }
    }
}

// MARK: - F4 pronunciation game
struct PronunciationGameScreen: View {
    @EnvironmentObject var llm: LlmStore
    @StateObject private var state = AppState.shared
    @State private var target = "사과"
    @State private var heard = ""
    @State private var verdict: PronunciationVerdict?
    @State private var busy = false
    var body: some View {
        ScreenScaffold("🎤 Pronunciation Game") {
            TextField("target word", text: $target).textFieldStyle(.roundedBorder)
            HStack {
                Button("🎙 listen") {
                    Task { heard = await SpeechManager.shared.listenOnce(lang: detectSpeechLang(target)) ?? "" }
                }.buttonStyle(.bordered)
                Button(busy ? "judging…" : "score") {
                    busy = true
                    Task {
                        let raw = (try? await llm.generate(prompt: PromptLibrary.pronunciation(
                            target: target, heard: heard, family: state.family))) ?? ""
                        verdict = Schemas.parse(raw); busy = false
                    }
                }
                .buttonStyle(.borderedProminent).disabled(busy || heard.isEmpty)
            }
            if !heard.isEmpty { Text("heard: \"\(heard)\"").font(.caption) }
            if let v = verdict {
                CardBox {
                    let s = v.score ?? 0
                    Text(String(repeating: "★", count: s) + String(repeating: "☆", count: max(3 - s, 0)))
                        .font(.largeTitle)
                    Text(v.encouragement ?? "")
                    Text(v.retryHint ?? "").font(.caption)
                }
            }
        }
    }
}

// MARK: - F5 mealtime mode
struct MealtimeScreen: View {
    @EnvironmentObject var llm: LlmStore
    @StateObject private var state = AppState.shared
    @State private var running = false
    @State private var lastObject: String?
    @State private var lastNar: MealtimeNarration?
    @State private var startedAt = Date()
    @State private var now = Date()
    private let timer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()

    var body: some View {
        ScreenScaffold("🍎 Mealtime (5 min auto)") {
            HStack {
                Button(running ? "stop" : "start 5-min meal") {
                    if !running { startedAt = Date() }
                    running.toggle()
                }.buttonStyle(.borderedProminent)
                if running {
                    let remaining = max(0, 300 - Int(now.timeIntervalSince(startedAt)))
                    Text("\(remaining/60):\(String(format: "%02d", remaining%60))").font(.title3)
                }
            }
            .onReceive(timer) { _ in
                now = Date()
                if running, now.timeIntervalSince(startedAt) >= 300 { running = false }
            }
            if running {
                CameraPreviewView(onLabel: { lbl in
                    if lbl == lastObject { return }
                    lastObject = lbl
                    Task {
                        let raw = (try? await llm.generate(prompt: PromptLibrary.mealtimeNarration(
                            detected: lbl, family: state.family, vocab: state.vocab))) ?? ""
                        let n: MealtimeNarration? = Schemas.parse(raw)
                        lastNar = n
                        if let n = n {
                            await TtsManager.shared.speakActive(n.oneLinerByLang ?? [:], active: state.family.householdLanguages)
                        }
                    }
                }, isPaused: false)
                .frame(height: 260).clipShape(RoundedRectangle(cornerRadius: 12))
            }
            if let lo = lastObject { Text("now seeing: \(lo)").font(.caption) }
            if let n = lastNar {
                CardBox {
                    ForEach(state.family.householdLanguages, id: \.self) { code in
                        Text("\(Lang.label(code)) \(n.oneLinerByLang?[code] ?? "")")
                    }
                    Divider(); Text("👶 \(n.childQuestion ?? "")")
                }
            }
        }
    }
}
