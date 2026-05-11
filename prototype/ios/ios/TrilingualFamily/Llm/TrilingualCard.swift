import Foundation

struct TrilingualCard: Codable {
    let object: String
    let korean: String
    let russian: String
    let english: String
    let l1Note: String
    let pronunciationAid: String
    let ageBand: String
    let safetyFlag: String

    enum CodingKeys: String, CodingKey {
        case object, korean, russian, english
        case l1Note = "l1_note"
        case pronunciationAid = "pronunciation_aid"
        case ageBand = "age_band"
        case safetyFlag = "safety_flag"
    }

    static func parse(_ raw: String) -> TrilingualCard? {
        guard let start = raw.firstIndex(of: "{"),
              let end = raw.lastIndex(of: "}"),
              start < end else { return nil }
        let json = String(raw[start...end])
        return try? JSONDecoder().decode(TrilingualCard.self, from: Data(json.utf8))
    }
}
