import Foundation

enum AppConfig {
    /// Для симулятора — localhost. На реальном устройстве замените на IP вашего компьютера в локальной сети.
    static let apiBaseURL = "http://127.0.0.1:8000"

    static let heartRatePollInterval: TimeInterval = 3.0
    static let prefetchBeforeEnd: TimeInterval = 8.0
}
