import Foundation

/// UserDefaults-backed JSON persistence.
/// Swap to SwiftData if vocab grows large.
enum Persistence {
    private static let familyKey = "trilingual.family"
    private static let vocabKey  = "trilingual.vocab"
    private static let recentKey = "trilingual.recent"

    private static let enc = JSONEncoder()
    private static let dec = JSONDecoder()

    static func loadFamily() -> FamilySetup {
        guard let d = UserDefaults.standard.data(forKey: familyKey),
              let f = try? dec.decode(FamilySetup.self, from: d) else { return FamilySetup() }
        return f
    }
    static func saveFamily(_ f: FamilySetup) {
        if let d = try? enc.encode(f) { UserDefaults.standard.set(d, forKey: familyKey) }
    }

    static func loadVocab() -> [FamilyWord] {
        guard let d = UserDefaults.standard.data(forKey: vocabKey),
              let v = try? dec.decode([FamilyWord].self, from: d) else { return [] }
        return v
    }
    static func saveVocab(_ v: [FamilyWord]) {
        if let d = try? enc.encode(v) { UserDefaults.standard.set(d, forKey: vocabKey) }
    }

    static func loadRecent() -> [String] {
        UserDefaults.standard.stringArray(forKey: recentKey) ?? []
    }
    static func saveRecent(_ r: [String]) {
        UserDefaults.standard.set(Array(r.prefix(7)), forKey: recentKey)
    }
}
