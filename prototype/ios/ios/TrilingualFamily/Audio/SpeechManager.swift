import Foundation
import Speech
import AVFoundation

/// Single-shot on-device speech-to-text.
/// User taps "listen", we record ~3 s, return the top final hypothesis.
@MainActor
final class SpeechManager {
    static let shared = SpeechManager()

    enum Lang: String { case ko = "ko-KR", ru = "ru-RU", en = "en-US" }

    func listenOnce(lang: Lang = .ko, seconds: TimeInterval = 3.0) async -> String? {
        let auth = await requestAuth()
        guard auth else { return nil }
        guard let recognizer = SFSpeechRecognizer(locale: Locale(identifier: lang.rawValue)),
              recognizer.isAvailable else { return nil }
        let audioEngine = AVAudioEngine()
        let request = SFSpeechAudioBufferRecognitionRequest()
        request.shouldReportPartialResults = false
        if #available(iOS 13.0, *) { request.requiresOnDeviceRecognition = true }

        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.record, mode: .measurement, options: .duckOthers)
        try? session.setActive(true, options: .notifyOthersOnDeactivation)

        let node = audioEngine.inputNode
        let format = node.outputFormat(forBus: 0)
        node.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in
            request.append(buffer)
        }
        audioEngine.prepare()
        try? audioEngine.start()

        return await withCheckedContinuation { (cont: CheckedContinuation<String?, Never>) in
            var resumed = false
            let task = recognizer.recognitionTask(with: request) { result, error in
                if resumed { return }
                if let r = result, r.isFinal {
                    resumed = true
                    cont.resume(returning: r.bestTranscription.formattedString)
                } else if error != nil {
                    resumed = true
                    cont.resume(returning: nil)
                }
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + seconds) {
                request.endAudio()
                audioEngine.stop()
                node.removeTap(onBus: 0)
                if !resumed {
                    resumed = true
                    task.cancel()
                    cont.resume(returning: nil)
                }
            }
        }
    }

    private func requestAuth() async -> Bool {
        await withCheckedContinuation { (cont: CheckedContinuation<Bool, Never>) in
            SFSpeechRecognizer.requestAuthorization { status in
                AVAudioSession.sharedInstance().requestRecordPermission { ok in
                    cont.resume(returning: status == .authorized && ok)
                }
            }
        }
    }
}
