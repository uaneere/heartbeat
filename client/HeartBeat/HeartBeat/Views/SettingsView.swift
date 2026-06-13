import SwiftUI


struct TrainingGoal: Identifiable {
    let id = UUID()
    let title: String
    let icon: String
}

struct SettingsView: View {
    @Environment(\.dismiss) var dismiss

    @State private var selectedActivity: String = "Бег"
    @State private var selectedGoal: String = "Общая форма"
    @State private var selectedTempo: String = "Среднее"

    // Список всех целей (заглушка данных)
    let goals = [
        TrainingGoal(title: "Жиросжигание", icon: "flame.fill"),
        TrainingGoal(title: "Спринт", icon: "bolt.horizontal.fill"),
        TrainingGoal(title: "Восстановление", icon: "heart.fill"),
        TrainingGoal(title: "Общая форма", icon: "waveform.path.ecg"),
        TrainingGoal(title: "Антистресс", icon: "wind"),
        TrainingGoal(title: "Разминка", icon: "sun.max.fill"),
        TrainingGoal(title: "Заминка", icon: "snowflake")
    ]

    let activityColumns = [
        GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())
    ]

    var body: some View {
        VStack(spacing: 0) {
            // MARK: - Header
            headerView

            ScrollView(.vertical, showsIndicators: false) {
                VStack(alignment: .leading, spacing: 24) {

                    // MARK: - Тип активности
                    activitySection

                    // MARK: - Цель тренировки
                    VStack(alignment: .leading, spacing: 12) {
                        Text("ЦЕЛЬ ТРЕНИРОВКИ")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(.textSecondary)
                            .tracking(1.0)

                        FlowLayout(spacing: 8) {
                            ForEach(goals) { goal in
                                GoalChip(
                                    icon: goal.icon,
                                    title: goal.title,
                                    isSelected: selectedGoal == goal.title
                                ) {
                                    selectedGoal = goal.title
                                }
                            }
                        }
                    }

                    // MARK: - Предпочтение темпа
                    tempoSection

                    // MARK: - Кнопка 'Применить'
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
        VStack(alignment: .leading, spacing: 12) {
            Text("ТИП АКТИВНОСТИ")
                .font(.system(size: 11, weight: .bold))
                .foregroundColor(.textSecondary)
                .tracking(1.0)

            LazyVGrid(columns: activityColumns, spacing: 12) {
                ActivityTile(icon: "bolt.fill", title: "Бег", isSelected: selectedActivity == "Бег") { selectedActivity = "Бег" }
                ActivityTile(icon: "figure.walk", title: "Ходьба", isSelected: selectedActivity == "Ходьба") { selectedActivity = "Ходьба" }
                ActivityTile(icon: "dumbbell.fill", title: "Зал", isSelected: selectedActivity == "Зал") { selectedActivity = "Зал" }
                ActivityTile(icon: "bicycle", title: "Велосипед", isSelected: selectedActivity == "Велосипед") { selectedActivity = "Велосипед" }
                ActivityTile(icon: "brain.head.profile", title: "Медитация", isSelected: selectedActivity == "Медитация") { selectedActivity = "Медитация" }
                ActivityTile(icon: "moon.fill", title: "Сон", isSelected: selectedActivity == "Сон") { selectedActivity = "Сон" }
                ActivityTile(icon: "book.fill", title: "Учёба", isSelected: selectedActivity == "Учёба") { selectedActivity = "Учёба" }
                ActivityTile(icon: "laurel.leading", title: "Йога", isSelected: selectedActivity == "Йога") { selectedActivity = "Йога" }
                ActivityTile(icon: "gamecontroller.fill", title: "Игры", isSelected: selectedActivity == "Игры") { selectedActivity = "Игры" }
            }
        }
    }

    private var tempoSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("ПРЕДПОЧТЕНИЕ ТЕМПА")
                .font(.system(size: 11, weight: .bold))
                .foregroundColor(.textSecondary)
                .tracking(1.0)

            SegmentedControl(options: ["Медленно", "Среднее", "Быстро"], selectedOption: selectedTempo)

        }
    }

    private var applyButton: some View {
        Button(action: { dismiss() }) {
            Text("Применить")
                .font(.system(size: 18, weight: .bold))
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .frame(height: 64)
                .background(.primaryWine)
                .cornerRadius(32)
                .shadow(color: .primaryWine.opacity(0.3), radius: 10, x: 0, y: 5)
        }
        .padding(.top, 10)
        .padding(.bottom, 20)
    }
}

#Preview {
    SettingsView()
}
