import Combine
import Foundation
import Security
import Sparkle

/// Sparkle updater for a private GitHub repository.
/// The feed (raw.githubusercontent.com) and the update download (release asset API) both need a
/// read-only GitHub token, which the user enters in Settings and the app keeps in the Keychain.
@MainActor
final class AppUpdater: NSObject, ObservableObject, SPUUpdaterDelegate {
    private static let tokenService = (Bundle.main.bundleIdentifier ?? "app") + ".github-token"

    @Published private(set) var canCheckForUpdates = false
    @Published private(set) var hasToken = false
    @Published private(set) var errorMessage: String?

    private lazy var controller = SPUStandardUpdaterController(startingUpdater: false, updaterDelegate: self, userDriverDelegate: nil)

    override init() {
        super.init()
        controller.updater.publisher(for: \.canCheckForUpdates).assign(to: &$canCheckForUpdates)
        applyToken(Self.loadToken())
        controller.startUpdater()
    }

    func checkForUpdates() {
        controller.checkForUpdates(nil)
    }

    /// Passing nil removes the token. On failure the previous token stays in place.
    func setToken(_ token: String?) {
        let base: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: Self.tokenService]
        var status: OSStatus
        if let token {
            let data = Data(token.utf8)
            status = SecItemUpdate(base as CFDictionary, [kSecValueData as String: data] as CFDictionary)
            if status == errSecItemNotFound {
                var item = base
                item[kSecValueData as String] = data
                status = SecItemAdd(item as CFDictionary, nil)
            }
        } else {
            status = SecItemDelete(base as CFDictionary)
            if status == errSecItemNotFound { status = errSecSuccess }
        }
        guard status == errSecSuccess else {
            errorMessage = "Could not \(token == nil ? "remove" : "save") the token in the Keychain (\(status))."
            return
        }
        errorMessage = nil
        applyToken(token)
    }

    private func applyToken(_ token: String?) {
        hasToken = token != nil
        // Sparkle sends these with both the appcast and the update download. Do not set Accept here:
        // Sparkle overwrites it for the appcast, and willDownloadUpdate sets it for the download.
        controller.updater.httpHeaders = token.map { ["Authorization": "Bearer \($0)"] }
    }

    private static func loadToken() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: tokenService,
            kSecReturnData as String: true,
        ]
        var result: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess, let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    // MARK: SPUUpdaterDelegate

    nonisolated func updater(_ updater: SPUUpdater, mayPerform updateCheck: SPUUpdateCheck) throws {
        // Sparkle calls its delegate on the main thread.
        let hasToken = MainActor.assumeIsolated { updater.httpHeaders?["Authorization"] != nil }
        guard !hasToken else { return }
        throw NSError(domain: "AppUpdater", code: 1, userInfo: [
            NSLocalizedDescriptionKey: "Enter a GitHub token in Settings to check for updates.",
        ])
    }

    nonisolated func updater(_ updater: SPUUpdater, willDownloadUpdate item: SUAppcastItem, with request: NSMutableURLRequest) {
        // The release asset API returns the file itself only for this Accept value.
        request.setValue("application/octet-stream", forHTTPHeaderField: "Accept")
    }
}
