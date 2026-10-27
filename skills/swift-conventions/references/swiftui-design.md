# SwiftUI Design

Apply these rules when creating or materially changing SwiftUI code. Preserve the project's deployment target, architecture, and observation strategy. Do not refactor unrelated views solely for conformance.

## Progressive Disclosure

- Optimize the common call site before declaration-site convenience. The simplest use should expose only the information required to understand and use the component.
- Give optional presentation and behavior sensible, domain-neutral defaults. Reveal demonstrated customization through focused overloads, configuration values, or chainable modifier-style methods.
- Keep required semantic content and actions visible at the call site while hiding implementation plumbing.
- Prefer composing orthogonal capabilities to adding cases for every possible combination.
- Judge the design from representative simple and advanced call sites. Complexity should grow with the use case, and every argument or modifier should communicate necessary intent.

## View Composition and Dependencies

- Decompose screens into small, cohesive subviews so each `body` presents one readable level of visual hierarchy and primary data flow.
- Extract meaningful visual or behavioral sections with names that communicate their role and inputs limited to the data they use.
- Keep a trivial fragment inline when extraction would add only indirection, pass-through parameters, or a name without an independent concept.
- Do not pass an entire model to a child that semantically depends on only a narrow value or action. Do not fragment a model solely to reduce updates without an ownership, lifetime, or measured performance reason.
- Choose `Environment` by shared scope and ownership, not update frequency alone. Inject shared Observable models at the hierarchy that owns them; evaluate update cost from properties actually read and measured behavior.

## State and Observation

- Maintain one source of truth. The parent owns why and when a component appears, the domain event, and the payload or message to present.
- The component owns how it renders and manages its visual lifecycle, including layout, styling, animation, local timing, cancellation, and cleanup.
- For the project's Observation-based code, use private `@State` for View-owned values and Observable model lifetimes, `@Bindable` when bindings into a supplied Observable model are required, and `@Environment` for models shared through a View hierarchy. Otherwise, a supplied Observable model can be a plain property. A plain property does not make a referenced model immutable; mutate it through its intended domain API.
- Use `Binding` when a component must mutate a value owned by its parent. Do not copy an external source of truth into `@State` merely to make it locally mutable.
- Avoid imperative `show()` APIs and components that infer business outcomes such as request failure or copy success.

## Transient Presentation

- When transient UI carries a payload, prefer one optional item as the presentation state instead of a separate `Bool` and payload. Use item identity when consecutive equivalent events must still produce distinct presentations.
- Use a `Bool` binding when the on/off state itself is meaningful and no payload is required.
- Let the component manage automatic dismissal only when it is a presentation concern. Keep duration control in the parent when it affects business behavior.

## Identity and Type Erasure

- Use stable, domain-derived identity for dynamic data. Do not generate a new identifier whenever an existing element's ID is read.
- Preserve structural identity when the same conceptual View changes appearance or state. Use distinct conditional branches when the alternatives intentionally represent different identities and lifetimes.
- Avoid `AnyView` by default because it hides structural type and identity information. Prefer `some View`, `@ViewBuilder`, generics, and explicit conditional composition.
- Use `AnyView` only at a real dynamic heterogeneous-storage boundary where type erasure is required, and keep that boundary narrow.

## Main-Actor and Concurrent SwiftUI APIs

- Declare app-owned types conforming to `View` explicitly `@MainActor`, even when conformance already implies main-actor isolation, so the UI boundary remains visible in source.
- Respect the actual isolation requirements of `Shape`, `Layout`, and SwiftUI callbacks instead of applying `@MainActor` mechanically to nonisolated requirements. `@Sendable` alone does not specify execution location; a closure can be both `@MainActor` and `@Sendable`.
- For callbacks that execute outside the owning actor, prefer API-supplied values and capture only the transferable data needed. Do not access actor-isolated state directly there. A callback isolated to the same actor may access that actor's state.
- For async work, cancellation, or isolation diagnostics, also read [Swift Concurrency Design](swift-concurrency-design.md). Keep UI-specific isolation conventions above; apply the shared concurrency rules there.

## Performance Decisions

- Keep View dependencies limited to values the View actually reads, but do not split every dependency into a separate View or model mechanically.
- Use `EquatableView` or `.equatable()` only after evidence shows redundant child updates are material and equality can include every input that affects rendering. An incomplete equality definition can suppress a required update and display stale UI.
- Reshape or split a model when ownership, lifetime, transactional consistency, or measured update scope establishes a real boundary. Do not split a model based only on size or an assumed performance benefit.
- Profile an observed performance problem before adding caching, memoization, custom equality, or other optimization-specific structure.

## Accessibility

- Prefer semantic controls such as `Button`, `Toggle`, and `NavigationLink` for their corresponding interactions, and customize their appearance without replacing their behavior with a tap gesture alone.
- Preserve accessible labels, values, and actions in custom components. Add explicit accessibility metadata where built-in semantics are insufficient; do not duplicate labels that the standard control already supplies.
- Support Dynamic Type using semantic text styles or appropriately scaled custom fonts, and let layouts accommodate larger text. Avoid fixed text containers that clip required content.
- Respect Reduce Motion for custom motion effects. Reduce or replace substantial movement while preserving feedback and the meaning of state changes.

## Sources

- [The craft of SwiftUI API design: Progressive disclosure](https://developer.apple.com/videos/play/wwdc2022/10059/)
- [Data Flow Through SwiftUI](https://developer.apple.com/videos/play/wwdc2019/226/)
- [Demystify SwiftUI](https://developer.apple.com/videos/play/wwdc2021/10022/)
- [Discover Observation in SwiftUI](https://developer.apple.com/videos/play/wwdc2023/10149/)
- [Demystify SwiftUI performance](https://developer.apple.com/videos/play/wwdc2023/10160/)
- [Explore concurrency in SwiftUI](https://developer.apple.com/videos/play/wwdc2025/266/)
- [Optimize SwiftUI performance with Instruments](https://developer.apple.com/videos/play/wwdc2025/306/)
- [`EquatableView`](https://developer.apple.com/documentation/swiftui/equatableview)
- [`View.equatable()`](https://developer.apple.com/documentation/swiftui/view/equatable%28%29)
- [SE-0434: Usability of global-actor-isolated types](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0434-global-actor-isolated-types-usability.md)
- [Accessibility modifiers](https://developer.apple.com/documentation/swiftui/view-accessibility)
- [Get started with Dynamic Type](https://developer.apple.com/videos/play/wwdc2024/10074/)
- [Reduce Motion](https://developer.apple.com/documentation/swiftui/environmentvalues/accessibilityreducemotion)
