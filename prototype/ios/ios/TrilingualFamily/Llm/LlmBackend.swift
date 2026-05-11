import Foundation

protocol LlmBackend: AnyObject {
    func initialize() async throws
    func generate(prompt: String, maxTokens: Int, temperature: Float) async throws -> String
    func close()
}

extension LlmBackend {
    func generate(prompt: String) async throws -> String {
        try await generate(prompt: prompt, maxTokens: 512, temperature: 0.3)
    }
}

@MainActor
final class LlmStore: ObservableObject {
    enum Status { case notLoaded, loading, ready, error(String) }

    @Published private(set) var status: Status = .notLoaded
    private let backend: LlmBackend = MediaPipeBackend()

    var statusText: String {
        switch status {
        case .notLoaded: return "not loaded"
        case .loading: return "loading"
        case .ready: return "ready"
        case .error(let m): return "error: \(m)"
        }
    }

    func initialize() async {
        status = .loading
        do {
            try await backend.initialize()
            status = .ready
        } catch {
            status = .error(String(describing: error))
        }
    }

    func generate(prompt: String) async throws -> String {
        try await backend.generate(prompt: prompt)
    }

    deinit { backend.close() }
}
