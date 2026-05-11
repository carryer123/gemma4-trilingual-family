import AVFoundation

/// Sequential 3-language TTS queue mirroring Android TtsManager.
/// AVSpeechSynthesizer queues utterances natively; we just set the right voice
/// per item and await the delegate callback before scheduling the next.
@MainActor
final class TtsManager: NSObject, AVSpeechSynthesizerDelegate {
    static let shared = TtsManager()

    private let synth = AVSpeechSynthesizer()
    private var continuations: [String: CheckedContinuation<Void, Never>] = [:]

    enum Lang: String { case ko = "ko-KR", ru = "ru-RU", en = "en-US", fr = "fr-FR"
        static func forCode(_ code: String) -> Lang {
            switch code {
            case "ko": return .ko; case "ru": return .ru; case "fr": return .fr; default: return .en
            }
        }
    }

    override init() {
        super.init()
        synth.delegate = self
    }

    func speakOne(_ text: String, lang: Lang) async {
        guard !text.isEmpty else { return }
        let u = AVSpeechUtterance(string: text)
        u.voice = AVSpeechSynthesisVoice(language: lang.rawValue) ?? AVSpeechSynthesisVoice(language: "en-US")
        u.rate = AVSpeechUtteranceDefaultSpeechRate * 0.95
        let key = UUID().uuidString
        await withCheckedContinuation { (cont: CheckedContinuation<Void, Never>) in
            continuations[key] = cont
            (u as NSObject).setValue(key, forKey: "trilingualKey")  // see speechSynthesizer(_:didFinish:)
            synth.speak(u)
        }
    }

    func speakAll(ko: String?, ru: String?, en: String?) async {
        if let s = ko { await speakOne(s, lang: .ko) }
        if let s = ru { await speakOne(s, lang: .ru) }
        if let s = en { await speakOne(s, lang: .en) }
    }

    /// Speak in the given order using `byLang[code]` for each active code.
    func speakActive(_ byLang: [String: String], active: [String]) async {
        for code in active {
            if let s = byLang[code], !s.isEmpty {
                await speakOne(s, lang: Lang.forCode(code))
            }
        }
    }

    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didFinish utterance: AVSpeechUtterance) {
        let key = (utterance as NSObject).value(forKey: "trilingualKey") as? String
        Task { @MainActor in
            if let k = key, let c = self.continuations.removeValue(forKey: k) { c.resume() }
        }
    }
}
