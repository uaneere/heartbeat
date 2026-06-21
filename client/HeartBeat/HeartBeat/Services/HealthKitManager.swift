import Foundation
import HealthKit

enum HealthKitError: LocalizedError {
    case notAvailableOnDevice
    case sharingNotAuthorized

    var errorDescription: String? {
        switch self {
        case .notAvailableOnDevice: return "HealthKit недоступен на этом устройстве"
        case .sharingNotAuthorized: return "Нет разрешения на чтение данных пульса"
        }
    }
}

@Observable
final class HealthKitManager {
    private let healthStore = HKHealthStore()

    var currentHeartRate: Double?

    var isAvailable: Bool {
        HKHealthStore.isHealthDataAvailable()
    }

    /// Запрос разрешения у пользователя
    func requestAuthorization() async throws {
        guard isAvailable else { throw HealthKitError.notAvailableOnDevice }

        // Указываем, что хотим читать именно пульс (Heart Rate)
        guard let heartRateType = HKQuantityType.quantityType(forIdentifier: .heartRate) else { return }

        let typesToRead: Set<HKObjectType> = [heartRateType]

        // Запрашиваем доступ
        try await healthStore.requestAuthorization(toShare: [], read: typesToRead)
    }

    /// Запуск постоянного наблюдения за пульсом (активный воркаут)
    func startHeartRateObserver(onUpdate: @escaping (Double) -> Void) {
        guard let heartRateType = HKQuantityType.quantityType(forIdentifier: .heartRate) else { return }

        let predicate = HKQuery.predicateForSamples(withStart: Date(), end: nil, options: .strictStartDate)

        // Используем HKObserverQuery — реагирует на появление новых записей в "Здоровье"
        let observerQuery = HKObserverQuery(sampleType: heartRateType, predicate: predicate) { [weak self] query, completionHandler, error in
            if error != nil { return }

            // Как только "Здоровье" обновило пульс, мы идем забирать последнее значение
            Task {
                await self?.fetchLatestHeartRateSample(onUpdate: onUpdate)
            completionHandler()
            }
        }

        healthStore.execute(observerQuery)
    }

    /// Остановка наблюдения
        func stopObserver() {
            Task {
                try? await healthStore.disableAllBackgroundDelivery()
            }
        }

    /// Вытаскиваем самую последнюю запись пульса
    private func fetchLatestHeartRateSample(onUpdate: @escaping (Double) -> Void) async {
        guard let heartRateType = HKQuantityType.quantityType(forIdentifier: .heartRate) else { return }

        let predicate = HKQuery.predicateForSamples(withStart: Date().addingTimeInterval(-60), end: Date(), options: .strictStartDate)
        let sortDescriptor = NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: false)

        let query = HKSampleQuery(sampleType: heartRateType, predicate: predicate, limit: 1, sortDescriptors: [sortDescriptor]) { _, samples, error in
            guard let sample = samples?.first as? HKQuantitySample else { return }

            let hrUnit = HKUnit.count().unitDivided(by: HKUnit.minute())
            let heartRate = sample.quantity.doubleValue(for: hrUnit)

            DispatchQueue.main.async {
                onUpdate(heartRate)
            }
        }

        healthStore.execute(query)
    }
}

