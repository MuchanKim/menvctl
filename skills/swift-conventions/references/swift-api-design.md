# Swift API Design

Apply these rules when creating or materially changing a reusable API or service boundary. Evaluate the API at representative call sites, and preserve more specific project conventions.

## Call-Site Clarity

- Prefer clarity over brevity. Judge names, labels, and defaults where the API is used rather than only at its declaration.
- Name values and parameters for their semantic role rather than their concrete type.
- Use argument labels to clarify weakly typed values such as `String`, `Int`, and `Bool`; omit words that merely repeat type information.
- Name side-effecting operations with imperative verbs. Name nonmutating operations as noun phrases or with a consistent nonmutating counterpart such as `sort()` and `sorted()`.

## Required Inputs, Defaults, and Customization

- Put required semantic inputs first and defaulted parameters last.
- Prefer a default parameter to a family of overloads when one value is the clear common case and the parameter remains part of the same operation.
- For reusable SwiftUI components, keep required content and actions in the initializer. Prefer chainable modifier-style methods for demonstrated optional customization; return a new value and follow the project's naming style.
- Do not expose every internal property as public configuration. Each option should represent a current call-site need.

## Abstraction and Protocols

- Start with concrete code. Generalize only after a shared capability, substitution boundary, or repeated behavior is established.
- Define focused protocols at app-facing service, repository, and client boundaries that perform external effects. Keep concrete implementation details behind those boundaries so production, preview, test, or alternate implementations can be substituted without changing consumers.
- Place a protocol at the consumer boundary and express only the capabilities callers require. Do not create protocols for pure value helpers or concrete types with no substitution boundary.
- Prefer a concrete type when no abstraction is required. When abstracting, prefer generics or `some` while static type relationships matter; use `any` when arbitrary conforming values must be stored, erased, or collected heterogeneously.

## Documentation

- Add `///` documentation to reusable APIs when their contract, effects, constraints, or failure behavior is not clear from the declaration and call site.
- Start with a concise summary. Document semantic requirements and non-obvious behavior rather than repeating names and types.
- Do not add documentation comments mechanically to obvious private or local declarations.

## Sources

- [Swift API Design Guidelines](https://www.swift.org/documentation/api-design-guidelines/)
- [Google Swift Style Guide — File Names](https://google.github.io/swift/#file-names): reference for extension filenames, not a Swift language requirement.
- [The Swift Programming Language — Access Control](https://docs.swift.org/swift-book/documentation/the-swift-programming-language/accesscontrol/): private members in same-file extensions.
- [Embrace Swift generics](https://developer.apple.com/videos/play/wwdc2022/110352/)
- [Design protocol interfaces in Swift](https://developer.apple.com/videos/play/wwdc2022/110353/)
