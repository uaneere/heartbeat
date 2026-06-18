import Foundation

enum AppConfig {
    /// Для симулятора — localhost. На реальном устройстве замените на IP вашего компьютера в локальной сети.
    static let apiBaseURL = "http://127.0.0.1:8000"

    static let heartRatePollInterval: TimeInterval = 3.0
    /// Crossfade на сервере (см. MUSICGEN_CROSSFADE), для справки
    static let crossfadeDuration: TimeInterval = 2.0
}
