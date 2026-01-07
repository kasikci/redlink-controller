import XCTest
@testable import CheesesHVACControlDeckiOS

final class AppSettingsTests: XCTestCase {
    func testDefaultURLPrefersEnvironment() {
        let env = ["REDLINK_IOS_URL": "http://example.com:8000"]
        let result = AppSettings.defaultURLString(environment: env, infoPlistValue: "http://plist")
        XCTAssertEqual(result, "http://example.com:8000")
    }

    func testDefaultURLFallsBackToInfoPlist() {
        let result = AppSettings.defaultURLString(environment: [:], infoPlistValue: "http://plist")
        XCTAssertEqual(result, "http://plist")
    }

    func testNormalizeURLAddsScheme() {
        let result = AppSettings.normalizeURLString("192.168.1.5:8000")
        XCTAssertEqual(result, "http://192.168.1.5:8000")
    }

    func testUpdateURLPersistsValue() {
        let defaults = makeUserDefaults()
        let settings = AppSettings(
            userDefaults: defaults,
            environment: [:],
            infoPlistValue: "http://localhost:8000"
        )

        XCTAssertTrue(settings.updateURL("192.168.1.5:8000"))
        XCTAssertEqual(
            defaults.string(forKey: AppSettings.serverURLKey),
            "http://192.168.1.5:8000"
        )
        XCTAssertEqual(settings.controllerURL.absoluteString, "http://192.168.1.5:8000")
    }

    func testUpdateURLRejectsInvalidValue() {
        let defaults = makeUserDefaults()
        let settings = AppSettings(
            userDefaults: defaults,
            environment: [:],
            infoPlistValue: "http://localhost:8000"
        )

        XCTAssertFalse(settings.updateURL("not a url"))
        XCTAssertNil(defaults.string(forKey: AppSettings.serverURLKey))
    }

    private func makeUserDefaults() -> UserDefaults {
        let suite = "CheesesHVACControlDeckiOSTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suite)!
        defaults.removePersistentDomain(forName: suite)
        return defaults
    }
}
