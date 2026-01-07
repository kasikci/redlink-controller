import Foundation

final class ConnectionMonitor: ObservableObject {
    enum Status: Equatable {
        case idle
        case checking
        case connected
        case failed(String)
    }

    @Published private(set) var status: Status = .idle

    private var task: Task<Void, Never>?

    func checkHealth(url: URL) {
        task?.cancel()
        task = Task {
            await MainActor.run { self.status = .checking }

            var request = URLRequest(url: url)
            request.timeoutInterval = 3.0

            do {
                let (_, response) = try await URLSession.shared.data(for: request)
                let success = (response as? HTTPURLResponse).map { (200..<400).contains($0.statusCode) } ?? false
                await MainActor.run {
                    self.status = success ? .connected : .failed("Server did not respond")
                }
            } catch {
                if Task.isCancelled {
                    return
                }
                await MainActor.run {
                    self.status = .failed(error.localizedDescription)
                }
            }
        }
    }

    func reset() {
        task?.cancel()
        status = .idle
    }
}
