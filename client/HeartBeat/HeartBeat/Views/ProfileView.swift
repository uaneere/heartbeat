import SwiftUI

struct ProfileView: View {
    @State private var hasDiseases: Bool = true

    var body: some View {
        ZStack {
            Color.colorBackground
                .ignoresSafeArea()

            ScrollView(.vertical, showsIndicators: false) {
                VStack(spacing: 24) {

                    HStack {
                        Text("Профиль")
                            .font(.system(size: 34, weight: .bold))
                            .foregroundColor(.primaryWine)
                        Spacer()
                    }
                    .padding(.horizontal, 24)
                    .padding(.top, 16)

                    VStack(spacing: 20) {
                        ProfileInputField(title: "ВОЗРАСТ", placeholder: "Например, 20")

                        VStack(alignment: .leading, spacing: 8) {
                            Text("ПОЛ")
                                .font(.system(size: 11, weight: .bold))
                                . foregroundColor(.textSecondary)
                            SegmentedControl(options: ["Мужской", "Женский"], selectedOption: "Мужской")
                        }

                        HStack(spacing: 16) {
                            ProfileInputField(title: "РОСТ (СМ)", placeholder: "175")
                            ProfileInputField(title: "ВЕС (КГ)", placeholder: "70")
                        }

                        VStack(alignment: .leading, spacing: 8) {
                            Text("ДАВЛЕНИЕ (ВЕРХНЕЕ/НИЖНЕЕ)")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(.textSecondary)
                                .tracking(1.0)
                            HStack(spacing: 12) {
                                ProfileInputField(title: "", placeholder: "120")
                                Text("/")
                                    .font(.system(size: 20, weight: .light))
                                    .foregroundColor(.textSecondary)
                                ProfileInputField(title: "", placeholder: "80")
                            }
                        }

                        HStack(spacing: 16) {
                            ProfileInputField(title: "ПУЛЬС (ПОКОЙ)", placeholder: "65")
                            ProfileInputField(title: "ПУЛЬС (АКТИВ)", placeholder: "130")
                        }
                    }
                    .padding(24)
                    .background(.white)
                    .cornerRadius(32)
                    .padding(.horizontal, 16)

                    VStack(spacing: 20) {
                        HStack {
                            Text("Хронические заболевания")
                                .font(.system(size: 16, weight: .bold))
                                .foregroundColor(.textMain)
                            Spacer()

                            HStack(spacing: 0) {
                                Text("Нет")
                                    .font(.system(size: 14, weight: .semibold))
                                    .frame(width: 50, height: 34)
                                    .background(!hasDiseases ? .primaryWine : .clear)
                                    .foregroundColor(!hasDiseases ? .white : .textSecondary)
                                    .cornerRadius(10)
                                    .onTapGesture{hasDiseases = false}

                                Text("Есть")
                                    .font(.system(size: 14, weight: .semibold))
                                    .frame(width: 50, height: 34)
                                    .background(hasDiseases ? .primaryWine : .clear)
                                    .foregroundColor(hasDiseases ? .white : .textSecondary)
                                    .cornerRadius(10)
                                    .onTapGesture { hasDiseases = true }
                            }
                            .padding(3)
                            .background(.accentBackground)
                            .cornerRadius(12)
                        }

                        if hasDiseases {
                            Divider()
                                .background(.textSecondary.opacity(0.2))
                                .padding(.vertical, 4)

                            VStack(spacing: 18) {
                                DiseaseRow(title: "Гипертония")
                                DiseaseRow(title: "Аритмия")
                                DiseaseRow(title: "Бронхиальная астма")
                                DiseaseRow(title: "Сахарный диабет")
                                DiseaseRow(title: "Ишемическая болезнь")
                            }
                        }
                    }
                    .padding(24)
                    .background(.white)
                    .cornerRadius(32)
                    .padding(.horizontal, 16)

                    VStack(alignment: .leading, spacing: 16) {
                        Text("Предпочитаемые жанры")
                            .font(.system(size: 16, weight: .bold))
                            .foregroundColor(.textMain)
                            .padding(.horizontal, 24)

                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 14) {
                                MusicGenreCard(title: "Классика", imageName: "classic", isSelected: false)
                                MusicGenreCard(title: "Поп", imageName: "pop", isSelected: false)
                                MusicGenreCard(title: "Рок", imageName: "rock", isSelected: false)
                                MusicGenreCard(title: "Электроника", imageName: "electro", isSelected: false)
                                MusicGenreCard(title: "Джаз", imageName: "jazz", isSelected: false)
                                MusicGenreCard(title: "Lo-Fi", imageName: "lofi", isSelected: false)
                                MusicGenreCard(title: "Фонк", imageName: "fonk", isSelected: false)
                            }
                            .padding(.horizontal, 24)
                            .padding(.bottom, 10)
                        }
                    }

                    Button(action: {
                        print("Настройки сохранены")
                    }) {
                        Text("Сохранить настройки")
                            .font(.system(size: 18, weight: .bold))
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .frame(height: 60)
                            .background(.primaryWine)
                            .cornerRadius(30)
                            .shadow(color: .primaryWine.opacity(0.4), radius: 12, x: 0, y: 8)
                    }
                    .padding(.horizontal, 24)
                    .padding(.top, 16)
                    .padding(.bottom, 32)
                }
            }

        }
    }
}
