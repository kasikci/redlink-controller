import SwiftUI

@main
struct CheesesHVACControlDeckiOSApp: App {
    @StateObject private var settings = AppSettings()
    @StateObject private var connectionMonitor = ConnectionMonitor()

    var body: some Scene {
        WindowGroup {
            NavigationStack {
                ContentView(settings: settings, connectionMonitor: connectionMonitor)
                    .navigationTitle("Cheeses HVAC")
                    .navigationBarTitleDisplayMode(.inline)
            }
        }
    }
}
