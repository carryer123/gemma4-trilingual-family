import SwiftUI

struct ContentView: View {
    @EnvironmentObject var llmStore: LlmStore
    @StateObject private var state = AppState.shared
    @State private var setupDone: Bool = AppState.shared.family.childName != "the child"

    var body: some View {
        Group {
            switch llmStore.status {
            case .ready:
                if setupDone { RootTabView() }
                else { FamilySetupScreen(onDone: { setupDone = true }) }
            case .loading:
                VStack(spacing: 16) {
                    ProgressView()
                    Text("Loading on-device Gemma 4 E2B…")
                }
            case .notLoaded:
                Text("preparing…").onAppear { Task { await llmStore.initialize() } }
            case .error(let m):
                VStack(alignment: .leading, spacing: 8) {
                    Text("Could not load model").font(.headline)
                    Text(m).font(.caption).foregroundStyle(.secondary)
                    Button("retry") { Task { await llmStore.initialize() } }
                        .buttonStyle(.borderedProminent)
                }.padding()
            }
        }
        .task { await NotificationManager.requestAndScheduleDaily() }
    }
}
