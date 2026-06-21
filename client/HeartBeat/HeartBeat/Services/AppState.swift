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
    private var isPrefetching = false

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

            let response = try await api.startSession(
                profile: userProfile.toAPIProfile(),
                context: sessionSettings.toAPIContext()
            )

            sessionId = response.sessionId
            isSessionActive = true
            currentHR = response.currentHr
            simulatedHR = response.currentHr

            startHeartRatePolling()
            await generateNextTrack()
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func stopWorkout() async {
        heartRateTimer?.invalidate()
        heartRateTimer = nil
        audioPlayer.stop()

        if let sessionId {
            try? await api.endSession(sessionId: sessionId)
        }

        sessionId = nil
        isSessionActive = false
        currentTrack = nil
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
            await generateNextTrack()
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

    /// Симуляция пульса до подключения HealthKit / BLE
    private func simulateHeartRate() {
        let resting = Int(userProfile.restingHr) ?? 65
        let active = Int(userProfile.activeHr) ?? 130
        let target = active
        let step = Int.random(in: -2...4)

        if simulatedHR < target {
            simulatedHR = min(target, simulatedHR + max(1, step))
        } else {
            simulatedHR = max(resting, simulatedHR + step)
        }
        currentHR = simulatedHR

        let safeHR = min(active, max(resting, simulatedHR))
        simulatedHR = safeHR
        currentHR = safeHR
    }

    // MARK: - Music generation

    func generateNextTrack() async {
        guard let sessionId, !isGenerating else { return }
        isGenerating = true
        errorMessage = nil

        do {
            let response = try await api.generateMusic(sessionId: sessionId)
            let track = CurrentTrack(from: response, baseURL: AppConfig.apiBaseURL)

            heartRateZone = response.heartRateZone
            heartRateZoneLabel = response.heartRateZoneLabel
            targetBPM = response.bpm
            currentTrack = track

            audioPlayer.play(track: track) { [weak self] in
                Task { @MainActor in
                    await self?.prefetchIfNeeded()
                }
            }
        } catch let error as APIError where error.errorDescription?.contains("загружается") == true {
            errorMessage = error.localizedDescription
            try? await Task.sleep(for: .seconds(5))
            isGenerating = false
            await generateNextTrack()
            return
        } catch {
            errorMessage = error.localizedDescription
        }

        isGenerating = false
    }

    private func prefetchIfNeeded() async {
        guard !isPrefetching else { return }
        isPrefetching = true
        await generateNextTrack()
        isPrefetching = false
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
