import Foundation

// MARK: - JSON Log Structures
struct SessionLogDump: Codable {
    let userId: String
    var sessions: [String: SessionRecord]
}

struct SessionRecord: Codable {
    let profileData: APIProfile
    var iterations: [String: IterationRecord]
}

struct IterationRecord: Codable {
    let currentHeartRate: Int
    let activityType: String
    let tempoPreference: String
    let goal: String
    let timestamp: String
}

// MARK: - Logger Service
final class AppLogger {
    static let shared = AppLogger()
    private init() {}

    private let fileManager = FileManager.default


    private var txtLogsURL: URL {
        fileManager.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("api_client_logs.txt")
    }

    private var jsonHistoryURL: URL {
        fileManager.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("sessions_history.json")
    }

    // MARK: - 1. Текстовое логирование (Файл 1)

    func log(_ message: String) {
        let timestamp = ISO8601DateFormatter().string(from: Date())
        let logLine = "[\(timestamp)] \(message)\n"

        print(logLine.replacingOccurrences(of: "\n", with: ""))

        if let data = logLine.data(using: .utf8) {
            if fileManager.fileExists(atPath: txtLogsURL.path) {
                if let fileHandle = try? FileHandle(forWritingTo: txtLogsURL) {
                    fileHandle.seekToEndOfFile()
                    fileHandle.write(data)
                    fileHandle.closeFile()
                }
            } else {
                try? data.write(to: txtLogsURL)
            }
        }
    }

    // MARK: - 2. JSON-структурирование сессий (Файл 2)

    func appendIteration(
        sessionId: UUID,
        profile: APIProfile,
        currentHR: Int,
        context: APISessionContext,
        iterationIndex: Int
    ) {
        let fileURL = jsonHistoryURL
        var currentDump = SessionLogDump(userId: "irina_user", sessions: [:])


        if fileManager.fileExists(atPath: fileURL.path),
           let data = try? Data(contentsOf: fileURL),
           let decoded = try? JSONDecoder().decode(SessionLogDump.self, from: data) {
            currentDump = decoded
        }

        let sessionKey = sessionId.uuidString
        let iterationKey = "iteration_\(iterationIndex)"

        let newIteration = IterationRecord(
            currentHeartRate: currentHR,
            activityType: context.activityType.displayName,
            tempoPreference: context.tempoPreference.displayName,
            goal: context.goal.displayName,
            timestamp: ISO8601DateFormatter().string(from: Date())
        )

        if var existingSession = currentDump.sessions[sessionKey] {

            existingSession.iterations[iterationKey] = newIteration
            currentDump.sessions[sessionKey] = existingSession
        } else {

            let newSessionRecord = SessionRecord(
                profileData: profile,
                iterations: [iterationKey: newIteration]
            )
            currentDump.sessions[sessionKey] = newSessionRecord
        }


        let encoder = JSONEncoder()
        encoder.outputFormatting = .prettyPrinted 
        if let data = try? encoder.encode(currentDump) {
            try? data.write(to: fileURL)
        }
    }
}

