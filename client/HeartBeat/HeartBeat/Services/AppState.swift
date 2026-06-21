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

    private var playingFragment: MusicFragment?
    private var readyNextFragment: MusicFragment?
    private var generationTask: Task<Void, Never>?


    private let healthKit = HealthKitManager()


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

            startHeartRatePolling()
            configurePlayback()
            await loadAndPlayFirstFragment()

        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false

    }

    func stopWorkout() async {
        healthKit.stopObserver()
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
            readyNextFragment = nil
            startGeneratingNext()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    // MARK: - Heart rate

    private func startHeartRatePolling() {
        // 1. Просим доступ у пользователя перед началом
        Task {
            do {
                try await healthKit.requestAuthorization()

                // 2. Запускаем наблюдение за реальным пульсом
                healthKit.startHeartRateObserver { [weak self] realHR in
                    Task { @MainActor in
                        self?.currentHR = Int(realHR)
                        await self?.sendRealHeartRateToBackend(heartRate: Int(realHR))
                    }
                }
            } catch {
                self.errorMessage = "Доступ к HealthKit отклонен или недоступен: \(error.localizedDescription)"

            }
        }
    }

    private func sendRealHeartRateToBackend(heartRate: Int) async {
        guard let sessionId, isSessionActive else { return }

        let resting = Int(userProfile.restingHr) ?? 65
        let active = Int(userProfile.activeHr) ?? 130
        let intensity = min(1.0, max(0.0, Double(heartRate - resting) / Double(max(active - resting, 1))))

        let update = HeartRateUpdate(
            currentHr: heartRate,
            movementIntensity: intensity,
            stressLevel: 0.3
        )

        do {
            let response = try await api.updateHeartRate(sessionId: sessionId, update: update)
            self.currentHR = response.currentHr
            self.heartRateZone = response.heartRateZone
            self.heartRateZoneLabel = response.heartRateZoneLabel
            self.targetBPM = response.targetBpm
        } catch {

            if !isGenerating {
                errorMessage = error.localizedDescription
            }
        }
    }

    // MARK: - Music generation & playback

    private func configurePlayback() {
        audioPlayer.configure(
            onNearEnd: { [weak self] in
                Task { @MainActor in
                    self?.handleNearEndOfFragment()
                }
            },
            onFragmentStarted: { [weak self] index in
                Task { @MainActor in
                    self?.handleFragmentStarted(index: index)
                }
            }
        )
    }

    private func loadAndPlayFirstFragment() async {
        isGenerating = true
        do {
            let fragment = try await fetchFragment()
            playingFragment = fragment
            currentTrack = CurrentTrack(from: fragment)
            applyFragmentMetadata(fragment)

            audioPlayer.play(fragment: fragment) { [weak self] in
                // Следующая генерация только после буферизации первого трека
                self?.startGeneratingNext()
            }
        } catch {
            errorMessage = error.localizedDescription
        }
        isGenerating = false
    }

    private func fetchFragment() async throws -> MusicFragment {
        guard let sessionId else { throw APIError.invalidURL }

        var attempts = 0
        while true {
            do {
                let response = try await api.generateMusic(sessionId: sessionId)

                AppLogger.shared.appendIteration(
                    sessionId: sessionId,
                    profile: userProfile.toAPIProfile(),
                    currentHR: self.currentHR,
                    context: sessionSettings.toAPIContext(),
                    iterationIndex: response.fragmentIndex
                )

                return MusicFragment(from: response, baseURL: AppConfig.apiBaseURL)
            } catch let error as APIError where error.errorDescription?.contains("загружается") == true {
                attempts += 1
                if attempts > 12 { throw error }
                errorMessage = error.localizedDescription
                try await Task.sleep(for: .seconds(5))
            }
        }
    }

    private func startGeneratingNext() {
        guard isSessionActive, generationTask == nil else { return }

        generationTask = Task {
            isGenerating = true
            errorMessage = nil
            do {
                let fragment = try await fetchFragment()
                if !Task.isCancelled {
                    readyNextFragment = fragment
                    audioPlayer.prefetchNext(fragment)
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

    private func handleNearEndOfFragment() {
        guard isSessionActive else { return }

        if let next = readyNextFragment {
            audioPlayer.prefetchNext(next)
            return
        }

        if !audioPlayer.hasNextFragmentQueued, let fragment = playingFragment {
            audioPlayer.enqueueLoopBridge(for: fragment)
        }
    }

    private func handleFragmentStarted(index: Int) {
        guard isSessionActive else { return }

        if let next = readyNextFragment, next.fragmentIndex == index {
            playingFragment = next
            readyNextFragment = nil
            currentTrack = CurrentTrack(from: next)
            applyFragmentMetadata(next)
            startGeneratingNext()
        }

        if let playbackError = audioPlayer.playbackError {
            errorMessage = playbackError
        }
    }

    private func stopPlaybackPipeline() {
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
