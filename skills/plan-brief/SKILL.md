---
name: plan-brief
description: Create a self-contained HTML planning brief that exposes requirement understanding, scope, scenarios, acceptance criteria and unresolved decisions before implementation. Use when the user or project requests a planning brief or a reviewable explanation of a proposed implementation. Not for reporting completed work, performing implementation or general-purpose documents.
---

# Plan Brief

Make the agent's interpretation reviewable before implementation. Use the project's language; template controls are Korean. Read [references/content.md](references/content.md) for the requirement/scenario/acceptance contract and [references/structure.md](references/structure.md) for HTML markup and validation.

Distinguish **사용자 요구**, **확인된 사실**, **에이전트 제안**, and **미확정 사항**. Minimize inference; proposals and targets must never look like agreed facts or measured outcomes. Give requirements and acceptance criteria stable IDs so a later result brief can report against the same criteria. Cite the original request or document and its version/date; agreement is recorded only when it actually occurred.

## Workflow

1. Gather the request, relevant specifications and any actually inspected repository facts. Establish the source/version, scope and confirmation state. Do not invent requirements to fill a document. Important unresolved choices belong in the decision table; routine implementation details need no new approval gate.
2. Choose a project report location or a directory outside the repository. Keep the HTML body beside the output. Prefer an already ignored directory when working inside Git; do not edit ignore rules automatically.
3. Copy `assets/example/content.html`. Replace all scaffold instructions and remove `data-placeholder` only after replacement. Keep overview and the four required sections: requirements, scenarios, acceptance, decisions. Explain inapplicable items. Show observable pass/fail conditions and the proposed verification method/environment; these are not completed tests.
4. Build with Python 3.9+ (no third-party dependencies or Git required):
   ```sh
   python3 "<skill>/scripts/build.py" "<body.html>" "<report.html>"
   ```
   There is no mode selector. Commit plans, base revisions and diff embeds belong to `result-brief`; this entrypoint rejects result-only arguments. Fix errors; normal failure exits 2 without replacing a previous report. `--draft` produces a labeled incomplete preview, not a completed brief.
5. Validate the output in an available browser, inspect scenario/criteria layout and exercise navigation/theme. The optional existing-Playwright checker is:
   ```sh
   node "<skill>/scripts/check_browser.mjs" "<report.html>" "<screenshots-dir>"
   ```
   Do not install dependencies just for this step. If unavailable, record `브라우저 검증 미실행`; do not claim validated rendering. See the structure reference for exact browser acceptance checks.
6. Deliver the HTML path, what remains unconfirmed and any actual decisions needed. Do not infer implementation authorization from the existence of the document or record a person's approval without a real source. Regenerate after requirements or decisions change; keep stable IDs and explicit criterion changes.

## Boundaries

This skill writes a planning document. It does not implement, run project tests, commit or publish. Use `result-brief` to report actual work later; the two skills are independently usable, and the original request can serve as the requirements source if no planning brief exists.

Keep HTML self-contained and use only trusted authored markup; escape untrusted text. Structural validation checks document shape, not factual accuracy. Saved checkbox state is a personal note, not sign-off. Do not invent choices, metrics, reviewer participation or execution results.
