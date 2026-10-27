# Swift Testing Guide

Apply when selecting test coverage or writing or reviewing Swift tests. Follow the existing test target, framework, and directory conventions. These are team defaults informed by Apple's testing guidance; fixture organization is a team preference, not an Apple requirement.

## Scope and Reachability

- Select cases from current requirements, supported input contracts, reachable changed behavior, or a reproduced regression. Be able to explain the behavior each test protects; do not add tests merely because a branch or helper exists.
- Trace callers, validation, and state transitions before declaring a case reachable or impossible. Do not bypass validated constructors or manufacture impossible private state just to cover defensive code. Rare but reachable failures remain valid test cases.
- Test malformed external input at the boundary responsible for rejecting it. A decoder rejecting a missing required field is meaningful; forcing that field to be absent in an already validated non-optional domain model is not.
- Cover distinct outcomes and meaningful boundaries. Use representative equivalence classes rather than every input combination. Parameterize cases when they exercise the same rule; do not create large matrices without distinct failure risks.
- Prefer the smallest test level that proves the behavior. Add integration or UI coverage when the risk lies in wiring or user interaction; do not repeat every unit case through UI automation. Respect existing coverage requirements without inventing a new percentage or test-count target.

## Assertions and Testability

- Assert observable results, state transitions, and required side effects. Do not mirror the implementation to calculate the expected result, inspect source text, or retest trivial storage and framework behavior without a project-specific contract.
- Verify call counts or order only when they are part of required behavior, such as preventing duplicate submission. Avoid assertions coupled to incidental helper calls or internal sequencing.
- Keep the setup, action, and expected outcome readable in the test. One test should communicate one behavior, though it may need several related assertions.
- Use existing dependency boundaries for isolation. Do not widen production visibility, add test-only branches, or introduce a protocol solely to reach an implementation detail. If testing exposes a real architectural problem, identify it before expanding the implementation scope.

## Fixtures and Test Doubles

- Put fixture factories, payload resources, and mock, stub, or fake type definitions in separate files under the test target, near their feature or in the existing test-support directory. Do not move unrelated existing tests merely to match this layout.
- A fixture supplies data; a stub supplies a chosen response; a spy/mock records or verifies interactions; a fake provides simplified working behavior. Use only the capabilities required by the test, not a configurable imitation of the entire service.
- Keep scenario-defining values, response selection, and expected results visible at the test call site. Tiny scalar literals can remain inline; do not hide the tested distinction behind a large default fixture or builder.
- Use fresh mutable test doubles and state per test. Immutable fixtures may be shared; do not share mutable static mocks or depend on test execution order.
- Give defaults to incidental valid data only. Make relevant error responses and edge conditions explicit. Unexpected calls should fail clearly rather than silently returning success or plausible default data.
- Keep support code in test targets. Reuse preview support only when it already fits the same contract and isolation needs; never use test fixtures as production error fallbacks.

Illustrative layout; create only the files needed for the current tests and adapt names to the repository:

```text
FeatureTests/
  ProfileModelTests.swift
  Fixtures/
    UserProfileFixtures.swift
  TestDoubles/
    ProfileLoaderStub.swift
```

## Async Tests and Framework Choice

- Prefer Swift Testing for new unit tests when the project's toolchain and conventions support it. Preserve existing XCTest tests unless migration is requested. Use XCTest/XCUIAutomation for UI tests and XCTest for its performance-measurement APIs; do not mix assertion APIs within one test.
- Make tests `async` or `async throws` and await the actual operation. For ordering or cancellation behavior, coordinate with explicit completion signals or controllable dependencies rather than arbitrary sleeps or assumptions about task scheduling.
- Keep unit tests independent of live network services and uncontrolled time, randomness, or persistent state. Control only the dependency relevant to the behavior; do not add a clock or scheduler abstraction to every test.
- Isolate mutable resources for parallel execution. Use serialization only for an identified shared-resource requirement, not to hide order-dependent tests or races.
- After the relevant checks pass, stop unless a new change or unresolved risk justifies more verification. Report what ran and any remaining gap; a coverage number alone does not establish correctness.

## Official References

- [Testing in Xcode](https://developer.apple.com/documentation/xcode/testing): roles of unit, integration, and UI coverage.
- [Adding tests to your Xcode project](https://developer.apple.com/documentation/xcode/adding-tests-to-your-xcode-project): test targets and framework selection.
- [XCTest](https://developer.apple.com/documentation/xctest): Swift Testing coexistence, UI tests, and performance tests.
- [Swift Testing](https://developer.apple.com/documentation/testing): assertions, parameterized tests, and concurrency support.
