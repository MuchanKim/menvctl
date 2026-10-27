---
name: swift-testing-pro
description: Write or review Swift Testing tests, fixtures, and assertions. Use when editing tests, diagnosing test failures, or explicitly migrating XCTest tests.
license: MIT
metadata:
  author: Paul Hudson
  version: "1.0"
---

Write and review Swift Testing code for correctness, modern API usage, and adherence to project conventions. Report only genuine problems - do not nitpick or invent issues.

Follow the project's configured Swift language version, SDK, deployment target, concurrency settings, and existing architecture. Apply personal conventions from `swift-conventions` when available; project instructions and local style take precedence. Do not upgrade build settings, reorganize unrelated code, or expand a focused task into a full audit.

Reference routing: choose only the checks relevant to the requested change or review. The list below is not a mandatory sequence.

1. Ensure tests follow core Swift Testing conventions using `references/core-rules.md`.
1. Validate test structure, assertions, dependency injection, and other best practices using `references/writing-better-tests.md`.
1. Check async tests, confirmations, time limits, actor isolation, and networking mocks using `references/async-tests.md`.
1. Ensure new features like raw identifiers, test scopes, exit tests, and attachments are used correctly using `references/new-features.md`.
1. If migrating from XCTest, follow the conversion guidance in `references/migrating-from-xctest.md`.

If doing partial work, load only the relevant reference files.


## Core Instructions

- Use Swift Testing where the project uses it or the requested change adopts it. Migrate existing XCTest tests only when requested.
- Swift Testing does *not* support UI tests – XCTest must be used there.
- Preserve the project's existing test organization.

Check API availability against the installed toolchain and current official documentation. Apply newer features only when the project supports them.


## Output Format

If the user asks for a review, organize findings by file. For each issue:

1. State the file and relevant line(s).
2. Name the rule being violated.
3. Show a brief before/after code fix.

Skip files with no issues. End with a prioritized summary of the most impactful changes to make first.

If the user asks you to write or improve tests, follow the same rules above but make the changes directly instead of returning a findings report.

Example output:

### UserTests.swift

**Line 5: Use struct, not class, for test suites.**

```swift
// Before
class UserTests: XCTestCase {

// After
struct UserTests {
```

**Line 12: Use `#expect` instead of `XCTAssertEqual`.**

```swift
// Before
XCTAssertEqual(user.name, "Taylor")

// After
#expect(user.name == "Taylor")
```

**Line 30: Use `#require` for preconditions, not `#expect`.**

```swift
// Before
#expect(users.isEmpty == false)
let first = users.first!

// After
let first = try #require(users.first)
```

### Summary

1. **Fundamentals (high):** Test suite on line 5 should be a struct, not a class inheriting from `XCTestCase`.
2. **Migration (medium):** `XCTAssertEqual` on line 12 should be migrated to `#expect`.
3. **Assertions (medium):** Force-unwrap on line 30 should use `#require` to unwrap safely and stop the test early on failure.

End of example.


## References

- `references/core-rules.md` - core Swift Testing rules: structs over classes, `init`/`deinit` over setUp/tearDown, parallel execution, parameterized tests, `withKnownIssue`, and tags.
- `references/writing-better-tests.md` - test hygiene, structuring tests, hidden dependencies, `#expect` vs `#require`, `Issue.record()`, `#expect(throws:)`, and verification methods.
- `references/async-tests.md` - serialized tests, `confirmation()`, time limits, actor isolation, testing pre-concurrency code, and mocking networking.
- `references/new-features.md` - raw identifiers, range-based confirmations, test scoping traits, exit tests, attachments, `ConditionTrait.evaluate()`, and the updated `#expect(throws:)` return value.
- `references/migrating-from-xctest.md` - XCTest-to-Swift Testing conversion steps, assertion mappings, and floating-point tolerance via Swift Numerics.
