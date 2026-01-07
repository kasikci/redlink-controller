import SwiftUI

struct ContentView: View {
    @ObservedObject var settings: AppSettings
    @ObservedObject var connectionMonitor: ConnectionMonitor

    @State private var loadState: LoadState = .loading
    @State private var reloadToken = UUID()
    @State private var showingSettings = false

    var body: some View {
        ZStack {
            WebView(url: settings.controllerURL, loadState: $loadState)
                .id(reloadToken)
                .ignoresSafeArea()

            overlayView
        }
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    showingSettings = true
                } label: {
                    Image(systemName: "gearshape")
                }
                .accessibilityLabel("Server Settings")
            }
        }
        .sheet(isPresented: $showingSettings) {
            SettingsView(settings: settings)
        }
        .onAppear {
            connectionMonitor.checkHealth(url: settings.healthURL)
        }
        .onChange(of: settings.controllerURL) { _ in
            reloadToken = UUID()
            loadState = .loading
            connectionMonitor.checkHealth(url: settings.healthURL)
        }
    }

    @ViewBuilder
    private var overlayView: some View {
        switch connectionMonitor.status {
        case .checking:
            statusCard(text: "Connecting to server...")
        case let .failed(message):
            failureCard(message: message)
        default:
            if case let .failed(message) = loadState {
                failureCard(message: message)
            } else if loadState == .loading {
                statusCard(text: "Loading controller...")
            }
        }
    }

    private func statusCard(text: String) -> some View {
        VStack(spacing: 12) {
            ProgressView(text)
        }
        .padding(18)
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .shadow(radius: 16)
        .padding()
    }

    private func failureCard(message: String) -> some View {
        VStack(spacing: 12) {
            Text("Unable to reach the controller")
                .font(.title3)
                .bold()
            Text(message)
                .font(.body)
                .foregroundStyle(.secondary)
            Text("URL: \(settings.controllerURL.absoluteString)")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            HStack(spacing: 12) {
                Button("Retry") {
                    loadState = .loading
                    reloadToken = UUID()
                    connectionMonitor.checkHealth(url: settings.healthURL)
                }
                .buttonStyle(.borderedProminent)

                Button("Edit Server") {
                    showingSettings = true
                }
                .buttonStyle(.bordered)
            }
        }
        .padding(20)
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .shadow(radius: 18)
        .padding()
    }
}

struct SettingsView: View {
    @ObservedObject var settings: AppSettings
    @Environment(\.dismiss) private var dismiss

    @State private var urlString: String
    @State private var errorMessage: String?

    init(settings: AppSettings) {
        self.settings = settings
        _urlString = State(initialValue: settings.controllerURLString)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Server") {
                    TextField("http://192.168.1.10:8000", text: $urlString)
                        .keyboardType(.URL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled(true)
                    Text("Use the LAN address where the Redlink server is running.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                if let errorMessage {
                    Text(errorMessage)
                        .font(.footnote)
                        .foregroundColor(.red)
                }
            }
            .navigationTitle("Server Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Save") {
                        if settings.updateURL(urlString) {
                            dismiss()
                        } else {
                            errorMessage = "Enter a valid http(s) URL."
                        }
                    }
                }
            }
        }
    }
}
