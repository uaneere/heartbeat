import Foundation
import SwiftUI

@Observable
@MainActor
final class AppState {
    var userProfile = UserProfile.load()
    var sessionSettings = SessionSettings()

    var sessionId: UUID?
    var isSessionActive = false
    var isLoading = false
    var isGenerating = false
    var errorMessage: String?
    var modelReady = false

    var currentHR: Int = 65
    var heartRateZone: Int = 1
    var heartRateZoneLabel: String = "Восстановление"
    var targetBPM: Int = 120
    var currentTrack: CurrentTrack?

    let audioPlayer = AudioPlayerManager()
    private let api = APIClient()
    private var heartRateTimer: Timer?
    private var simulatedHR: Int = 65

    /// Текущий отрывок, который крутится в плеере
    private var playingFragment: MusicFragment?
    /// Следующий отрывок, уже сгенерированный и ждущий своей очереди
    private var readyNextFragment: MusicFragment?
    /// Фоновая задача генерации
    private var generationTask: Task<Void, Never>?
    /// Цикл воспроизведения (fragment → loop → fragment …)
    private var playbackTask: Task<Void, Never>?

    // MARK: - Profile

    func saveProfile() {
        userProfile.save()
        errorMessage = nil
    }

    // MARK: - Session lifecycle

    func startWorkout() async {
        guard userProfile.isValidForSession else {
            errorMessage = "Заполните профиль: возраст и пульс в покое"
            return
        }

        isLoading = true
        errorMessage = nil

        do {
            let health = try await api.health()
            modelReady = health.modelReady

            if let existingId = sessionId {
                try? await api.endSession(sessionId: existingId)
            }

            stopPlaybackPipeline()

            let response = try await api.startSession(
                profile: userProfile.toAPIProfile(),
                context: sessionSettings.toAPIContext()
            )

            sessionId = response.sessionId
            isSessionActive = true
            currentHR = response.currentHr
            simulatedHR = response.currentHr

            startHeartRatePolling()

            // Первый отрывок: ждём полной генерации, потом сразу стартуем второй в фоне
            isGenerating = true
            let first = try await fetchFragment()
            isGenerating = false

            playingFragment = first
            currentTrack = CurrentTrack(from: first)
            applyFragmentMetadata(first)

            startGeneratingNext()
            startPlaybackLoop()
        } catch {
            errorMessage = error.localizedDescription
            isGenerating = false
        }

        isLoading = false
    }

    func stopWorkout() async {
        heartRateTimer?.invalidate()
        heartRateTimer = nil
        stopPlaybackPipeline()

        if let sessionId {
            try? await api.endSession(sessionId: sessionId)
        }

        sessionId = nil
        isSessionActive = false
        currentTrack = nil
        playingFragment = nil
        readyNextFragment = nil
    }

    func applySessionSettings() async {
        guard isSessionActive, let sessionId else { return }

        isLoading = true
        do {
            let status = try await api.updateSessionContext(
                sessionId: sessionId,
                context: sessionSettings.toAPIContext()
            )
            applyStatus(status)
            // Перегенерировать следующий отрывок с новыми настройками
            readyNextFragment = nil
            startGeneratingNext()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    // MARK: - Heart rate

    private func startHeartRatePolling() {
        heartRateTimer?.invalidate()
        heartRateTimer = Timer.scheduledTimer(withTimeInterval: AppConfig.heartRatePollInterval, repeats: true) { [weak self] _ in
            Task { @MainActor in
                await self?.pollHeartRate()
            }
        }
    }

    private func pollHeartRate() async {
        guard let sessionId, isSessionActive else { return }

        simulateHeartRate()

        let resting = Int(userProfile.restingHr) ?? 65
        let active = Int(userProfile.activeHr) ?? 130
        let intensity = min(1.0, max(0.0, Double(simulatedHR - resting) / Double(max(active - resting, 1))))

        let update = HeartRateUpdate(
            currentHr: simulatedHR,
            movementIntensity: intensity,
            stressLevel: 0.3
        )

        do {
            let response = try await api.updateHeartRate(sessionId: sessionId, update: update)
            currentHR = response.currentHr
            heartRateZone = response.heartRateZone
            heartRateZoneLabel = response.heartRateZoneLabel
            targetBPM = response.targetBpm
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func simulateHeartRate() {
        let resting = Int(userProfile.restingHr) ?? 65
        let active = Int(userProfile.activeHr) ?? 130
        let step = Int.random(in: -2...4)

        if simulatedHR < active {
            simulatedHR = min(active, simulatedHR + max(1, step))
        } else {
            simulatedHR = max(resting, simulatedHR + step)
        }
        currentHR = simulatedHR
    }

    // MARK: - Generation pipeline

    private func fetchFragment() async throws -> MusicFragment {
        guard let sessionId else { throw APIError.invalidURL }

        var attempts = 0
        while true {
            do {
                let response = try await api.generateMusic(sessionId: sessionId)
                return MusicFragment(from: response, baseURL: AppConfig.apiBaseURL)
            } catch let error as APIError where error.errorDescription?.contains("загружается") == true {
                attempts += 1
                if attempts > 12 { throw error }
                errorMessage = error.localizedDescription
                try await Task.sleep(for: .seconds(5))
            }
        }
    }

    /// Сразу после окончания генерации предыдущего — стартуем следующий
    private func startGeneratingNext() {
        guard isSessionActive, generationTask == nil else { return }

        generationTask = Task {
            isGenerating = true
            errorMessage = nil
            do {
                let fragment = try await fetchFragment()
                if !Task.isCancelled {
                    readyNextFragment = fragment
                }
            } catch {
                if !Task.isCancelled {
                    errorMessage = error.localizedDescription
                }
            }
            isGenerating = false
            generationTask = nil
        }
    }

    // MARK: - Playback pipeline

    private func startPlaybackLoop() {
        playbackTask?.cancel()
        playbackTask = Task {
            while !Task.isCancelled, isSessionActive, let fragment = playingFragment {
                // 1. Играем текущий отрывок
                await audioPlayer.playAndWait(url: fragment.fragmentURL)

                if Task.isCancelled || !isSessionActive { break }

                // 2. Следующий готов — переход + новый отрывок
                if let next = readyNextFragment {
                    readyNextFragment = nil

                    if let transition = next.transitionURL {
                        await audioPlayer.playAndWait(url: transition)
                    }

                    playingFragment = next
                    currentTrack = CurrentTrack(from: next)
                    applyFragmentMetadata(next)
                    startGeneratingNext()
                    continue
                }

                // 3. Следующий ещё не готов — loop-bridge + повтор текущего
                if let bridge = fragment.loopBridgeURL {
                    await audioPlayer.playAndWait(url: bridge)
                }

                if Task.isCancelled || !isSessionActive { break }

                // Проверяем, не появился ли следующий отрывок за время bridge
                if let next = readyNextFragment {
                    readyNextFragment = nil
                    if let transition = next.transitionURL {
                        await audioPlayer.playAndWait(url: transition)
                    }
                    playingFragment = next
                    currentTrack = CurrentTrack(from: next)
                    applyFragmentMetadata(next)
                    startGeneratingNext()
                }
                // иначе цикл повторит тот же fragment
            }
        }
    }

    private func stopPlaybackPipeline() {
        playbackTask?.cancel()
        playbackTask = nil
        generationTask?.cancel()
        generationTask = nil
        audioPlayer.stop()
        isGenerating = false
    }

    private func applyFragmentMetadata(_ fragment: MusicFragment) {
        targetBPM = fragment.bpm
    }

    private func applyStatus(_ status: SessionStatusResponse) {
        currentHR = status.currentHr
        heartRateZone = status.heartRateZone
        heartRateZoneLabel = status.heartRateZoneLabel
        targetBPM = status.targetBpm
    }

    func zoneColor() -> Color {
        switch heartRateZone {
        case 1: return .green
        case 2: return .yellow
        case 3: return .orange
        case 4: return .red
        default: return .purple
        }
    }
}
