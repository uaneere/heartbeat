import SwiftUI

struct ProfileView: View {
    @Environment(AppState.self) private var appState

    var body: some View {
        @Bindable var profile = appState.userProfile

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
                        ProfileInputField(
                            title: "ВОЗРАСТ",
                            placeholder: "Например, 20",
                            text: $profile.age
                        )

                        VStack(alignment: .leading, spacing: 8) {
                            Text("ПОЛ")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(.textSecondary)
                            SegmentedControl(
                                options: Gender.allCases.map(\.title),
                                selectedOption: Binding(
                                    get: { profile.gender.title },
                                    set: { title in
                                        if let gender = Gender.allCases.first(where: { $0.title == title }) {
                                            profile.gender = gender
                                        }
                                    }
                                )
                            )
                        }

                        HStack(spacing: 16) {
                            ProfileInputField(title: "РОСТ (СМ)", placeholder: "175", text: $profile.height)
                            ProfileInputField(title: "ВЕС (КГ)", placeholder: "70", text: $profile.weight)
                        }

                        VStack(alignment: .leading, spacing: 8) {
                            Text("ДАВЛЕНИЕ (ВЕРХНЕЕ/НИЖНЕЕ)")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(.textSecondary)
                                .tracking(1.0)
                            HStack(spacing: 12) {
                                ProfileInputField(title: "", placeholder: "120", text: $profile.systolicPressure)
                                Text("/")
                                    .font(.system(size: 20, weight: .light))
                                    .foregroundColor(.textSecondary)
                                ProfileInputField(title: "", placeholder: "80", text: $profile.diastolicPressure)
                            }
                        }

                        HStack(spacing: 16) {
                            ProfileInputField(title: "ПУЛЬС (ПОКОЙ)", placeholder: "65", text: $profile.restingHr)
                            ProfileInputField(title: "ПУЛЬС (АКТИВ)", placeholder: "130", text: $profile.activeHr)
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
                                    .background(!profile.hasDiseases ? .primaryWine : .clear)
                                    .foregroundColor(!profile.hasDiseases ? .white : .textSecondary)
                                    .cornerRadius(10)
                                    .onTapGesture { profile.hasDiseases = false }

                                Text("Есть")
                                    .font(.system(size: 14, weight: .semibold))
                                    .frame(width: 50, height: 34)
                                    .background(profile.hasDiseases ? .primaryWine : .clear)
                                    .foregroundColor(profile.hasDiseases ? .white : .textSecondary)
                                    .cornerRadius(10)
                                    .onTapGesture { profile.hasDiseases = true }
                            }
                            .padding(3)
                            .background(.accentBackground)
                            .cornerRadius(12)
                        }

                        if profile.hasDiseases {
                            Divider()
                                .background(.textSecondary.opacity(0.2))
                                .padding(.vertical, 4)

                            VStack(spacing: 18) {
                                ForEach(ConditionMapping.items, id: \.apiKey) { item in
                                    DiseaseRow(
                                        title: item.title,
                                        isChecked: Binding(
                                            get: { profile.selectedConditions.contains(item.apiKey) },
                                            set: { checked in
                                                if checked {
                                                    profile.selectedConditions.insert(item.apiKey)
                                                } else {
                                                    profile.selectedConditions.remove(item.apiKey)
                                                }
                                            }
                                        )
                                    )
                                }
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
                                ForEach(GenreMapping.items, id: \.apiKey) { genre in
                                    MusicGenreCard(
                                        title: genre.title,
                                        imageName: genre.imageName,
                                        isSelected: profile.selectedGenres.contains(genre.apiKey),
                                        onTap: {
                                            if profile.selectedGenres.contains(genre.apiKey) {
                                                profile.selectedGenres.remove(genre.apiKey)
                                            } else {
                                                profile.selectedGenres.insert(genre.apiKey)
                                            }
                                        }
                                    )
                                }
                            }
                            .padding(.horizontal, 24)
                            .padding(.bottom, 10)
                        }
                    }

                    if let error = appState.errorMessage {
                        Text(error)
                            .font(.system(size: 14))
                            .foregroundColor(.red)
                            .padding(.horizontal, 24)
                    }

                    Button {
                        appState.saveProfile()
                    } label: {
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

#Preview {
    ProfileView()
        .environment(AppState())
}
