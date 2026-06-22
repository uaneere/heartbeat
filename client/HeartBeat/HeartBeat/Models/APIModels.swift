import Foundation

// MARK: - API Enums

enum ActivityType: String, Codable, CaseIterable {
    case running, walking, gym, cycling, meditation, sleep, studying, yoga, gaming

    var displayName: String {
        switch self {
        case .running: return "Бег"
        case .walking: return "Ходьба"
        case .gym: return "Зал"
        case .cycling: return "Велосипед"
        case .meditation: return "Медитация"
        case .sleep: return "Сон"
        case .studying: return "Учёба"
        case .yoga: return "Йога"
        case .gaming: return "Игры"
        }
    }

    var icon: String {
        switch self {
        case .running: return "bolt.fill"
        case .walking: return "figure.walk"
        case .gym: return "dumbbell.fill"
        case .cycling: return "bicycle"
        case .meditation: return "brain.head.profile"
        case .sleep: return "moon.fill"
        case .studying: return "book.fill"
        case .yoga: return "laurel.leading"
        case .gaming: return "gamecontroller.fill"
        }
    }
}

enum GoalType: String, Codable, CaseIterable {
    case fatBurning = "fat_burning"
    case sprint
    case recovery
    case generalFitness = "general_fitness"
    case stressReduction = "stress_reduction"
    case warmup
    case cooldown

    var displayName: String {
        switch self {
        case .fatBurning: return "Жиросжигание"
        case .sprint: return "Спринт"
        case .recovery: return "Восстановление"
        case .generalFitness: return "Общая форма"
        case .stressReduction: return "Антистресс"
        case .warmup: return "Разминка"
        case .cooldown: return "Заминка"
        }
    }

    var icon: String {
        switch self {
        case .fatBurning: return "flame.fill"
        case .sprint: return "bolt.horizontal.fill"
        case .recovery: return "heart.fill"
        case .generalFitness: return "waveform.path.ecg"
        case .stressReduction: return "wind"
        case .warmup: return "sun.max.fill"
        case .cooldown: return "snowflake"
        }
    }
}

enum TempoPreference: String, Codable, CaseIterable {
    case slow, medium, fast

    var displayName: String {
        switch self {
        case .slow: return "Медленно"
        case .medium: return "Среднее"
        case .fast: return "Быстро"
        }
    }
}

enum EnergyLevel: String, Codable {
    case low, medium, high
}

// MARK: - Request / Response

struct APIProfile: Codable {
    var age: Int
    var restingHr: Int
    var preferredGenres: [String]
    var conditions: [String]

    enum CodingKeys: String, CodingKey {
        case age
        case restingHr = "resting_hr"
        case preferredGenres = "preferred_genres"
        case conditions
    }
}

struct APISessionContext: Codable {
    var activityType: ActivityType
    var goal: GoalType
    var tempoPreference: TempoPreference

    enum CodingKeys: String, CodingKey {
        case activityType = "activity_type"
        case goal
        case tempoPreference = "tempo_preference"
    }
}

struct StartSessionRequest: Codable {
    let profile: APIProfile
    let session: APISessionContext
}

struct StartSessionResponse: Codable {
    let sessionId: UUID
    let currentHr: Int
    let tick: Int
    let message: String

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case currentHr = "current_hr"
        case tick, message
    }
}

struct HeartRateUpdate: Codable {
    let currentHr: Int

    enum CodingKeys: String, CodingKey {
        case currentHr = "current_hr"
    }
}

struct HeartRateResponse: Codable {
    let success: Bool
    let tick: Int
    let currentHr: Int
    let heartRateZone: Int
    let heartRateZoneLabel: String
    let targetBpm: Int

    enum CodingKeys: String, CodingKey {
        case success, tick
        case currentHr = "current_hr"
        case heartRateZone = "heart_rate_zone"
        case heartRateZoneLabel = "heart_rate_zone_label"
        case targetBpm = "target_bpm"
    }
}

struct SessionStatusResponse: Codable {
    let sessionId: UUID
    let tick: Int
    let currentHr: Int
    let activityType: ActivityType
    let goal: GoalType
    let tempoPreference: TempoPreference
    let isActive: Bool
    let heartRateZone: Int
    let heartRateZoneLabel: String
    let targetBpm: Int
    let lastBpm: Int?
    let lastGenre: String?

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case tick
        case currentHr = "current_hr"
        case activityType = "activity_type"
        case goal
        case tempoPreference = "tempo_preference"
        case isActive = "is_active"
        case heartRateZone = "heart_rate_zone"
        case heartRateZoneLabel = "heart_rate_zone_label"
        case targetBpm = "target_bpm"
        case lastBpm = "last_bpm"
        case lastGenre = "last_genre"
    }
}

struct GenerateResponse: Codable {
    let success: Bool
    let audioUrl: String
    let bpm: Int
    let genre: String
    let energy: EnergyLevel
    let mood: String
    let trackTitle: String
    let durationSeconds: Int
    let tick: Int
    let fragmentFile: String
    let fragmentIndex: Int
    let heartRateZone: Int
    let heartRateZoneLabel: String
    let transitionAudioUrl: String?
    let transitionDurationSeconds: Int
    let loopBridgeUrl: String?
    let loopBridgeDurationSeconds: Int
    let chunkDurationSec: Double

    enum CodingKeys: String, CodingKey {
        case success
        case audioUrl = "audio_url"
        case bpm, genre, energy, mood
        case trackTitle = "track_title"
        case durationSeconds = "duration_seconds"
        case tick
        case fragmentFile = "fragment_file"
        case fragmentIndex = "fragment_index"
        case heartRateZone = "heart_rate_zone"
        case heartRateZoneLabel = "heart_rate_zone_label"
        case transitionAudioUrl = "transition_audio_url"
        case transitionDurationSeconds = "transition_duration_seconds"
        case loopBridgeUrl = "loop_bridge_url"
        case loopBridgeDurationSeconds = "loop_bridge_duration_seconds"
        case chunkDurationSec = "chunk_duration_sec"
    }
}

struct HealthResponse: Codable {
    let status: String
    let modelReady: Bool
    let modelKey: String
    let chunkDurationSec: Double
    let version: String

    enum CodingKeys: String, CodingKey {
        case status
        case modelReady = "model_ready"
        case modelKey = "model_key"
        case chunkDurationSec = "chunk_duration_sec"
        case version
    }
}

// MARK: - UI Mappings

enum GenreMapping {
    static let items: [(title: String, apiKey: String, imageName: String)] = [
        ("Классика", "classical", "classic"),
        ("Поп", "pop", "pop"),
        ("Рок", "rock", "rock"),
        ("Электроника", "electronic", "electro"),
        ("Джаз", "jazz", "jazz"),
        ("Lo-Fi", "lofi", "lofi"),
        ("Фонк", "phonk", "fonk"),
    ]
}

enum ConditionMapping {
    static let items: [(title: String, apiKey: String, effect: String)] = [
        ("Гипертония", "hypertension", "BPM ≤ 120, спокойная музыка"),
        ("Аритмия", "arrhythmia", "BPM ≤ 110, плавная смена темпа"),
        ("Бронхиальная астма", "asthma", "BPM ≤ 125"),
        ("Сахарный диабет", "diabetes", "BPM ≥ 70"),
        ("Ишемическая болезнь", "ischemic_heart_disease", "BPM ≤ 115, спокойная музыка"),
    ]
}

enum HeartRateZoneColor {
    static func color(for zone: Int) -> (name: String, swiftUIColor: String) {
        switch zone {
        case 1: return ("Восстановление", "green")
        case 2: return ("Жиросжигание", "yellow")
        case 3: return ("Кардио", "orange")
        case 4: return ("Анаэробная", "red")
        default: return ("Максимум", "purple")
        }
    }
}
