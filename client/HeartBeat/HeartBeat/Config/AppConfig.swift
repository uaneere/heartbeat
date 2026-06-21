import Foundation

enum AppConfig {

    static let apiBaseURL = "http://88.204.68.180:8000"

    static let heartRatePollInterval: TimeInterval = 3.0
    /// Crossfade на сервере (см. MUSICGEN_CROSSFADE), для справки
    static let crossfadeDuration: TimeInterval = 2.0
}
