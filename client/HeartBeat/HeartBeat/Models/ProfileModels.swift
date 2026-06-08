import Foundation

enum Gender {
    case male, female

    var title: String {
        switch self {
        case .male: return "Мужской"
        case .female: return "Женский"
        }
    }
}


