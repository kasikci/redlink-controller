import Foundation
import SwiftUI

final class AppSettings: ObservableObject {
    static let serverURLKey = "RedlinkControllerURL"

    @Published private(set) var controllerURL: URL
    @Published private(set) var controllerURLString: String

    private let userDefaults: UserDefaults

    init(
        userDefaults: UserDefaults = .standard,
        environment: [String: String] = ProcessInfo.processInfo.environment,
        infoPlistValue: String? = Bundle.main.object(forInfoDictionaryKey: "RedlinkDefaultURL") as? String
    ) {
        self.userDefaults = userDefaults

        let defaultURLString = Self.defaultURLString(
            environment: environment,
            infoPlistValue: infoPlistValue
        )

        let storedValue = userDefaults.string(forKey: Self.serverURLKey) ?? defaultURLString
        let normalizedStored = Self.normalizeURLString(storedValue)

        if let storedURL = Self.parseURL(normalizedStored) {
            controllerURL = storedURL
            controllerURLString = normalizedStored
        } else {
            let normalizedDefault = Self.normalizeURLString(defaultURLString)
            controllerURLString = normalizedDefault
            controllerURL = Self.parseURL(normalizedDefault)
                ?? URL(string: "http://localhost:8000")!
        }
    }

    var healthURL: URL {
        controllerURL.appendingPathComponent("api/health")
    }

    static func defaultURLString(
        environment: [String: String],
        infoPlistValue: String?
    ) -> String {
        if let envValue = environment["REDLINK_IOS_URL"] ?? environment["REDLINK_UI_URL"] {
            let trimmed = envValue.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty {
                return trimmed
            }
        }

        if let infoPlistValue {
            let trimmed = infoPlistValue.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty {
                return trimmed
            }
        }

        return "http://localhost:8000"
    }

    static func normalizeURLString(_ value: String) -> String {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty {
            return trimmed
        }
        if trimmed.contains("://") {
            return trimmed
        }
        return "http://" + trimmed
    }

    static func parseURL(_ value: String) -> URL? {
        let normalized = normalizeURLString(value)
        guard !normalized.isEmpty else {
            return nil
        }
        guard let url = URL(string: normalized) else {
            return nil
        }
        guard let scheme = url.scheme?.lowercased(), ["http", "https"].contains(scheme) else {
            return nil
        }
        return url
    }

    @discardableResult
    func updateURL(_ value: String) -> Bool {
        let normalized = Self.normalizeURLString(value)
        guard let url = Self.parseURL(normalized) else {
            return false
        }
        controllerURL = url
        controllerURLString = normalized
        userDefaults.set(normalized, forKey: Self.serverURLKey)
        return true
    }
}
