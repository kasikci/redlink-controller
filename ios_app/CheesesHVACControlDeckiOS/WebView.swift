import SwiftUI
import WebKit

enum LoadState: Equatable {
    case loading
    case loaded
    case failed(String)
}

struct WebView: UIViewRepresentable {
    let url: URL
    @Binding var loadState: LoadState

    func makeCoordinator() -> Coordinator {
        Coordinator(loadState: $loadState)
    }

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = context.coordinator
        context.coordinator.currentURL = url
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {
        if context.coordinator.currentURL != url {
            context.coordinator.currentURL = url
            uiView.load(URLRequest(url: url))
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
