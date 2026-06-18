import Foundation

struct UserProfile: Codable {
    var age: String = "25"
    var gender: Gender = .male
    var height: String = "175"
    var weight: String = "70"
    var systolicPressure: String = "120"
    var diastolicPressure: String = "80"
    var restingHr: String = "65"
    var activeHr: String = "130"
    var hasDiseases: Bool = false
    var selectedConditions: Set<String> = []
    var selectedGenres: Set<String> = []

    private static let storageKey = "heartbeat_user_profile"

    var isValidForSession: Bool {
        guard let ageInt = Int(age), ageInt >= 5, ageInt <= 100,
              let resting = Int(restingHr), resting >= 40, resting <= 120 else {
            return false
        }
        return true
    }

    func toAPIProfile() -> APIProfile {
        APIProfile(
            age: Int(age) ?? 25,
            restingHr: Int(restingHr) ?? 65,
            avgActiveHr: Int(activeHr),
            preferredGenres: Array(selectedGenres),
            conditions: Array(selectedConditions)
        )
    }

    static func load() -> UserProfile {
        guard let data = UserDefaults.standard.data(forKey: storageKey),
              let profile = try? JSONDecoder().decode(UserProfile.self, from: data) else {
            return UserProfile()
        }
        return profile
    }

    func save() {
        if let data = try? JSONEncoder().encode(self) {
            UserDefaults.standard.set(data, forKey: Self.storageKey)
        }
    }
}

struct SessionSettings: Codable {
    var activityType: ActivityType = .running
    var goal: GoalType = .generalFitness
    var tempoPreference: TempoPreference = .medium

    func toAPIContext() -> APISessionContext {
        APISessionContext(
            activityType: activityType,
            goal: goal,
            tempoPreference: tempoPreference
        )
    }
}

/// Один сгенерированный отрывок + вспомогательные файлы для переходов
struct MusicFragment: Equatable {
    let title: String
    let genre: String
    let bpm: Int
    let mood: String
    let fragmentIndex: Int
    let fragmentURL: URL
    let fragmentDuration: Int
    let transitionURL: URL?
    let transitionDuration: Int
    let loopBridgeURL: URL?
    let loopBridgeDuration: Int

    init(from response: GenerateResponse, baseURL: String) {
        title = response.trackTitle
        genre = response.genre
        bpm = response.bpm
        mood = response.mood
        fragmentIndex = response.fragmentIndex
        fragmentDuration = response.durationSeconds
        transitionDuration = response.transitionDurationSeconds
        loopBridgeDuration = response.loopBridgeDurationSeconds

        fragmentURL = Self.makeURL(response.audioUrl, baseURL: baseURL)
        transitionURL = response.transitionAudioUrl.map { Self.makeURL($0, baseURL: baseURL) }
        loopBridgeURL = response.loopBridgeUrl.map { Self.makeURL($0, baseURL: baseURL) }
    }

    private static func makeURL(_ path: String, baseURL: String) -> URL {
        if path.hasPrefix("http") {
            return URL(string: path)!
        }
        return URL(string: baseURL + path)!
    }
}

/// Для UI-плеера на главном экране
struct CurrentTrack: Equatable {
    let title: String
    let genre: String
    let bpm: Int
    let mood: String
    let fragmentIndex: Int

    init(from fragment: MusicFragment) {
        title = fragment.title
        genre = fragment.genre
        bpm = fragment.bpm
        mood = fragment.mood
        fragmentIndex = fragment.fragmentIndex
    }
}
