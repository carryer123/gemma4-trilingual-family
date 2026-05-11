import Foundation
import MediaPipeTasksGenAI
import MediaPipeTasksGenAIC

/// On-device Gemma 4 E2B via MediaPipe LLM Inference.
/// Loads the same `gemma-4-E2B-it-merged.task` artifact that ships in the
/// Android sibling app — single conversion pipeline, single artifact.
///
/// The .task file is bundled in the app's main bundle (Resources). On first
/// launch it is copied to Application Support so MediaPipe can mmap it.
final class MediaPipeBackend: LlmBackend {
    private var llm: LlmInference?

    func initialize() async throws {
        let modelPath = try ensureModelOnDisk()
        let options = LlmInference.Options(modelPath: modelPath)
        options.maxTokens = 2048
        options.maxTopK = 64
        // For LoRA hot-swap (currently unused — we ship merged):
        // options.loraPath = Bundle.main.path(forResource: "lora_v2", ofType: "bin")
        self.llm = try LlmInference(options: options)
    }

    func generate(prompt: String, maxTokens: Int, temperature: Float) async throws -> String {
        guard let llm = llm else { throw NSError(domain: "Llm", code: 1, userInfo: [NSLocalizedDescriptionKey: "not initialized"]) }
        return try llm.generateResponse(inputText: prompt)
    }

    func close() {
        llm = nil
    }

    private func ensureModelOnDisk() throws -> String {
        let fm = FileManager.default
        let appSupport = try fm.url(for: .applicationSupportDirectory, in: .userDomainMask, appropriateFor: nil, create: true)
        let modelDir = appSupport.appendingPathComponent("models", isDirectory: true)
        try fm.createDirectory(at: modelDir, withIntermediateDirectories: true)
        let dest = modelDir.appendingPathComponent("gemma-4-E2B-it-merged.task")
        if fm.fileExists(atPath: dest.path) {
            return dest.path
        }
        guard let bundled = Bundle.main.url(forResource: "gemma-4-E2B-it-merged", withExtension: "task") else {
            throw NSError(
                domain: "Llm", code: 2,
                userInfo: [NSLocalizedDescriptionKey: "gemma-4-E2B-it-merged.task not bundled. Drag it into the Xcode project (Resources, target = TrilingualFamily, no compression)."]
            )
        }
        try fm.copyItem(at: bundled, to: dest)
        return dest.path
    }
}
