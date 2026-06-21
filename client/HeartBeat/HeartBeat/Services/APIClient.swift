import Foundation

enum APIError: LocalizedError {
    case invalidURL
    case httpError(Int, String)
    case decodingError(Error)
    case modelNotReady

    var errorDescription: String? {
        switch self {
        case .invalidURL: return "Некорректный URL"
        case .httpError(let code, let message): return "Ошибка \(code): \(message)"
        case .decodingError(let error): return "Ошибка данных: \(error.localizedDescription)"
        case .modelNotReady: return "Модель ещё загружается, подождите..."
        }
    }
}

struct APIClient {
    let baseURL: String

    private static let urlSession: URLSession = {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 300
        config.timeoutIntervalForResource = 600
        return URLSession(configuration: config)
    }()

    init(baseURL: String = AppConfig.apiBaseURL) {
        self.baseURL = baseURL
    }

    func health() async throws -> HealthResponse {
        try await get("/health")
    }

    func startSession(profile: APIProfile, context: APISessionContext) async throws -> StartSessionResponse {
        let body = StartSessionRequest(profile: profile, session: context)
        return try await post("/api/v1/session/start", body: body)
    }

    func updateHeartRate(sessionId: UUID, update: HeartRateUpdate) async throws -> HeartRateResponse {
        try await post("/api/v1/session/\(sessionId.uuidString)/heartrate", body: update)
    }

    func sessionStatus(sessionId: UUID) async throws -> SessionStatusResponse {
        try await get("/api/v1/session/\(sessionId.uuidString)/status")
    }

    func updateSessionContext(sessionId: UUID, context: APISessionContext) async throws -> SessionStatusResponse {
        try await patch("/api/v1/session/\(sessionId.uuidString)/context", body: ContextPatchBody(session: context))
    }

    func generateMusic(sessionId: UUID) async throws -> GenerateResponse {
        try await post("/api/v1/session/\(sessionId.uuidString)/generate", body: EmptyBody())
    }

    func endSession(sessionId: UUID) async throws {
        let _: EmptyResponse = try await delete("/api/v1/session/\(sessionId.uuidString)")
    }

    // MARK: - HTTP helpers

    private struct EmptyBody: Encodable {}
    private struct EmptyResponse: Decodable {}
    private struct ContextPatchBody: Encodable {
        let session: APISessionContext
    }

    private func get<T: Decodable>(_ path: String) async throws -> T {
        guard let url = URL(string: baseURL + path) else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        return try await execute(request)
    }

    private func post<T: Decodable, B: Encodable>(_ path: String, body: B) async throws -> T {
        guard let url = URL(string: baseURL + path) else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)
        return try await execute(request)
    }

    private func patch<T: Decodable, B: Encodable>(_ path: String, body: B) async throws -> T {
        guard let url = URL(string: baseURL + path) else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = "PATCH"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)
        return try await execute(request)
    }

    private func delete<T: Decodable>(_ path: String) async throws -> T {
        guard let url = URL(string: baseURL + path) else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        return try await execute(request)
    }

    private func execute<T: Decodable>(_ request: URLRequest) async throws -> T {
        let (data, response) = try await Self.urlSession.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw APIError.httpError(0, "Нет ответа от сервера")
        }

        if http.statusCode == 503 {
            throw APIError.modelNotReady
        }

        guard (200...299).contains(http.statusCode) else {
            let message = String(data: data, encoding: .utf8) ?? "Неизвестная ошибка"
            throw APIError.httpError(http.statusCode, message)
        }

        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw APIError.decodingError(error)
        }
    }
}
