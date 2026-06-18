import SwiftUI

struct SettingsView: View {
    @Environment(AppState.self) private var appState
    @Environment(\.dismiss) var dismiss

    var body: some View {
        @Bindable var state = appState

        VStack(spacing: 0) {
            headerView

            ScrollView(.vertical, showsIndicators: false) {
                VStack(alignment: .leading, spacing: 24) {
                    activitySection

                    VStack(alignment: .leading, spacing: 12) {
                        Text("ЦЕЛЬ ТРЕНИРОВКИ")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(.textSecondary)
                            .tracking(1.0)

                        FlowLayout(spacing: 8) {
                            ForEach(GoalType.allCases, id: \.self) { goal in
                                GoalChip(
                                    icon: goal.icon,
                                    title: goal.displayName,
                                    isSelected: state.sessionSettings.goal == goal
                                ) {
                                    state.sessionSettings.goal = goal
                                }
                            }
                        }
                    }

                    tempoSection

                    applyButton
                }
                .padding(.horizontal, 24)
            }
        }
        .background(Color.white)
    }

    private var headerView: some View {
        HStack {
            Text("Настройки сессии")
                .font(.system(size: 24, weight: .bold))
                .foregroundColor(.primaryWine)

            Spacer()

            Button(action: { dismiss() }) {
                Image(systemName: "xmark")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundColor(.textSecondary)
                    .padding(10)
                    .background(.accentBackground)
                    .clipShape(Circle())
            }
        }
        .padding(.horizontal, 24)
        .padding(.top, 30)
        .padding(.bottom, 20)
    }

    private var activitySection: some View {
        let columns = [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())]

        return VStack(alignment: .leading, spacing: 12) {
            Text("ТИП АКТИВНОСТИ")
                .font(.system(size: 11, weight: .bold))
                .foregroundColor(.textSecondary)
                .tracking(1.0)

            LazyVGrid(columns: columns, spacing: 12) {
                ForEach(ActivityType.allCases, id: \.self) { activity in
                    ActivityTile(
                        icon: activity.icon,
                        title: activity.displayName,
                        isSelected: appState.sessionSettings.activityType == activity
                    ) {
                        appState.sessionSettings.activityType = activity
                    }
                }
            }
        }
    }

    private var tempoSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("ПРЕДПОЧТЕНИЕ ТЕМПА")
                .font(.system(size: 11, weight: .bold))
                .foregroundColor(.textSecondary)
                .tracking(1.0)

            SegmentedControl(
                options: TempoPreference.allCases.map(\.displayName),
                selectedOption: Binding(
                    get: { appState.sessionSettings.tempoPreference.displayName },
                    set: { name in
                        if let tempo = TempoPreference.allCases.first(where: { $0.displayName == name }) {
                            appState.sessionSettings.tempoPreference = tempo
                        }
                    }
                )
            )
        }
    }

    private var applyButton: some View {
        Button {
            Task {
                await appState.applySessionSettings()
                dismiss()
            }
        } label: {
            Text(appState.isLoading ? "Применение..." : "Применить")
                .font(.system(size: 18, weight: .bold))
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .frame(height: 64)
                .background(.primaryWine)
                .cornerRadius(32)
                .shadow(color: .primaryWine.opacity(0.3), radius: 10, x: 0, y: 5)
        }
        .disabled(appState.isLoading)
        .padding(.top, 10)
        .padding(.bottom, 20)
    }
}

#Preview {
    SettingsView()
        .environment(AppState())
}
