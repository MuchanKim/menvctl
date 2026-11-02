---
name: result-brief
description: Create a self-contained HTML result brief for completed code changes, mapping requirements to actual changes and verification evidence, mandatory review points and merge conditions. Use when the user or project requests a result brief, implementation report, work report or review handoff after implementation. Not for planning proposed work or performing code review itself.
---

# Result Brief

Report what was actually done and observed so the reviewer can judge delivery. Use the project's language; template controls are Korean. Read [references/content.md](references/content.md) for evidence and reviewer/merge fields, and [references/structure.md](references/structure.md) for markup, commit plans and supported file types.

Preserve stable requirement/criterion IDs and the agreed source/version from `plan-brief`, if present. Otherwise cite the actual user request or specification; do not invent a prior agreement. Record changed criteria and their authorization explicitly. Separate **implementation state** from **verification state**. A diff or passing build does not establish requirement satisfaction, runtime correctness or performance gains.

## Evidence rules

- Report actual changes, executed checks and measured outcomes. Keep `미실행`, `미측정`, `미검증` and `커버리지 미확인` explicit. Exclude speculative risk scores, invented design rationale and estimated gains. Documented decisions/constraints may be included with their source. Future proposals and manual checks belong in separate unperformed sections.
- Record verification commands/steps, working directory, target revision/tree, environment/device/build, timestamp, result and evidence location. Test/review evidence predating relevant edits is stale until rechecked. Name searches locate candidate tests; inspect call paths and assertions before claiming a gap or coverage.
- Performance claims need comparable before/after observations, metric/unit, workload, sample count, aggregation and raw result source. Without measurements, describe the code change and say performance was not measured.
- Each reviewer-focus item states what changed, why review is required and its source, the diff/path, and the acceptance question. Mark **필수** only from an agreed criterion, repository rule or explicit instruction; agent-suggested items remain **제안**.
- Every non-header row in `#merge-checklist` requires `data-check-kind="human|automated|criterion"`, `data-verdict` and `data-basis`; see the content reference for status-specific evidence attributes. Merge rows use `충족 / 미충족 / 미확인 / 해당 없음` with criterion/rule source and evidence or remaining work. N/A needs a reason. Human review completion needs an actual reviewer, time and scope; the agent cannot replace this with passing tests or local checkboxes. There is no universal mandatory second reviewer or device test.
- Every row in the `#verification` table needs `data-verifier` (`script`, `implementer`, `independent`, `human` or `none`) and, unless `none`, `data-verifier-name`, with the same verifier visible in the table. Use the relevant session or specific review record only, never guess model IDs or search unrelated transcripts. Record self-review as `implementer`. Missing reviews stay missing; do not launch a reviewer merely to fill a field.
- Do not write conclusions or summaries on the first screen. `.sub` in the body is rejected. The builder inserts `#auto-facts` after the hero: test verdict from `--verify`, folder diff and test expectation changes. Reviewer findings stay verbatim; label any agent interpretation as such and keep dismissed findings with their reason.
- UI path changes need an embedded `data:` screenshot or `data-screenshot-na="reason"`. The builder fails on suspected secrets and resident registration numbers without printing the value; remove the data instead of working around the check. A file attached to GitHub is hard to delete.

## Workflow

1. Choose the comparison deliberately. Default `HEAD` compares committed base bytes to the final working tree, including staged paths and non-ignored untracked files; it is not a staged-only report. For a branch-wide report resolve the intended merge-base and pass its SHA. Do not assume `main` exists. Inspect the changed file list before embedding source/sensitive local data; agree scope for unrelated work rather than silently omitting it.
2. Choose an existing ignored report directory or a directory outside Git. Keep body, optional commit plan and snapshots together. The builder rejects tracked/non-ignored body/plan/output paths to prevent self-inclusion. Do not edit `.git/info/exclude` automatically.
3. Copy `assets/example/content.html`, replace all scaffold instructions/claims and then remove `data-placeholder`. Required overview sections: changes, metrics, impact, requirements, review-focus, verification, merge-checklist, follow-up; also include the all-files tab. Put the planning document link in the hero `meta`. `metrics` reports measured values or `미측정`. `impact` lists changed symbols and the references found by an actual search. `follow-up` holds the user's device test items, or why there are none. Explicitly explain inapplicable sections. The first screen should show actual outcomes and remaining review/verification, with diffs as supporting evidence.
4. Write `commits.json` following project rules and the structure reference; the builder rejects a report with changes and no plan. Each commit shows its message, diff and added details. Repeated-file snapshots represent the cumulative state after each commit, including mode/type; intermediate deletions are explicit. File overlap does not prove independent buildability.
5. Build from inside the target repository (Python 3.9+, Git; no third-party Python dependencies):
   ```sh
   python3 "<skill>/scripts/build.py" "<body.html>" "<report.html>" --base HEAD --plan "<commits.json>"
   ```
   Pass `--plan "<commits.json>"`. Pass `--verify "<record.json>"` when the project writes a test verdict record; a record whose `tree` differs from the working tree fails the build, so rerun the tests, and a record with `source` other than `run` fails too. Pass `--review "<review.txt>"` with first line `tree <id>` and the reviewer's verbatim output after it; a different tree fails the build. `--strip-prefix App/` affects displayed paths. There is no mode selector. Fix validation errors; failure exits 2 without replacing the old report. `--draft` creates a visibly incomplete preview and must not be presented for approval. Hard Git/path/schema errors still fail.
6. Validate every tab in an available browser, inspect overview and a commit screenshot if commits exist, and try search/theme/navigation/manual checkboxes. Require `window.reviewBriefValidation.ready === true`, empty `.errors`, no unresolved diff embeds and no console errors. Optional checker:
   ```sh
   node "<skill>/scripts/check_browser.mjs" "<report.html>" "<screenshots-dir>"
   ```
   It uses existing Playwright only; environment overrides are in the structure reference. Do not install dependencies automatically. If unavailable, deliver with `브라우저 검증 미실행`, never claim validated rendering. Browser QA is separate from project tests.
7. Confirm the report matches the final change. Rebuild/revalidate after code, plan or checklist edits; saved checks reset with the fingerprint. Deliver the HTML path and verification limits. Ask for commit approval only when the requested workflow requires it and approval remains missing. Never infer approval to merge from a completed report.

## Boundaries

This skill generates a report; it does not implement fixes, run project tests, commit, merge, publish, add dependencies or change ignore rules automatically. Complete project verification under the actual task authorization before reporting it. Use `plan-brief` for proposed work. Rollback descriptions must distinguish uncommitted undo from reverting published commits and cite concrete prerequisites; do not execute them as part of reporting.

Keep output self-contained, with no remote fonts/scripts/images/CSS imports. Body and plan metadata are trusted authored HTML; escape untrusted content and literal `<` in embedded JSON as `\u003c`. Do not put executable scripts in the body. Structural evidence checks cannot prove a source exists or supports a claim; inspect the actual evidence. Human approval and a personal checklist remain distinct.
