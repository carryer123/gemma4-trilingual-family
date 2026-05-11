import Foundation
import UserNotifications

@MainActor
enum NotificationManager {
    static func requestAndScheduleDaily() async {
        let center = UNUserNotificationCenter.current()
        let granted = (try? await center.requestAuthorization(options: [.alert, .sound, .badge])) ?? false
        guard granted else { return }

        let content = UNMutableNotificationContent()
        content.title = "Today's family phrase 🌅"
        content.body = "Open Trilingual Family for your KO/RU/EN phrase of the day."
        content.sound = .default

        var date = DateComponents()
        date.hour = 8
        date.minute = 0
        let trigger = UNCalendarNotificationTrigger(dateMatching: date, repeats: true)
        let req = UNNotificationRequest(identifier: "daily_phrase_8am", content: content, trigger: trigger)
        try? await center.add(req)
    }
}
