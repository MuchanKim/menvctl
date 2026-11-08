# Sparkle in the app

## Package

Add `https://github.com/sparkle-project/Sparkle` with "Up to Next Major" from a release at least two weeks old. Link the `Sparkle` product to the app target. Xcode embeds the framework automatically. Commit `Package.resolved` so CI builds the same version.

To edit `project.pbxproj` by hand, add these entries:

- `XCRemoteSwiftPackageReference`, listed under `packageReferences` on the project
- `XCSwiftPackageProductDependency`, listed under `packageProductDependencies` on the target
- a `PBXBuildFile` with `productRef`, placed in the target's Frameworks phase

Release notes are embedded in the appcast as Markdown. This needs **Sparkle 2.9 or later in the installed app** (the copy that shows the update, not the new one) on macOS 12 or later. Older Sparkle shows the raw text. All new setups meet this, but check it before migrating an app with an older Sparkle.

## Info.plist

| Key | Value |
|---|---|
| `SUFeedURL` | public: `https://github.com/<owner>/<repo>/releases/latest/download/appcast.xml` · private: `https://raw.githubusercontent.com/<owner>/<repo>/appcast/appcast.xml` |
| `SUPublicEDKey` | from `generate_keys -p` (see signing.md) |
| `SUEnableAutomaticChecks` | `true`. Checks once a day without asking first. Leave it out to let Sparkle ask on the second launch |
| `SUEnableInstallerLauncherService` | `true`, **sandboxed apps only** |

Do not set `SUEnableDownloaderService` when the app already has the outgoing-network entitlement (`ENABLE_OUTGOING_NETWORK_CONNECTIONS` / `com.apple.security.network.client`). The downloader service only exists for sandboxed apps without network access.

## Sandbox entitlements (sandboxed apps only)

```xml
<key>com.apple.security.temporary-exception.mach-lookup.global-name</key>
<array>
	<string>$(PRODUCT_BUNDLE_IDENTIFIER)-spks</string>
	<string>$(PRODUCT_BUNDLE_IDENTIFIER)-spki</string>
</array>
```

If the sandbox comes from build settings (`ENABLE_APP_SANDBOX`), Xcode merges these keys into the entitlements file. To confirm, run `codesign -d --entitlements - <built app>` and check that both names appear with the bundle id filled in.

## Updater

- **Public feed**: a plain `SPUStandardUpdaterController(startingUpdater: true, updaterDelegate: nil, userDriverDelegate: nil)` held by the app is enough. Add a "Check for Updates…" menu item bound to `canCheckForUpdates`.
- **Private feed**: copy `templates/AppUpdater.swift`. It does four things:
  - keeps the token in the Keychain (a generic password, which works in the sandbox without extra entitlements)
  - sends the token as `Authorization: Bearer` through `updater.httpHeaders`, which applies to both the feed and the download
  - switches `Accept` to `application/octet-stream` in `willDownloadUpdate`, because the GitHub asset API returns JSON otherwise
  - refuses checks while no token is set, with a message that points to Settings

  Create it as an `@StateObject` in the `App`, pass it to the commands and the settings view, and add an app menu item:

```swift
CommandGroup(after: .appInfo) {
    Button("Check for Updates…") { updater.checkForUpdates() }
        .disabled(!updater.canCheckForUpdates)
}
```

Settings section for the token (private feed):

```swift
@State private var token = ""

Section("Updates") {
    HStack {
        SecureField("GitHub token", text: $token, prompt: Text(updater.hasToken ? "Saved" : "github_pat_…"))
            .onSubmit(saveToken)
        if !token.isEmpty {
            Button("Save", action: saveToken)
        } else if updater.hasToken {
            Button("Remove") { updater.setToken(nil) }
        }
    }
    Button("Check for Updates…") { updater.checkForUpdates() }
        .disabled(!updater.canCheckForUpdates)
    Text("A fine-grained token for this repository with Contents: Read-only. Stored in the Keychain.")
        .font(.caption).foregroundStyle(.secondary)
    if let message = updater.errorMessage {
        Text(message).font(.caption).foregroundStyle(.red)
    }
}

private func saveToken() {
    let trimmed = token.trimmingCharacters(in: .whitespacesAndNewlines)
    guard !trimmed.isEmpty else { return }
    updater.setToken(trimmed)
    token = ""
}
```

Localize the strings to the app's language.

## Check before moving on

- The Debug build succeeds, and the built app contains `Sparkle.framework`, `SUFeedURL`, `SUPublicEDKey` and, if sandboxed, the mach-lookup entitlements.
- The bundle id, team and sandbox settings did not change. If they change, existing users lose access to their container and security-scoped bookmarks.
