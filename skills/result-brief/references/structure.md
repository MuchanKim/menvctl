# Report structure and markup

The body file contains only tab pages. `build.py` wraps it in `assets/template.html`. Numbering, the sidebar, commit headers, commit messages, commit diffs, and prev/next links are generated.

## Contents

- [Result brief](#result-brief)
- [Commit plan](#commitsjson)
- [Snapshots and comparison](#snapshots-and-comparison)
- [Overview](#overview-tab)
- [Commit tabs](#commit-tabs)
- [Diff embeds](#embedding-diffs)
- [Manual checks](#device-checklist-tab)
- [All files](#all-files-tab)
- [Validation](#validation)

## Result brief

Read [content.md](content.md) for the evidence contract and reviewer/merge table fields. This skill reports actual work. Use `plan-brief` to document proposed work. `--plan` here means only the optional commit split.

Required sections: `changes`, `requirements`, `review-focus`, `verification`, `merge-checklist`, plus overview and all-files tabs. Preserve required sections and explain inapplicable items. Structural validation cannot prove that a source supports a claim.

## commits.json

```json
{
  "prefix": "App/",
  "commits": [
    {
      "group": "A", "kind": "fix",
      "message": "full commit message, title on the first line",
      "files": ["Sources/A.swift", "App.xcodeproj/project.pbxproj"],
      "impact": "what users notice, or 없음",
      "verify": "what checked this commit; say what was not run",
      "review": "which cross-review findings this commit applies",
      "requires": "earlier commits it depends on beyond shared files",
      "revert": "what else must be reverted with it"
    }
  ]
}
```

- `prefix` is an optional repository-relative directory ending in `/`. The builder considers the prefixed and literal path; if both exist it fails as ambiguous. Prefer full repository paths with an empty prefix. Display paths are stripped unless `--strip-prefix` overrides this; collisions are rejected.
- `kind`: `fix`, `refactor`, `test`, `feat`, `chore`, `docs`. It sets the color.
- `risk` … `revert` are optional authored metadata; note/description values accept trusted HTML. `risk` is retained for compatibility only: quote an existing sourced assessment if needed; do not generate speculative ratings in result briefs. `risk.level`, when present, is `high`, `medium` or `low`. `kind` is an enum and other metadata fields are strings. Earlier commits touching the same files are listed automatically, but dependencies remain **unverified** unless inspected. Do not infer independent buildability from lack of file overlap.
- `message` and a nonempty `files` array are required per commit. Duplicate paths, unchanged file entries and incomplete final states are rejected. An empty commits array is valid only when there are no changes; omit the plan for an overall report.
- Paths must be normalized repository-relative paths, without `..`, absolute paths or `.git`. File items are either path strings or objects: `{"path":"bin/run", "mode":"100755"}` / `{"path":"old.txt", "delete":true}`. Allowed modes: `100644` regular, `100755` executable, `120000` symlink. Deletion cannot specify a mode.

## Snapshots and comparison

`snapshots/<n>/<repo path>` next to the plan contains the **cumulative file state after commit n**. The next commit compares against that state, not against the original base again. With no snapshot, the file uses its final working-tree state (or deletion if absent). When a file appears in multiple commits, supply each required intermediate snapshot; otherwise later entries may be empty and fail validation.

For example, base `A`, commit 1 `A+B`, commit 2 `A+B+C`: snapshot 1 must contain `A+B`, and commit 2 can use the working tree. Snapshot files carry their filesystem mode; set `mode` explicitly if a copy operation lost the executable bit. Symlink snapshots store the link target without reading it. A `120000` mode on a regular snapshot interprets its bytes as the target. Use `delete:true` for an intermediate deletion when the file exists again in the final tree. A file created and later deleted can be introduced using its first snapshot.

The builder compares the chosen base commit with the working tree, including staged paths and non-ignored untracked files; it does **not** reproduce a separate staged-only version. A staged addition subsequently removed from disk has no final addition. Renames are shown conservatively as deletion plus addition, so counts are path operations rather than Git rename counts. Include both paths in plans. Mode/type changes are retained even without text hunks. Binary and non-UTF-8 content show sizes rather than text; hashes contribute to the report identity. Empty files and missing final newlines are represented explicitly. All comment changes remain visible.

Merge conflicts, submodules/gitlinks, special files and paths traversing symlink directories are rejected explicitly. Git clean/smudge filters, LFS materialization and line-ending normalization are not applied: this is a comparison of base blob bytes with filesystem bytes, not a promise of the exact eventual staged patch. Review such repositories accordingly. There is no staged-only mode. A repository with no initial commit needs an explicit committed baseline first; the skill must not create that commit automatically.

The builder resolves `--base` once and records its full SHA separately from HEAD. It detects working-tree/HEAD changes during generation and fails; edits after generation require rebuilding. It reads repository file contents to compare states, so very large repositories may take time. Do not silently truncate a report or omit files to make it faster.

## Overview tab

`<div class="tab-page" data-tab="overview" data-label="개요">` holds `<header class="hero">` and then `<section id="…" data-toc="…">` blocks. Sections, in order:

| Section | Content | Main markup |
|---|---|---|
| hero | mode, source requirement/plan version, date/owner, conclusion; result change statistics only | `.eyebrow`, `dl.meta`, `.stats` |
| 변경 전 → 변경 후 (`changes`) | actual behavior/code change with diff evidence; distinguish code inspection from observed runtime behavior | `table.grid` |
| 요구별 결과 (`requirements`) | stable requirement/criterion IDs, original source, implementation state, verification state, evidence, remaining work | `table.grid` |
| 필수 리뷰 지점 (`review-focus`) | what/why/source, location, acceptance question, required vs proposed | `table.grid` |
| 검증·측정 (`verification`) | executed commands/scenarios, revision, environment, time, results, metrics with comparable measurement conditions | `.verify`, `table.grid` |
| 머지 조건 (`merge-checklist`) | sourced conditions, state, evidence/remaining action, human review record when applicable | `table.grid`, required `data-check-kind` / `data-verdict` / `data-basis` attributes |
| optional details | recorded decisions, actual cross-review, commit map, observed limitations, documented rollback, unperformed manual tests and follow-ups | `.card`, `#commit-map`, separate sections |

Use Korean headings in Korean reports: 변경 전 → 변경 후, 요구별 결과, 필수 리뷰 지점, 검증·측정 결과, 머지 체크리스트. Use the fields in content.md. Do not add synthetic risk scores or invented rationale to results.

Verdict pills: `pill ok` (동의), `pill warn` (부분 동의), `pill fix` (정정, 반박), `pill must` (P1). Severity pills: `pill must` for P1, `pill warn` for P2.

## Commit tabs

`<div class="tab-page" data-commit="N" data-summary="one line for the commit list">` with:

- `data-toc="무엇을 바꿨나"`: cause and change in one paragraph; an SVG figure if it shows the mechanism.
- `data-toc="diff 읽기"`: the hunks worth reading, each with one sentence.
- `data-toc="리뷰 포인트"`: `ul.points` with non-obvious things to check.

An empty commit tab still gets its generated header and diff.

## Embedding diffs

```html
<div class="diff-embed" data-file="Name.swift" data-match="regex" data-title="Label"></div>
<div class="diff-embed" data-file="Dir/Name.swift" data-hunks="1,3"></div>
```

`data-file` first matches the exact displayed path, then a unique path suffix separated by `/`. Zero or multiple matches are errors. Inside a commit tab it searches that commit's diff; elsewhere it searches the full diff. Use display paths after prefix stripping.

`data-match` is a JavaScript regular expression applied to added/deleted lines only. `data-hunks` selects positive, one-based hunk numbers, e.g. `1,3` (no spaces). Use only one selector. Invalid regexes, nonexistent/duplicate indices, and zero matched hunks produce visible validation failures. For binary, empty-file or mode-only changes, omit both selectors so metadata is displayed. These JavaScript checks run in the browser, not in the Python build step.

## Device checklist tab

```html
<div class="tab-page" data-tab="device" data-label="실기기 테스트">
  <section id="device-check" data-toc="체크리스트">
    <header><h2><span class="idx"></span>…</h2><div class="progress" data-progress-for="device-list"></div></header>
    <ul class="device" id="device-list">
      <li class="card"><label><input type="checkbox" data-check-id="list-refresh"><div>
        <div class="t">behavior to confirm <span class="pill must">필수</span><a class="pill fix" href="#c1">커밋 1</a></div>
        <dl class="steps"><dt>요구·필수 근거</dt><dd>관련 요구 ID와 필수 조건의 출처</dd><dt>환경·준비</dt><dd>장치·OS·빌드·초기 상태</dd><dt>조작</dt><dd><ol><li>따라 할 단계</li></ol></dd><dt>기대</dt><dd>관측할 통과 결과</dd><dt>실패</dt><dd>관측할 실패 조건</dd><dt>증거</dt><dd>로그·화면·수행자·시각</dd></dl>
      </div></label></li>
    </ul>
  </section>
</div>
```

This tab is optional; label it `수동 검증` for non-device work or omit it when inapplicable. Each item needs its requirement/source, environment and preparation, steps, pass/fail conditions, evidence to record and a globally unique stable `data-check-id`. Use `pill must` for required items and `pill neutral` for recommended ones. Browser-local check state is keyed by the report fingerprint and item ID; changed code, plan or body resets it. It is a convenience, not an execution log or shared sign-off. Record test environment, executor, time and result separately when claiming a completed check.

## All files tab

```html
<div class="tab-page" data-tab="all" data-label="전체 변경">
  <section id="all-files" data-toc="전체 diff"><div id="file-browser"></div></section>
</div>
```

Optional per-file notes: `<script type="application/json" id="file-notes">{"Name.swift": {"groups": "A,B", "note": "…"}}</script>`.

## Validation

Python generation checks required sections and verdict evidence attributes, then (for this result brief) Git state, plan shape, paths, final state, basic body structure, duplicate IDs, stable checkbox IDs, resource tags, and scaffold markers (`data-placeholder` or the explicit token `[REPLACE]`). It is not a full HTML sanitizer or a fact checker. Ordinary words such as TODO or model-id in actual requirements are allowed. Write completion evidence manually only after checking it.

Without `--plan`, remove `data-commit` tabs and links to `#cN`; include overview and all-files tabs. Commit pages may be generated automatically when the plan exists. Keep `data-tab="cN"` reserved for generated commit pages. An empty change is a valid no-change report, not evidence of work performed.

`--draft` permits report-content/plan-consistency issues with a visible warning; hard input/Git errors still fail. Exit 0 means a file was generated, not that a draft passed acceptance. On normal validation failure the previous output remains unchanged and must not be mistaken for a fresh report. Only use the output after a successful normal build and browser validation.

The optional `scripts/check_browser.mjs` checks every tab, JS errors, external HTTP requests, unresolved embeds and `window.reviewBriefValidation`. It exits nonzero for draft/error reports and may save overview/commit screenshots. Inspect screenshots visually and exercise the relevant controls; this is not project-level testing. Existing Playwright/Chromium is required only for this optional runner; a connected browser can perform the same checks. If neither is available, state the browser verification gap.

## Sources for the structure

- Google Engineering Practices, CL descriptions: what and why, and the shortcomings of the approach.
- Phabricator Differential test plans: repeatable verification, error paths, revert plan.
- Common PR templates (for example Circle's engineering practices): impact, dependencies, deployment, risk and rollback.
- BLUF: the conclusion and the decisions needed come first.

The final HTML must not contain duplicate IDs. Body IDs must not reuse template IDs such as `main`, `diff-data`, `toc-list`, `theme-btn` or `wrap-btn`. Use distinct section IDs. Input and output must refer to different files, including through symlinks or `..` path aliases.
