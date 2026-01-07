import AppKit
import Foundation
import SwiftUI
import WebKit

enum LoadState: Equatable {
    case loading
    case loaded
    case failed(String)
}

final class ServerManager: ObservableObject {
    enum Status: Equatable {
        case idle
        case starting
        case running
        case failed(String)
    }

    @Published private(set) var status: Status = .idle

    private var process: Process?
    private var monitorTask: Task<Void, Never>?
    private var logHandle: FileHandle?

    func ensureServer(config: ServerConfig) {
        monitorTask?.cancel()
        monitorTask = Task {
            await MainActor.run { self.status = .starting }
            if await checkHealth(url: config.healthURL) {
                await MainActor.run { self.status = .running }
                return
            }

            do {
                try startProcess(config: config)
            } catch {
                await MainActor.run {
                    self.status = .failed("Failed to start server: \(error.localizedDescription)")
                }
                return
            }

            let ready = await waitForHealth(url: config.healthURL, timeout: 20)
            await MainActor.run {
                self.status = ready
                    ? .running
                    : .failed("Server did not respond on \(config.controllerURL.absoluteString)")
            }
        }
    }

    func stopServer() {
        monitorTask?.cancel()
        if let process, process.isRunning {
            process.terminate()
        }
        process = nil
        logHandle?.closeFile()
        logHandle = nil
        status = .idle
    }

    private func startProcess(config: ServerConfig) throws {
        let process = Process()
        process.executableURL = config.pythonExecutable
        process.arguments = config.pythonArguments + [
            "-m",
            "redlink_controller",
            "--config",
            config.configPath,
            "server",
        ]

        var env = ProcessInfo.processInfo.environment
        env["PYTHONUNBUFFERED"] = "1"
        if let pythonPath = config.pythonPath {
            env["PYTHONPATH"] = pythonPath.path
        }
        process.environment = env

        if let serverCwd = config.serverCwd {
            process.currentDirectoryURL = serverCwd
        }

        try FileManager.default.createDirectory(
            at: config.configDirectory,
            withIntermediateDirectories: true
        )

        let logHandle = try openLogFile(at: config.logURL)
        process.standardOutput = logHandle
        process.standardError = logHandle
        self.logHandle = logHandle

        process.terminationHandler = { [weak self] process in
            Task { @MainActor in
                guard let self else { return }
                if case .idle = self.status {
                    return
                }
                let reason = process.terminationReason == .exit ? "exit" : "signal"
                self.status = .failed("Server terminated (\(reason) \(process.terminationStatus)).")
            }
        }

        try writeLaunchSummary(
            to: logHandle,
            config: config,
            executable: process.executableURL,
            arguments: process.arguments,
            environment: process.environment
        )
        try process.run()
        self.process = process
    }

    private func openLogFile(at url: URL) throws -> FileHandle {
        let directory = url.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        if !FileManager.default.fileExists(atPath: url.path) {
            FileManager.default.createFile(atPath: url.path, contents: nil)
        }
        let handle = try FileHandle(forWritingTo: url)
        try? handle.truncate(atOffset: 0)
        return handle
    }

    private func writeLaunchSummary(
        to handle: FileHandle,
        config: ServerConfig,
        executable: URL?,
        arguments: [String]?,
        environment: [String: String]?
    ) throws {
        let timestamp = ISO8601DateFormatter().string(from: Date())
        let command = ([executable?.path ?? "python"] + (arguments ?? [])).joined(separator: " ")
        let pythonPath = environment?["PYTHONPATH"] ?? "(unset)"
        let cwd = config.serverCwd?.path ?? "(none)"
        let lines = [
            "=== Launch \(timestamp) ===",
            "Command: \(command)",
            "CWD: \(cwd)",
            "Config: \(config.configPath)",
            "PYTHONPATH: \(pythonPath)",
            ""
        ]
        if let data = lines.joined(separator: "\n").data(using: .utf8) {
            try handle.write(contentsOf: data)
        }
    }

    private func checkHealth(url: URL) async -> Bool {
        var request = URLRequest(url: url)
        request.timeoutInterval = 1.0
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            if let httpResponse = response as? HTTPURLResponse {
                return (200..<400).contains(httpResponse.statusCode)
            }
        } catch {
            return false
        }
        return false
    }

    private func waitForHealth(url: URL, timeout: TimeInterval) async -> Bool {
        let start = Date()
        while Date().timeIntervalSince(start) < timeout {
            if let process, !process.isRunning {
                return false
            }
            if await checkHealth(url: url) {
                return true
            }
            try? await Task.sleep(nanoseconds: 500_000_000)
        }
        return false
    }
}

struct ServerConfig {
    let controllerURL: URL
    let configPath: String
    let pythonExecutable: URL
    let pythonArguments: [String]
    let serverCwd: URL?
    let pythonPath: URL?
    let logURL: URL

    var healthURL: URL {
        controllerURL.appendingPathComponent("api/health")
    }

    var configDirectory: URL {
        URL(fileURLWithPath: configPath).deletingLastPathComponent()
    }

    static func load() -> ServerConfig {
        let env = ProcessInfo.processInfo.environment
        let controllerURL = URL(string: env["REDLINK_UI_URL"] ?? "http://localhost:8000")!
        let repoRoot = findRepoRoot()
        let bundlePython = bundledPythonRoot()
        let bundledPythonExecutable = bundledVenvPython()

        let configPath = env["REDLINK_CONFIG_PATH"]
            ?? repoRoot?.appendingPathComponent("config.json").path
            ?? defaultConfigPath()

        let serverCwd = env["REDLINK_SERVER_CWD"].map { URL(fileURLWithPath: $0) }
            ?? repoRoot
            ?? bundlePython

        let pythonPath = bundlePython ?? repoRoot

        let (pythonExecutable, pythonArguments) = resolvePythonExecutable(
            env["REDLINK_PYTHON"],
            bundledPythonExecutable: bundledPythonExecutable
        )

        let logURL = URL(fileURLWithPath: env["REDLINK_LOG_PATH"] ?? defaultLogPath())

        return ServerConfig(
            controllerURL: controllerURL,
            configPath: configPath,
            pythonExecutable: pythonExecutable,
            pythonArguments: pythonArguments,
            serverCwd: serverCwd,
            pythonPath: pythonPath,
            logURL: logURL
        )
    }

    private static func defaultConfigPath() -> String {
        let supportDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        return supportDir
            .appendingPathComponent("CheesesHVACControlDeck", isDirectory: true)
            .appendingPathComponent("config.json")
            .path
    }

    private static func defaultLogPath() -> String {
        let supportDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        return supportDir
            .appendingPathComponent("CheesesHVACControlDeck", isDirectory: true)
            .appendingPathComponent("server.log")
            .path
    }

    private static func findRepoRoot() -> URL? {
        let fileManager = FileManager.default
        let currentDir = URL(fileURLWithPath: fileManager.currentDirectoryPath)
        let bundleDir = Bundle.main.bundleURL

        for base in [currentDir, bundleDir] {
            if let root = searchUpwards(from: base) {
                return root
            }
        }
        return nil
    }

    private static func bundledPythonRoot() -> URL? {
        guard let resources = Bundle.main.resourceURL else {
            return nil
        }
        let pythonRoot = resources.appendingPathComponent("python")
        let packagePath = pythonRoot.appendingPathComponent("redlink_controller")
        if FileManager.default.fileExists(atPath: packagePath.path) {
            return pythonRoot
        }
        return nil
    }

    private static func bundledVenvPython() -> URL? {
        guard let resources = Bundle.main.resourceURL else {
            return nil
        }
        let python = resources.appendingPathComponent("venv/bin/python3")
        if FileManager.default.isExecutableFile(atPath: python.path) {
            return python
        }
        return nil
    }

    private static func searchUpwards(from start: URL) -> URL? {
        var current = start
        for _ in 0..<6 {
            let candidate = current.appendingPathComponent("redlink_controller")
            if FileManager.default.fileExists(atPath: candidate.path) {
                return current
            }
            current.deleteLastPathComponent()
        }
        return nil
    }

    private static func resolvePythonExecutable(
        _ override: String?,
        bundledPythonExecutable: URL?
    ) -> (URL, [String]) {
        let overrideValue = override?.trimmingCharacters(in: .whitespacesAndNewlines)
        if let overrideValue, !overrideValue.isEmpty {
            if overrideValue.contains("/") {
                let url = URL(fileURLWithPath: overrideValue)
                return (url, [])
            }
            if let resolved = resolveCommand(overrideValue) {
                return (resolved, [])
            }
            return (URL(fileURLWithPath: "/usr/bin/env"), [overrideValue])
        }

        if let bundledPythonExecutable {
            return (bundledPythonExecutable, [])
        }

        if let resolved = resolveCommand("python3") {
            return (resolved, [])
        }

        return (URL(fileURLWithPath: "/usr/bin/env"), ["python3"])
    }

    private static func resolveCommand(_ name: String) -> URL? {
        let candidates = [
            "/opt/homebrew/bin/\(name)",
            "/usr/local/bin/\(name)",
            "/usr/bin/\(name)",
        ]
        for path in candidates {
            if FileManager.default.isExecutableFile(atPath: path) {
                return URL(fileURLWithPath: path)
            }
        }
        return nil
    }
}

@main
struct CheesesHVACControlDeckApp: App {
    @StateObject private var serverManager = ServerManager()

    var body: some Scene {
        WindowGroup {
            ContentView(serverManager: serverManager)
                .onReceive(NotificationCenter.default.publisher(for: NSApplication.willTerminateNotification)) { _ in
                    serverManager.stopServer()
                }
        }
    }
}

struct ContentView: View {
    @ObservedObject var serverManager: ServerManager
    @State private var loadState: LoadState = .loading
    @State private var reloadToken = UUID()

    private let serverConfig = ServerConfig.load()

    var body: some View {
        ZStack {
            WebView(url: serverConfig.controllerURL, loadState: $loadState)
                .id(reloadToken)

            switch serverManager.status {
            case .starting:
                ProgressView("Starting local server...")
                    .padding(16)
                    .background(.ultraThinMaterial)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
            case let .failed(message):
                failureView(message: message)
            default:
                if case let .failed(message) = loadState {
                    failureView(message: message)
                } else if loadState == .loading {
                    ProgressView("Connecting...")
                        .padding(16)
                        .background(.ultraThinMaterial)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                }
            }
        }
        .frame(minWidth: 1100, minHeight: 720)
        .onAppear {
            serverManager.ensureServer(config: serverConfig)
        }
        .onChange(of: serverManager.status) { status in
            if status == .running {
                reloadToken = UUID()
            }
        }
    }

    @ViewBuilder
    private func failureView(message: String) -> some View {
        VStack(spacing: 12) {
            Text("Unable to reach the controller")
                .font(.title2)
                .bold()
            Text(message)
                .font(.body)
                .foregroundStyle(.secondary)
            Text("URL: \(serverConfig.controllerURL.absoluteString)")
                .font(.footnote)
                .foregroundStyle(.secondary)
            Text("Config: \(serverConfig.configPath)")
                .font(.footnote)
                .foregroundStyle(.secondary)
            Text("Log: \(serverConfig.logURL.path)")
                .font(.footnote)
                .foregroundStyle(.secondary)
            HStack(spacing: 12) {
                Button("Retry") {
                    loadState = .loading
                    reloadToken = UUID()
                    serverManager.ensureServer(config: serverConfig)
                }
                .buttonStyle(.borderedProminent)

                Button("Open Log") {
                    NSWorkspace.shared.open(serverConfig.logURL)
                }
                .buttonStyle(.bordered)

                Button("Open Config") {
                    NSWorkspace.shared.open(URL(fileURLWithPath: serverConfig.configPath))
                }
                .buttonStyle(.bordered)
            }
        }
        .padding(24)
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 18))
        .shadow(radius: 20)
        .padding()
    }
}

struct WebView: NSViewRepresentable {
    let url: URL
    @Binding var loadState: LoadState

    func makeCoordinator() -> Coordinator {
        Coordinator(loadState: $loadState)
    }

    func makeNSView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = context.coordinator
        context.coordinator.currentURL = url
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateNSView(_ nsView: WKWebView, context: Context) {
        if context.coordinator.currentURL != url {
            context.coordinator.currentURL = url
            nsView.load(URLRequest(url: url))
        }
    }

    final class Coordinator: NSObject, WKNavigationDelegate {
        @Binding var loadState: LoadState
        var currentURL: URL?

        init(loadState: Binding<LoadState>) {
            _loadState = loadState
        }

        func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
            loadState = .loading
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            loadState = .loaded
        }

        func webView(
            _ webView: WKWebView,
            didFail navigation: WKNavigation!,
            withError error: Error
        ) {
            if shouldIgnoreLoadError(error) {
                return
            }
            loadState = .failed(error.localizedDescription)
        }

        func webView(
            _ webView: WKWebView,
            didFailProvisionalNavigation navigation: WKNavigation!,
            withError error: Error
        ) {
            if shouldIgnoreLoadError(error) {
                return
            }
            loadState = .failed(error.localizedDescription)
        }

        private func shouldIgnoreLoadError(_ error: Error) -> Bool {
            let nsError = error as NSError
            if nsError.domain == NSURLErrorDomain && nsError.code == NSURLErrorCancelled {
                return true
            }
            if nsError.domain == "WebKitErrorDomain" && nsError.code == 102 {
                return true
            }
            return false
        }
    }
}
