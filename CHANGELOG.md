# Changelog

`menvctl update` shows the sections between the installed release and the new
one. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and releases are `vX.Y.Z` tags.

## [Unreleased]

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
