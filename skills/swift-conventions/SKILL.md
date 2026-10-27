---
name: swift-conventions
description: Apply personal Swift source organization, API and concurrency design, SwiftUI, and testing conventions when implementing or reviewing Swift code and tests. Use only for Swift changes; defer to more specific project instructions and existing local style.
---

# Swift Conventions

Follow the project's configured Swift language version, concurrency settings, architecture, and local style. This skill defines source organization, Swift API and concurrency design, SwiftUI design, and testing conventions; it does not select architecture or add compatibility code.

Apply these conventions to declarations being added or to files the user explicitly asks to reorganize. Do not reorder otherwise untouched code solely for conformance.

## Design References

- When creating or materially changing a reusable Swift API, service boundary, or public call site, read [Swift API Design](references/swift-api-design.md).
- When implementing or reviewing SwiftUI views, components, state flow, identity, or performance-sensitive structure, read [SwiftUI Design](references/swiftui-design.md).
- When implementing or reviewing async APIs, task lifetimes, cancellation, actor isolation, or cross-isolation data transfer, read [Swift Concurrency Design](references/swift-concurrency-design.md).
- When deciding test coverage or writing or reviewing Swift tests, fixtures, or test doubles, read [Swift Testing Guide](references/swift-testing-guide.md).
- When concrete examples would clarify component customization, View decomposition, or service boundaries, read the matching section of [Swift Golden Examples](references/swift-golden-examples.md).
- Read only the references relevant to the current change. Do not redesign unrelated existing code for conformance.

## Organization Principles

- Order declarations for a reader following the type's state and behavior, rather than alphabetically or by access level.
- Keep declarations with the same role together. Use a blank line only between meaningful groups.
- Place a new declaration with its related group instead of appending it mechanically.
- Prefer clear declaration order and whitespace over a `MARK` section that adds no navigation value.

## Role Naming

- Name a type for its responsibility, not its containing folder. Apply a project's architectural suffix only to types performing that role; a port, value, or error inside a `UseCase` folder is not itself a use case.
- Name identity protocols as nouns and capability protocols with `able`, `ible`, or `ing`, such as `Geocoding`. Name concrete implementations for their role and meaningful specialization, such as `NaverGeocoder`; name the injected dependency for its role, such as `geocoder`.
- Keep `Service`, `Manager`, and similar suffixes only when they clarify the actual abstraction. Do not stack technical suffixes or introduce pass-through types merely to make filenames uniform.
- Keep the primary type and filename aligned. Rename references and test doubles consistently within the authorized scope; do not migrate unrelated APIs.

## Extensions

- Decide responsibility boundaries before file boundaries. Extensions organize or adapt the same type; they do not create independent ownership or isolate state.
- Prefer the same file for tightly coupled implementation and helpers. Use an extension when it clarifies a conformance, constrained API, conversion, or other cohesive capability; do not wrap every method in an extension.
- Use a separate extension file when a cohesive capability or dependency boundary benefits from separate placement, such as UI presentation of a domain value or conversion from an external DTO. Do not split solely by line count.
- Name a conformance file `Type+Protocol.swift`; name another extension file `Type+SpecificRole.swift`, such as `PinCategory+Icon.swift`. Avoid vague suffixes such as `Helpers`, `Extensions`, or `Part2`.
- Do not widen `private` or `fileprivate` solely to move code across files. Same-file extensions can access the type's private members; a separate file is a different access-control boundary.
- If behavior needs its own state, dependencies, or task lifetime, evaluate a separate type rather than distributing a large type across extensions. Introduce it only when the current responsibility requires it.
- Preserve initializer availability, access control, actor isolation, and protocol conformance semantics when moving declarations.

## Korean Comment Style

- Use a concise, neutral technical tone for Korean code comments.
- Prefer a noun phrase when it conveys the full meaning, and omit the final period: `// 서버 응답과 로컬 캐시 비교`.
- When a full explanation is necessary, use the plain declarative endings `~한다.` or `~된다.`: `// 중복 요청을 막기 위해 진행 상태를 먼저 기록한다.`
- Do not use polite endings such as `~합니다.` or `~됩니다.`
- Do not shorten a comment when doing so would obscure its intent, condition, or constraint.

## MARK Comments

Use `// MARK: -` only when it makes a Swift file easier to scan. Omit sections that do not improve navigation, and do not repeat the type name in a label.

Allowed labels:

- `// MARK: - Properties`: stored properties, state, external inputs, and derived properties.
- `// MARK: - Callbacks`: closure properties injected into a SwiftUI `View`; not ViewModel methods, private helpers, or inline actions.
- `// MARK: - Layout`: UI layout constants, normally grouped in a private `Layout` namespace.
- `// MARK: - Methods`: public or internal behavior, lifecycle, and actions; never SwiftUI `body`.
- `// MARK: - Private Methods`: private helpers for the same type, including a private extension containing them.
- `// MARK: - Extensions`: extensions outside the primary type, especially extensions of another type.

Do not use `Dependencies`, `Init`, `Derived`, `Helpers`, `State`, `UI State`, or labels containing the type name as default labels.

For a SwiftUI `View`, prefer `Properties`, `Callbacks`, `body`, then `Private Methods` outside the primary declaration when needed. Keep `body` in the main declaration flow. For a ViewModel, prefer `Properties`, `Methods`, then `Private Methods` when needed.

## Declaration Order

Treat the following orders as the default reading flow. Keep closely related declarations together when a rigid ordering would make the code harder to understand.

### SwiftUI View Properties

1. SwiftUI runtime context and identity, such as `@Environment` and `@Namespace`
2. External inputs, such as `@Bindable`, `@Binding`, and initializer-supplied values
3. View-owned state and Observable models, such as `@State`, plus local presentation state such as `@FocusState`
4. Derived read-only properties and bindings

`@Namespace` belongs to SwiftUI runtime context and identity, not view-local presentation state.

### ViewModel Properties

1. Static configuration
2. Instance identity and initial configuration
3. Dependencies
4. Source-of-truth state loaded from repositories, services, or stores
5. Loading and error state
6. Flow and UI state
7. Derived read-only properties

### Callbacks

Order callbacks by the screen's user flow:

1. Navigation and close actions
2. Primary actions
3. Selection and input actions
4. System events

### Methods

Order public and internal methods by externally readable behavior:

1. Lifecycle
2. User intents and actions
3. Mode or navigation transitions
4. External event handlers
5. Async side effects

### Private Methods

- Put helpers shared by several methods near the top.
- Keep a helper used by one flow near that flow.
- Put pure calculations after the flow they support when that reads naturally.
- Keep error reporting, toast, and logging helpers near the bottom unless the call flow is clearer elsewhere.

### Layout

Order layout constants from broad structure to detail: container values, spacing and insets, then sizes, radii, and icons. Prefer the screen's top-to-bottom reading order when it is clearer.
