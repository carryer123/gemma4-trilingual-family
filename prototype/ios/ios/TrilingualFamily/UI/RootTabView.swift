import SwiftUI

struct RootTabView: View {
    @EnvironmentObject var llmStore: LlmStore

    var body: some View {
        TabView {
            ObjectCardScreen()
                .tabItem { Label("Card", systemImage: "camera.fill") }
            BedtimeStoryScreen()
                .tabItem { Label("Story", systemImage: "moon.stars.fill") }
            DailyPhraseScreen()
                .tabItem { Label("Daily", systemImage: "sun.max.fill") }
            FamilyWordScreen()
                .tabItem { Label("Family", systemImage: "person.3.fill") }
            PronunciationGameScreen()
                .tabItem { Label("Game", systemImage: "mic.fill") }
            MealtimeScreen()
                .tabItem { Label("Meal", systemImage: "fork.knife") }
        }
    }
}
