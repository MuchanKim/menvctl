# Swift Concurrency Design

Apply when implementing or reviewing async APIs, task lifetimes, cancellation, isolation, or data transfer in Swift. These are project defaults derived from official guidance; prefer the simplest applicable mechanism and preserve more specific project contracts.

## Execution and Isolation

- Check the target's Swift language mode, compiler version, Default Actor Isolation, and Approachable Concurrency/upcoming-feature settings before reasoning about execution. Do not change build settings as part of an ordinary API edit.
- `async` permits suspension; it does not promise background execution or create a new task. Same-actor synchronous work remains serialized even when multiple tasks call it.
- In Swift 6.2, `NonisolatedNonsendingByDefault` makes nonisolated async functions run on the caller's actor by default. Without that feature, their default execution behavior differs. Do not infer execution from `nonisolated` alone.
- Keep UI-facing mutable state on `MainActor`. Introduce another actor for an actual shared-state isolation boundary, not automatically for every service or model.
- Use `@concurrent` for async work that needs to execute off the caller's actor, such as CPU-intensive processing affecting responsiveness. It changes execution isolation, not task lifetime; it does not spawn a child task. Do not add it to ordinary I/O waits mechanically.

## API Contracts and Data Transfer

- Prefer a direct async return for a single asynchronous result, and `throws` for failure. Use an optional for meaningful absence, not to conceal failure. Avoid redundant `Result` wrappers unless outcomes are intentionally stored or transported as data.
- Express required isolation in type, protocol, and closure signatures. Do not label every service protocol `@MainActor` or `Sendable` without considering its consumers and implementations.
- Prefer immutable `Sendable` values or snapshots when sharing data across isolation domains. Use `sending` when exclusive transfer is the actual contract; not every transferable value needs a globally shareable type.
- Treat `Sendable` as a safety guarantee. Use `nonisolated` only for code that does not require the enclosing isolation. Unsafe opt-outs such as `@unchecked Sendable` or `nonisolated(unsafe)` require a concrete synchronization guarantee; `@preconcurrency` requires a specific interoperability or migration reason. None is a routine diagnostic fix.
- Follow semantic Swift naming; avoid an `Async` suffix or callback-era naming that adds no meaning to a directly returned result. Preserve established public names unless API changes are requested.

## Choose the Task Structure

| Requirement | Preferred mechanism |
| --- | --- |
| The next operation needs the preceding result or ordering | Sequential `await` |
| A fixed set of independent operations whose results belong to this scope | Separate `async let` bindings |
| A dynamic number of operations or completion-order result processing | `withTaskGroup` / `withThrowingTaskGroup` |
| Work tied to a SwiftUI View's presence or input identity | `.task` / `.task(id:)` |
| Entry from a synchronous event into async code, or deliberately independent lifetime | `Task` with explicit lifetime and error ownership |

- Prefer structured children for work belonging to the current operation. Do not create several unstructured `Task` handles merely to await their `.value` results.
- Concurrency requires independent data, side effects, and ordering. Preserve transactional requirements, rate limits, and resource constraints. Do not mechanically parallelize adjacent awaits.
- Use a bounded number of active group children when supported input sizes and resource costs justify a limit. Group results arrive in completion order; carry indices or IDs if output order matters. Do not introduce a general scheduler for a small fixed workload.

### Fixed Independent Work

Assuming these operations can safely run concurrently and both results are required:

```swift
async let profileRequest = loadProfile()
async let permissionsRequest = loadPermissions()

let (profile, permissions) = try await (
    profileRequest,
    permissionsRequest
)
```

- Start each independent operation with a separate binding. `async let (a, b) = (loadA(), loadB())` has one initializer task; it is not equivalent to two child tasks.
- Prefer a tuple join when the results are consumed together. Await at the point of need when results have different consumers; tuple syntax is a readability convention, not a concurrency requirement.
- Observe required results and errors explicitly. An `async let` error is surfaced when its value is awaited; do not assume whichever child fails first immediately interrupts the others. Use group result iteration when completion-order failure observation is required.

## Lifetime, Cancellation, and Failure

- Structured scopes wait for all children to finish, including after cancellation. Cancellation is cooperative, not immediate termination. Unawaited `async let` children are cancelled and awaited on scope exit; a normally returning task group waits for remaining children without automatically cancelling them.
- Consume throwing group results with `try await` so required failures reach the caller. If an error escapes the group body, remaining children are cancelled and awaited. Call `cancelAll()` when returning early and remaining work is no longer needed; it still waits for children to finish.
- `Task {}` is unstructured even inside another task. Context inheritance does not provide structured parent cancellation. For tasks that need cancellation, retain the handle with the lifetime owner and cancel when the work is superseded or no longer needed. Always define how failures are observed.
- Use `Task.detached` only when lack of inherited actor context and task-local values is intentional and independent lifetime management is justified. Prefer `@concurrent` for off-actor execution within the existing task.
- Propagate cancellation through service APIs according to their contract. At a UI boundary, treat recognized cancellation as control flow rather than a user-facing failure. Respect framework-specific cancellation errors instead of checking only `CancellationError`.
- Check cancellation before expensive work and at useful checkpoints in long-running loops. Avoid repetitive checks around every await. Cancellation handlers are for work that needs a cancellation signal while suspended, such as bridging a cancellable callback operation.
- Return partial results only under an explicit API contract. Do not silently turn errors or cancellation into plausible defaults, or add retries and fallbacks without a supported requirement.

## State Across Suspension

- Actor isolation prevents data races, not stale assumptions or transactional races. After `await`, revalidate the state, request identity, or version that the next mutation relies on when another operation could have changed it.
- Keep state transitions that must be observed together free of suspension points. Do not assume actor jobs execute in FIFO order.
- Keep SwiftUI event entry code small and place substantial async orchestration with the state or service owner. For replaceable work such as search, ensure a superseded result cannot overwrite current state; choose cancellation or identity validation according to the operation's guarantees.

## Streams and Callback Interoperability

- Prefer `AsyncSequence` when a new API represents values arriving over time. Preserve an existing observation architecture unless replacement is requested. Define termination, failure, buffering, and consumer lifetime where they affect the contract.
- Use an SDK's native async API when available. Use checked continuations only to bridge callback APIs that lack a suitable async form; resume exactly once on every completion path.
- Continuations do not automatically cancel the underlying operation. Bridge cancellation when supported, and synchronize completion/cancellation races. For callback-backed streams, release subscriptions on termination and select buffering from actual delivery requirements.
- Never block a thread with a semaphore or synchronous wait to obtain an async result.

## Official References

- [Swift Language Guide: Concurrency](https://docs.swift.org/swift-book/LanguageGuide/Concurrency.html): task structure, cancellation, actors, and sendability.
- [Meet async/await in Swift — WWDC21](https://developer.apple.com/videos/play/wwdc2021/10132/): direct-return async APIs and callback interoperability.
- [Beyond the basics of structured concurrency — WWDC23](https://developer.apple.com/videos/play/wwdc2023/10170/): task ownership, cancellation, and bounded groups.
- [TaskGroup](https://developer.apple.com/documentation/swift/taskgroup) and [SE-0317: async let](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0317-async-let.md): scope exit, result observation, and binding semantics.
- [Embracing Swift concurrency — WWDC25](https://developer.apple.com/videos/play/wwdc2025/268/) and [SE-0461](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0461-async-function-isolation.md): incremental concurrency and Swift 6.2 execution settings.
- [Protect mutable state with Swift actors — WWDC21](https://developer.apple.com/videos/play/wwdc2021/10133/): reentrancy and state consistency.
- [Swift 6 Migration Guide: Common Compiler Errors](https://www.swift.org/migration/documentation/swift-6-concurrency-migration-guide/commonproblems/): isolation, `Sendable`, and `sending`.
- [Explore concurrency in SwiftUI — WWDC25](https://developer.apple.com/videos/play/wwdc2025/266/): UI boundaries and lifecycle integration.
- [AsyncStream](https://developer.apple.com/documentation/swift/asyncstream) and [CheckedContinuation](https://developer.apple.com/documentation/swift/checkedcontinuation): stream termination, buffering, and callback bridging contracts.
