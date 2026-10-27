# Swift Golden Examples

Use these small reference examples to interpret the team's conventions. They illustrate decisions, not mandatory names, dimensions, domain types, architecture, or files to copy. Read only the example relevant to the task. All snippets use SwiftUI; the service example also imports Observation.

## Component Customization at the Call Site

The common call supplies meaningful content. A second, current use case needs more space between rows, so it adds one modifier. The component retains its concrete generic content type and native text semantics.

```swift
import SwiftUI

@MainActor
struct InfoCard<Content: View>: View {
    let title: LocalizedStringKey
    let content: Content
    private var spacing: CGFloat = 8

    init(_ title: LocalizedStringKey, @ViewBuilder content: () -> Content) {
        self.title = title
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: spacing) {
            Text(title)
                .font(.headline)
            content
        }
    }

    func contentSpacing(_ spacing: CGFloat) -> Self {
        var copy = self
        copy.spacing = spacing
        return copy
    }
}

@MainActor
private func cardExamples() -> some View {
    VStack {
        InfoCard("배송 정보") {
            Text("내일 도착 예정")
        }

        InfoCard("배송 정보") {
            Text("내일 도착 예정")
            Text("경비실에 맡겨 주세요")
        }
        .contentSpacing(16)
    }
}
```

The custom modifier targets the card's internal row spacing; `.padding()` would change a different part of the layout. Do not add modifiers for every internal property or wrap existing SwiftUI modifiers without an additional component-specific meaning.

## Decomposition by Visual Responsibility

The screen composes an identity section and account actions. Each child receives only its required values or action; neither requires the whole screen model. Labels remain inline inside their section, and the action remains a native `Button`.

```swift
import SwiftUI

@MainActor
struct ProfileScreen: View {
    let name: String
    let email: String
    let onSignOut: () -> Void

    var body: some View {
        VStack(alignment: .leading) {
            ProfileIdentity(name: name, email: email)
            Divider()
            AccountActions(onSignOut: onSignOut)
        }
    }
}

@MainActor
private struct ProfileIdentity: View {
    let name: String
    let email: String

    var body: some View {
        VStack(alignment: .leading) {
            Text(name)
                .font(.headline)
            Text(email)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }
}

@MainActor
private struct AccountActions: View {
    let onSignOut: () -> Void

    var body: some View {
        VStack(alignment: .leading) {
            Text("계정")
                .font(.headline)
            Button("로그아웃", action: onSignOut)
        }
    }
}
```

These sections are separate concepts, not a requirement to extract every stack or label. Decomposition does not automatically require separate source files or independent ViewModels.

## Service Protocol at a Consumer Boundary

The consumer needs one profile-loading operation. The protocol supports a production I/O implementation and a preview substitute without exposing transport details. Here the loader and immutable result are `Sendable` because this boundary supports calls across isolation domains; that is not a requirement for every service protocol.

```swift
import Observation

struct UserProfile: Sendable {
    let name: String
}

protocol ProfileLoading: Sendable {
    func loadProfile() async throws -> UserProfile
}

@MainActor
@Observable
final class ProfileModel {
    private let loader: any ProfileLoading
    private(set) var profile: UserProfile?

    init(loader: any ProfileLoading) {
        self.loader = loader
    }

    func load() async throws {
        profile = try await loader.loadProfile()
    }
}

struct PreviewProfileLoader: ProfileLoading {
    func loadProfile() async throws -> UserProfile {
        UserProfile(name: "김민수")
    }
}
```

The preview consumer can be created with `ProfileModel(loader: PreviewProfileLoader())`; production supplies its real loader at the composition boundary. The model retains the selected implementation behind `any ProfileLoading`. The preview value is explicitly injected, never a fallback for failed production I/O.

This example assumes one load at a time and propagates failure to its caller. Replacement, cancellation, loading indicators, and error presentation belong to the actual feature's contract; they are not silently added by this example.
