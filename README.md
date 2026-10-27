# menvctl

[![test](https://github.com/MuchanKim/menvctl/actions/workflows/test.yml/badge.svg)](https://github.com/MuchanKim/menvctl/actions/workflows/test.yml)
[![release](https://img.shields.io/github/v/tag/MuchanKim/menvctl?sort=semver&label=release)](https://github.com/MuchanKim/menvctl/tags)
[![license](https://img.shields.io/github/license/MuchanKim/menvctl)](LICENSE)
![platform](https://img.shields.io/badge/platform-macOS-lightgrey?logo=apple)
![agents](https://img.shields.io/badge/agents-Claude%20Code%20%7C%20Codex-blueviolet)

My AI coding agent environment as code. One command sets up Codex and Claude
Code on a new Mac — global rules, skills, plugins, and shared settings — and
`menvctl update` keeps every machine on the latest release, including removing
what a release dropped.

> This is a personal setup. Fork it and replace the rules, skills, and plugins
> with your own; the installer does not depend on what they contain.

## Requirements

- macOS (the system bash 3.2 is enough)
- `git` and `jq` (both ship with macOS and the Command Line Tools)
- [Claude Code](https://claude.com/claude-code) and/or
  [Codex](https://github.com/openai/codex) — menvctl can install missing CLIs

## Quick start

```sh
git clone https://github.com/MuchanKim/menvctl.git ~/menvctl
~/menvctl/menvctl
```

The first run asks which agents to set up, whether to link the global rules,
apply shared settings, and show update notices, and which skills to link. It
then prints a plan and asks once before changing anything:

```text
Plan for v1.0.0:
  link   ~/.codex/AGENTS.md
  link   ~/.claude/CLAUDE.md
  + skill (Claude) swiftui-pro
  + plugin (Claude) swift-lsp@claude-plugins-official
  ~ merge ~/.claude/settings.json
  + update notice in ~/.zshrc
Apply this plan? [y/n]
```

Answer `[y/n]` questions with a single key; there is no need to press Enter.

menvctl links itself to `~/.local/bin/menvctl`, so later runs are just
`menvctl`.

## Commands

| Command | What it does |
|---|---|
| `menvctl` | Apply the checked-out version with this machine's saved choices |
| `menvctl --reconfigure` | Ask the setup questions again |
| `menvctl --yes` | Accept defaults and the plan without asking (skips CLI and gstack installs) |
| `menvctl update` | Check out the latest release, show its changelog, and apply it |
| `menvctl check` | Print a notice if a newer release exists (runs from `~/.zshrc`) |
| `menvctl capture` | Add skills and plugins you installed by hand to `packages.json` |
| `menvctl release X.Y.Z` | Check menvctl in a sandbox, then commit, tag, and publish this checkout, and apply it here |

## Common tasks

Changes that every Mac should get are made in this repo and published with
`menvctl release`; other Macs pick them up with `menvctl update`. Changes for
one Mac only use `menvctl --reconfigure` and are never published.

| I want to… | Do this |
|---|---|
| Set up a new Mac | `git clone https://github.com/MuchanKim/menvctl.git ~/menvctl && ~/menvctl/menvctl`. If Codex is not logged in yet, run `codex login`, then `menvctl` again for its plugins |
| Get the latest release | `menvctl update` (a new shell tells you when one is out) |
| Add a skill for every Mac | Put it in `skills/<name>/`, list it under `claude.skills` and/or `codex.skills` in `packages.json`, then release |
| Add a plugin for every Mac | Add `{ "id": "name@marketplace", "repo": "owner/repo", "cleanup": [] }` under `claude.plugins` or `codex.plugins`, then release |
| Keep something I installed by hand on every Mac | `menvctl capture`, then release |
| Remove a skill or plugin from every Mac | Delete it from `packages.json` (and `skills/`), then release; `update` uninstalls it everywhere |
| Change the global rules | Edit `claude/CLAUDE.md` or `codex/AGENTS.md`, then release. This Mac sees the edit at once: the rules are symlinks into the repo |
| Change shared Claude settings | Edit `claude/settings.shared.json`, then release. Keys you remove are removed from each Mac unless edited there |
| Skip a skill, an agent, or the update notice on this Mac only | `menvctl --reconfigure` |
| Publish my changes | `menvctl release X.Y.Z` (it writes the CHANGELOG section if you have not) |
| Undo something menvctl replaced or removed | Copy it back from `~/.menvctl-backup/<timestamp>/`, which mirrors paths under `~` |

Not managed, so set by hand on each Mac: model choice, credentials, Codex hooks,
and the `[desktop]` keys of `~/.codex/config.toml` (menvctl reports when they
differ from `codex/config.shared.toml`).

## What it manages

| What | Source in this repo | Installed to |
|---|---|---|
| Global rules | `codex/AGENTS.md`, `claude/CLAUDE.md` | `~/.codex/AGENTS.md`, `~/.claude/CLAUDE.md` (symlinks) |
| Skills | `skills/<name>/`, assigned per agent in `packages.json` | `~/.agents/skills` (Codex), `~/.claude/skills` (Claude Code) |
| Plugins | `packages.json` | `claude plugin install`, `codex plugin add` |
| Claude settings | `claude/settings.shared.json` | merged into `~/.claude/settings.json` |
| Codex settings | `codex/config.shared.toml` | MCP server via `codex mcp add`; `[desktop]` keys are compared, not written |

`packages.json` says which skills and plugins each agent gets:

```json
{
  "claude": { "skills": ["swiftui-pro"], "plugins": [{ "id": "swift-lsp@claude-plugins-official", "repo": "anthropics/claude-plugins-official", "cleanup": [] }] },
  "codex":  { "skills": ["swiftui-pro"], "plugins": [{ "id": "github@openai-curated-remote", "cleanup": [] }] }
}
```

- A skill has one copy in `skills/`. Listing it for both agents creates two
  symlinks to that copy, not two copies. A skill listed for neither agent is
  not linked, and the plan warns about it.
- `repo` is the GitHub repo of the plugin's marketplace, added when it is not
  configured yet. Plugins from marketplaces the Codex app provides need none.
- Only plugins in `packages.json` are managed. Plugins the Codex app bundles or
  installs by default, and anything you installed yourself, are left alone, as
  are plugins you turned off.
- A plugin that fails to install (for example before `codex login`) is reported
  and retried on the next run; the rest of the setup continues.

Everything else stays local: model choice, credentials, Codex hooks, and
machine-specific paths. `~/.codex/config.toml` is never edited, because the
Codex app rewrites it.

## Updates and removal

Releases are `vX.Y.Z` Git tags. Commits without a tag are never offered, and
prerelease tags such as `v1.2.0-rc.1` are ignored. With update notices on, a new
shell prints:

```text
menvctl v1.1.0 is available (installed v1.0.0). Run: menvctl update
```

The check runs at most once a day, in the background, so it never slows down a
shell start.

menvctl records what it installed in `~/.local/state/menvctl/state.json`, so an
update can remove what the new release no longer lists:

- **Skills:** a skill deleted from `skills/` or dropped from an agent's list is
  unlinked from that agent only. New skills are linked unless this machine
  excluded them.
- **Plugins:** uninstalled, their downloaded copy deleted, the files listed in
  their `cleanup` moved to the backup folder, and their marketplace removed
  when nothing else uses it.
- **Settings:** keys dropped from the shared settings are removed, unless you
  changed them locally. Local `permissions.deny` entries are always kept.

Anything menvctl replaces or removes goes to `~/.menvctl-backup/<timestamp>/`,
outside the agent directories so a backup is never loaded as a skill.

`update` refuses to run with uncommitted changes or unpushed commits. When the
checkout is already on the release commit, as on the machine that just tagged
it from `main`, `update` applies it in place and stays on the branch. Declining
the plan puts the previous checkout back.

## Making a release

1. Change `packages.json`, `skills/`, the rules, or the shared settings. If you
   installed something by hand, `menvctl capture` adds it for you:

   ```text
   Claude plugin warp@claude-code-warp
     installed with the plugin CLI
   Track it? [y/n] y

   Codex skill hatch-pet
     found at ~/.codex/skills/hatch-pet
   Track it? [y/n] n
   ```

   | Key | Effect | Next `capture` |
   |---|---|---|
   | `y` | Added to `packages.json` (a skill is copied into `skills/`) | Not shown: it is tracked now |
   | `n` | Left as it is; nothing changes | Shown again |

   `capture` explains these keys before the first question. Nothing is
   published until you run `menvctl release`.

   A captured skill's original moves to the backup folder, so the repo copy is
   the only one. Skills a tool installed (gstack), turned-off plugins, and
   plugins the Codex app bundles are never offered.
2. When you add a plugin that writes its own files, list them in its
   `cleanup`. Machines remove the paths recorded when they installed the plugin,
   since a later manifest no longer lists it. Cleanup paths must be under
   `~/.claude/` or `~/.codex/`; others are skipped.
3. Release notes: you may write a `## [X.Y.Z]` section in `CHANGELOG.md`
   yourself. If there is none, release writes it from what changed since the
   last published version:

   ```text
   ## [1.1.0] - 2026-11-02

   ### Added

   - Claude plugin `superpowers@claude-plugins-official`

   ### Removed

   - Claude plugin `ponytail@ponytail`

   ### Changed

   - `claude/CLAUDE.md`
   - Skill `swiftui-pro` updated
   ```

   Skills and plugins come from comparing `packages.json`, so they are exact.
   Other edits are listed by file name only, so add a sentence under a file if
   what changed matters. `menvctl update` shows this section on every Mac, and
   the release commit uses it.
4. Run `menvctl release X.Y.Z`. It works in six numbered steps:

   ```text
   [1/6] Checking the version and release notes
   [2/6] Checking menvctl in a throwaway sandbox (simulated installs and releases, about 1-2 minutes)
   [3/6] Scanning for secrets
   [4/6] Committing and tagging vX.Y.Z
   [5/6] Pushing main and vX.Y.Z to https://github.com/...
   [6/6] Applying vX.Y.Z on this Mac
   ```

   Step 2 runs `tests/install-test.sh`: it builds a temporary home folder and a
   temporary Git server, then installs, updates, and releases made-up versions
   there. Your Mac and GitHub are not touched, and the versions it prints are
   part of the simulation. Release stops before publishing if the version is not
   newer than the published one, nothing changed since it, a file or commit
   looks like it holds a token or private key, or the sandbox check fails.
   Between steps 3 and 4 it lists the files (`new`, `changed`, `deleted`) and
   release notes and asks `Publish vX.Y.Z to ...? [y/n]`. Only `y` (or `--yes`)
   publishes. Answering `n` publishes nothing and leaves generated notes in
   `CHANGELOG.md` to edit before you run release again.

CI runs the same sandbox check on every push, pull request, and release tag.

## My workflow

The rules and settings in this repo set up a split between the two agents:

| Stage | Agent | How |
|---|---|---|
| Planning | Claude Code | [gstack](https://github.com/garrytan/gstack) skills such as `/office-hours` and `/plan-eng-review` |
| Implementation | Claude Code | |
| Review | Codex | gstack `/codex review`, pinned to `gpt-6-astra` by `GSTACK_CODEX_MODEL` |

menvctl offers to install gstack and warns in the plan when it is missing.

## Skills

| Skill | Purpose | Claude Code | Codex |
|---|---|---|---|
| `swift-conventions` | Personal Swift and SwiftUI conventions | ✓ | ✓ |
| `swiftui-pro`, `swift-concurrency-pro`, `swift-testing-pro` | Customized versions of Paul Hudson's agent skills | ✓ | ✓ |
| `liquid-glass` | Apple Liquid Glass controls and navigation | ✓ | ✓ |

Claude Code implements and Codex reviews against the same rules, so these go to
both. Planning, implementation, and review skills are not tracked here, because
gstack covers those stages.

## Tests

```sh
tests/install-test.sh
```

Publishes v1.0.0, v1.1.0, and a prerelease tag from a copy of the repo into a
temporary origin, then installs, updates, and reconfigures with macOS's bash
3.2, a temporary `HOME`, and stubbed `claude` and `codex` CLIs.

## License

[MIT](LICENSE). The `swiftui-pro`, `swift-concurrency-pro`, and
`swift-testing-pro` skills are adapted from Paul Hudson's
[SwiftUI](https://github.com/twostraws/SwiftUI-Agent-Skill),
[Swift Concurrency](https://github.com/twostraws/Swift-Concurrency-Agent-Skill),
and [Swift Testing](https://github.com/twostraws/Swift-Testing-Agent-Skill)
agent skills, MIT-licensed; see the `LICENSE` file in each skill.
