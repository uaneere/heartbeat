import SwiftUI


// MARK: - Поле ввода данных
struct ProfileInputField: View {
    let title: String
    let placeholder: String
    @State var text: String = ""

    var body: some View {
        VStack(alignment: .leading) {
            Text(title)
                .font(.system(size: 11, weight: .bold))
                .foregroundColor(.textSecondary)
                .tracking(1.0)

            TextField("", text: $text, prompt: Text(placeholder).foregroundColor(.textSecondary.opacity(0.4)))
                .padding(.horizontal, 16)
                .frame(height: 54)
                .background(.accentBackground)
                .cornerRadius(16)
                .foregroundColor(.textMain)
                .font(.system(size: 16, weight: .medium))

        }
    }
}

// MARK: Сегмент-Контрол
struct SegmentedControl: View {
    let options: [String]
    @State var selectedOption: String

    var body: some View {
        HStack(spacing: 0) {
            ForEach(options, id: \.self) { option in
                Text(option)
                    .font(.system(size: 15, weight: .semibold))
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(selectedOption == option ? .primaryWine : .switchBackground)
                    .foregroundColor(selectedOption == option ? .white : .textSecondary)
                    .cornerRadius(12)
                    .onTapGesture {
                        selectedOption = option
                    }
                    .padding(4)
            }
        }
        .frame(height: 48)
        .background(.switchBackground)
        .cornerRadius(14)
    }
}

// MARK: - Элемент списка заболеваний
struct DiseaseRow: View {
    let title: String
    @State var isChecked: Bool = false

    var body: some View {
        HStack(spacing: 16) {
            Circle()
                .stroke(isChecked ? .primaryWine : .textSecondary.opacity(0.4), lineWidth: 2)
                .background(isChecked ? Circle().fill(.primaryWine) : Circle().fill(.clear))
                .frame(width: 24, height: 24)
                .overlay(
                    Group {
                        if isChecked {
                            Image(systemName: "checkmark")
                                .font(.system(size: 12, weight: .bold))
                                .foregroundColor(.white)
                        }
                    }
                )
            Text(title)
                .font(.system(size: 16, weight: .medium))
                .foregroundColor(.textMain.opacity(0.8))

            Spacer()
        }
        .contentShape(Rectangle())
        .onTapGesture {
            isChecked.toggle()
        }
    }
}

// MARK: - Карточка музыкального жанра
struct MusicGenreCard: View {
    let title: String
    let imageName: String
    let isSelected: Bool

    var body: some View {
        VStack {
            Spacer()
            HStack {
                Text(title)
                    .font(.system(size: 16, weight: .bold))
                    .foregroundColor(.white)
                    .padding([.leading, .bottom], 16)
                Spacer()
            }
        }
        .frame(width: 140, height: 180)
        .background(.green)
        .cornerRadius(24)
        .overlay(
            VStack {
                HStack {
                    Spacer()
                    Circle()
                        .stroke(.white.opacity(0.6), lineWidth: 2)
                        .background(isSelected ? Circle().fill(.white) : Circle().fill(.clear))
                        .frame(width: 24, height: 24)
                        .overlay(
                            Group {
                                if isSelected {
                                    Image(systemName: "checkmark")
                                        .font(.system(size: 12, weight: .bold))
                                        .foregroundColor(.primary)
                                }
                            }
                        )
                        .padding([.top, .trailing], 16)
                }
                Spacer()
            }
        )
    }
}


