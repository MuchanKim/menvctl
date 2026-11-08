# Changelog

`menvctl update` shows the sections between the installed release and the new
one. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and releases are `vX.Y.Z` tags.

## [Unreleased]

## [1.5.0] - 2026-11-09

### Added

- Skill `mac-app-release` (Claude and Codex): sets up Sparkle auto-updates and
  tag-triggered GitHub Actions releases for macOS apps outside the App Store,
  and runs releases. Developer ID signing from a p12, notarization, public or
  private (token) feeds, version taken from the tag, a local rehearsal that
  runs the same build script as CI, and release notes from a reviewed draft.

## [1.4.1] - 2026-11-07

### Changed

- Claude Code: no AI attribution in commits and PRs. Shared settings set
  `attribution` to empty, and CLAUDE.md states the rule Codex already had.

## [1.4.0] - 2026-11-07

### Changed

- `result-brief`: no longer builds an HTML file. The brief is a Markdown reply
  in four sections: intent vs. applied changes (including unplanned changes),
  before/after SVG diagrams embedded as images and checked by the reviewer in
  the same review call, verification and review results, and a user checklist.
  The builder, template, browser checker and tests are removed.
- Workflow: the cross-review runs right after implementation without asking;
  its findings wait in the brief for the developer instead of being applied.
  The model that implements a change never reviews it.
- PR bodies follow the repository template, filled from the result brief,
  with diagrams in Mermaid.
- pstack is the implementation skill set; CLAUDE.md suggests installing it
  when missing.

### Removed

- Skill `plan-brief`. `menvctl update` unlinks it.
- gstack: the install offer, the missing-gstack warning and the
  `GSTACK_CODEX_MODEL` setting. Review runs through T3 Code `delegate_task` or
  `codex exec`.

## [1.3.2] - 2026-11-02

### Changed

- `result-brief`: the test verdict card no longer shows a 하한 (test count
  floor) cell; the verify record has no floor value anymore. The card lays
  out its six fields in three columns.

## [1.3.1] - 2026-11-02

### Changed

- `result-brief`: every commit in the plan needs a body tab with a What table
  broken down by file › type › function, and at least one diagram (sequence,
  object/type or state) or `data-diagram-na` with a reason. The build fails
  without them.
- `result-brief`: new required overview section `behavior` (동작과 사용법):
  flow diagram, outcomes, usage and real output.
- `result-brief`, `plan-brief`: diagram styles in the template (`svg.dg`,
  box states new/changed/removed/test/warn, legend) that follow light and
  dark themes.
- `result-brief`: issue numbers, commit SHAs and pushed branches written as
  text become GitHub links when `origin` is on GitHub.

### Fixed

- Release sandbox check: it no longer fails once a real release is newer than
  v1.3.0. The sandbox drops the real release sections from its CHANGELOG copy
  before simulating its own versions.

## [1.3.0] - 2026-11-02

### Changed

- `result-brief`: a report with changes now requires a commit plan (`--plan`);
  each commit gets its own tab with message, diff and notes.
- `result-brief`: new `--verify` and `--review` inputs. The builder inserts an
  automatic facts section after the hero: test verdict, folder diff as a file
  tree with colored add/delete counts, test and runtime config changes, test
  expectation changes, and the verbatim review. A record for a different
  working tree fails the build.
- `result-brief`: required sections add metrics, impact and device test items;
  the verification table adds a verifier column.
- `result-brief`, `plan-brief`: readability. Verdict card, body font for
  metadata and review text, table headers kept as written, long code wraps
  inside table cells, numeric columns right-aligned.

## [1.2.0] - 2026-11-01

### Added

- Claude plugin `pstack@cursor-plugins` (cursor/plugins): engineering
  playbooks and principle skills, entered through `/pstack:poteto-mode`.

### Changed

- `claude/CLAUDE.md`: adds the `/pstack:poteto-mode` row and a role split:
  gstack for planning and product direction, pstack for implementation,
  maintenance, and refactoring, `/codex review` for review.
- `.gitignore`: ignores `__pycache__/` so script caches are not published.

## [1.1.0] - 2026-10-31

### Added

- Skill `plan-brief` (Claude, Codex): builds a self-contained HTML planning
  brief with requirements, scope, scenarios, acceptance criteria, and open
  decisions, for review before implementation.
- Skill `result-brief` (Claude, Codex): builds a self-contained HTML result
  brief mapping requirements to actual changes and verification evidence,
  reviewer focus, and merge conditions.

### Changed

- `README.md`: lists both skills and the `result-brief` test command.

## [1.0.1] - 2026-10-27

### Added

- `menvctl release` creates the version's GitHub release page, with its
  CHANGELOG section as the text, so the notes show under the repo's Releases.
  It needs the `gh` CLI logged in; without it, release prints the command to
  run by hand.
- `menvctl release` without a version releases the next minor version
  (v1.0.0 -> v1.1.0). `menvctl release X.Y.Z` still picks one.

### Changed

- `[y/n]` questions take only `y` or `n`. Other keys, such as a typo, Enter,
  or an arrow key, are ignored instead of answering no, so a slip no longer
  cancels a release. On a Korean keyboard layout `ㅛ` and `ㅜ` work as `y` and
  `n`.

## [1.0.0] - 2026-10-27

### Added

- `menvctl` installer for Codex and Claude Code: global rules, per-agent skills
  and plugins, and shared settings, with a change plan confirmed before applying.
- `menvctl update` applies the latest release tag and removes the skills,
  plugins, and plugin files that the release dropped.
- `menvctl check` shows a notice in new shells when a release is published.
- `menvctl capture` adds skills and plugins installed by hand to `packages.json`.
- `menvctl release` checks menvctl in a sandbox, then commits, tags, and
  publishes a release, and records it on the machine that made it.
- Claude plugins: `ponytail`, `swift-lsp`.
- Codex plugins: `github`, `gmail`, `google-calendar`, `figma`,
  `product-design`, `build-ios-apps`.
- Skills for both agents: `swift-conventions`, `swiftui-pro`,
  `swift-concurrency-pro`, `swift-testing-pro`, `liquid-glass`.
