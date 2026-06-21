import SwiftUI

struct HomeView: View {
    @Environment(AppState.self) private var appState
    @State private var isShowingSettings = false

    var body: some View {
        ZStack {
            Color.colorBackground
                .ignoresSafeArea()

            ScrollView(.vertical, showsIndicators: false) {
                VStack(spacing: 30) {
                    HStack {
                        Text("Главная")
                            .font(.system(size: 34, weight: .bold))
                            .foregroundStyle(.primaryWine)

                        Spacer()

                        Button(action: { isShowingSettings = true }) {
                            Image(systemName: "slider.horizontal.3")
                                .font(.system(size: 20, weight: .semibold))
                                .foregroundColor(.textMain)
                                .frame(width: 44, height: 44)
                                .background(Color.white)
                                .clipShape(Circle())
                                .shadow(color: .black.opacity(0.1), radius: 4)
                        }
                    }
                    .padding(.horizontal, 24)
                    .padding(.top, 16)

                    if let error = appState.errorMessage {
                        Text(error)
                            .font(.system(size: 14))
                            .foregroundColor(.red)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, 24)
                    }

                    BPMIndicator(bpm: "\(appState.currentHR)")
                        .padding(.top, 20)

                    Text("Зона \(appState.heartRateZone) — \(appState.heartRateZoneLabel)")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundColor(.white)
                        .padding(.vertical, 12)
                        .padding(.horizontal, 24)
                        .background(appState.zoneColor())
                        .cornerRadius(25)

                    HStack(spacing: 16) {
                        StatItem(
                            title: "Музыка",
                            value: "\(appState.targetBPM)",
                            subtitle: "BPM цель"
                        )

                        StatItem(
                            title: "Тип",
                            value: appState.sessionSettings.activityType.displayName,
                            subtitle: appState.sessionSettings.goal.displayName
                        )

                        StatItem(
                            title: "Темп",
                            value: appState.sessionSettings.tempoPreference.displayName,
                            subtitle: "Предпочтение"
                        )
                    }
                    .padding(.horizontal, 16)

                    if let track = appState.currentTrack {
                        MusicPlayerCard(
                            trackTitle: track.title,
                            genre: track.genre,
                            bpm: track.bpm,
                            isPlaying: appState.audioPlayer.isPlaying,
                            isGenerating: appState.isGenerating,
                            onPlayToggle: { appState.audioPlayer.togglePlayback() }
                        )
                        .padding(.horizontal, 16)
                    } else if appState.isGenerating || appState.isLoading {
                        ProgressView(appState.isGenerating ? "Генерация музыки..." : "Подключение...")
                            .padding()
                    }

                    sessionControlButton
                        .padding(.horizontal, 24)
                        .padding(.bottom, 32)

                    Spacer()
                }
            }
            .sheet(isPresented: $isShowingSettings) {
                SettingsView()
                    .environment(appState)
                    .presentationDetents([.large])
                    .presentationDragIndicator(.visible)
            }
        }
    }

    @ViewBuilder
    private var sessionControlButton: some View {
        if appState.isSessionActive {
            Button {
                Task { await appState.stopWorkout() }
            } label: {
                Text("Завершить генерацию")
                    .font(.system(size: 18, weight: .bold))
                    .foregroundColor(.primaryWine)
                    .frame(maxWidth: .infinity)
                    .frame(height: 60)
                    .background(Color.white)
                    .cornerRadius(30)
                    .overlay(
                        RoundedRectangle(cornerRadius: 30)
                            .stroke(Color.primaryWine, lineWidth: 2)
                    )
            }
            .disabled(appState.isLoading)
        } else {
            Button {
                Task { await appState.startWorkout() }
            } label: {
                Text(appState.isLoading ? "Запуск..." : "Начать генерацию")
                    .font(.system(size: 18, weight: .bold))
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .frame(height: 60)
                    .background(appState.userProfile.isValidForSession ? Color.primaryWine : Color.gray)
                    .cornerRadius(30)
            }
            .disabled(appState.isLoading || !appState.userProfile.isValidForSession)
        }
    }
}

#Preview {
    HomeView()
        .environment(AppState())
}
