import SwiftUI


struct HomeView: View {
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

                        Button(action: {
                            isShowingSettings = true
                        }) {
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

                    BPMIndicator(bpm: "125")
                        .padding(.top, 20)

                    Text("Зона 3 - Кардио")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundColor(.white)
                        .padding(.vertical, 12)
                        .padding(.horizontal, 24)
                        .background(Color.orange)
                        .cornerRadius(25)

                    HStack(spacing: 16) {
                        StatItem(title: "Музыка", value: "135", subtitle: "BPM цель")

                        StatItem(title: "Тип", value: "Бег", subtitle: "Общая форма")

                        StatItem(title: "Темп", value: "Среднее", subtitle: "Предпочтение")
                    }
                    .padding(.horizontal, 16)

                    MusicPlayerCard()
                        .padding(.horizontal, 16)

                    Spacer()
                }
            }
            .sheet(isPresented: $isShowingSettings) {
                SettingsView()
                    .presentationDetents([.large])
                    .presentationDragIndicator(.visible)
            }
        }
    }
}



#Preview {
    HomeView()
}
