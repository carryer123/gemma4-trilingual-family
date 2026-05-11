import Foundation
import Combine

@MainActor
final class AppState: ObservableObject {
    static let shared = AppState()
    @Published var family: FamilySetup
    @Published var vocab: [FamilyWord]
    @Published var recentDailyKorean: [String]

    init() {
        self.family = Persistence.loadFamily()
        self.vocab = Persistence.loadVocab()
        self.recentDailyKorean = Persistence.loadRecent()
    }

    func saveFamily() { Persistence.saveFamily(family) }
    func saveVocab() { Persistence.saveVocab(vocab) }
    func saveRecent() { Persistence.saveRecent(recentDailyKorean) }
}
