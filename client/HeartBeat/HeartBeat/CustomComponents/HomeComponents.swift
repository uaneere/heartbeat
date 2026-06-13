import SwiftUI


// MARK: - Блоки статистики
struct StatItem: View {
    let title: String
    let value: String
    let subtitle: String

    var body: some View {
        VStack(spacing: 8) {
            Text(title.uppercased())
                .font(.system(size: 10, weight: .bold))
                .foregroundColor(.textSecondary)
                .tracking(1.0)

            Text(value)
                .font(.system(size: 20, weight: .bold))
                .foregroundColor(.textMain)

            Text(subtitle)
                .font(.system(size: 12))
                .foregroundColor(.textSecondary)
                .multilineTextAlignment(.center)
        }
        .padding(.vertical, 16)
        .padding(.horizontal, 8)
        .frame(maxWidth: .infinity)
        .frame(height: 110)
        .background(Color.white)
        .cornerRadius(20)
        .shadow(color: Color.black.opacity(0.02), radius: 5, x: 0, y: 2)
    
    }
}

// MARK: - Центральный индикатор пульса
struct  BPMIndicator: View {
    let bpm: String

    var body: some View {
        ZStack {
            Circle()
                .stroke (
                    AngularGradient(gradient: Gradient(colors: [.green, .yellow, .orange]), center: .center),
                    lineWidth: 1
                )
                .frame(width: 280, height: 280)
                .opacity(0.3)

            Circle()
                .stroke(Color.orange.opacity(0.1), lineWidth: 20)
                .frame(width: 250, height: 250)

            Circle()
                .trim(from: 0, to: 0.7)
                .stroke(
                    LinearGradient(colors: [.orange, .yellow], startPoint: .top, endPoint: .bottom),
                    style: StrokeStyle(lineWidth: 8, lineCap: .round)
                )
                .frame(width: 220, height: 220)
                .rotationEffect(.degrees(-90))

            Circle()
                .fill(Color.white)
                .frame(width: 190, height: 190)
                .shadow(color: Color.black.opacity(0.08), radius: 10, x: 0, y: 6)

            VStack(spacing: -5) {
                Image(systemName: "heart.fill")
                    .font(.system(size: 30, weight: .light))
                    .foregroundColor(.orange)

                Text(bpm)
                    .font(.system(size: 64, weight: .bold))
                    .foregroundColor(.textMain)

                Text("BPM")
                    .font(.system(size: 16, weight: .medium))
                    .foregroundColor(.textSecondary)
            }
        }
    }
}

// MARK: - Карточка музыкальной генерации
struct MusicPlayerCard: View {
    var body: some View {
        HStack(spacing: 16) {
            // заглушка обложки
            ZStack {
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color(white: 0.9))
                    .frame(width: 60, height: 60)

                VStack(spacing: 2) {
                    Text("Cover")
                        .font(.system(size: 10))
                    Image(systemName: "questionmark.square")
                }
                .foregroundColor(.blue)
            }

            VStack(alignment: .leading, spacing: 4) {
                Text("ГЕНЕРАЦИЯ - 135 BPM")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(.orange)

                Text("Power Rush")
                    .font(.system(size: 18, weight: .bold))
                    .foregroundColor(.textMain)

                Text("EDM Mix")
                    .font(.system(size: 14))
                    .foregroundColor(.textSecondary)
            }

            Spacer()

            Button(action: {}) {
                Image(systemName: "play.fill")
                    .foregroundColor(.orange)
                    .frame(width: 40, height: 40)
                    .background(Color.orange.opacity(0.1))
                    .clipShape(Circle())
            }
        }
        .padding(16)
        .background(Color.white)
        .cornerRadius(20)
        .shadow(color: Color.black.opacity(0.05), radius: 10, x: 0, y: 5)
    }
}

// MARK: - Плитка типа активности
struct ActivityTile: View {
    let icon: String
    let title: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 20, weight: .semibold))

            Text(title)
                .font(.system(size: 12, weight: .bold))
        }
        .foregroundColor(isSelected ? .white : .textMain.opacity(0.8))
        .frame(maxWidth: .infinity)
        .frame(height: 80)
        .background(isSelected ? .primaryWine : .accentBackground)
        .cornerRadius(16)
        .shadow(color: isSelected ? .primaryWine.opacity(0.3) : Color.clear, radius: 8, x: 0, y: 4)
        .onTapGesture {
            action()
        }

    }
}

// MARK: - Тег для тренировки
struct GoalChip: View {
    let icon: String
    let title: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 14))

            Text(title)
                .font(.system(size: 14, weight: .bold))
                .lineLimit(1)
                .minimumScaleFactor(0.8)

        }
        .padding(.horizontal, 16)
        .frame(height: 42)
        .background(isSelected ? .primaryWine : .accentBackground)
        .foregroundColor(isSelected ? .white : .textMain.opacity(0.8))
        .cornerRadius(20)
        .onTapGesture {
            action()
        }
    }
}

// MARK: - Динамический Flow Layout
struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let result = FlowResult(in: proposal.width ?? 0, subviews: subviews, spacing: spacing)
        return result.size
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let result = FlowResult(in: bounds.width, subviews: subviews, spacing: spacing)
        for element in result.elements {
            element.subview.place(at: CGPoint(x: bounds.minX + element.rect.minX, y: bounds.minY + element.rect.minY), proposal: ProposedViewSize(element.rect.size))
        }
    }

    struct FlowResult {
        struct Element {
            let subview: LayoutSubview
            let rect: CGRect
        }
        var elements: [Element] = []
        var size: CGSize = .zero

        init(in maxWidth: CGFloat, subviews: LayoutSubviews, spacing: CGFloat) {
            var currentX: CGFloat = 0
            var currentY: CGFloat = 0
            var lineHeight: CGFloat = 0

            for subview in subviews {
                let sigze = subview.sizeThatFits(.unspecified)
                if currentX + sigze.width > maxWidth && currentX > 0 {
                    currentX = 0
                    currentY += lineHeight + spacing
                    lineHeight = 0
                }
                elements.append(Element(subview: subview, rect: CGRect(x: currentX, y: currentY, width: sigze.width, height: sigze.height)))
                lineHeight = max(lineHeight, sigze.height)
                currentX += sigze.width + spacing
            }
            size = CGSize(width: maxWidth, height: currentY + lineHeight)
        }
    }
}
