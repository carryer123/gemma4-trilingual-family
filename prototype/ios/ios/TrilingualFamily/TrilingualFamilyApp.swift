import SwiftUI

@main
struct TrilingualFamilyApp: App {
    @StateObject private var llmStore = LlmStore()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(llmStore)
                .task { await llmStore.initialize() }
        }
    }
}
