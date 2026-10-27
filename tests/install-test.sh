#!/bin/bash
# End-to-end check of install, update notice, and update with macOS's bash 3.2.
# Releases v1.0.0 and v1.1.0 from a copy of this repo into a throwaway origin,
# with a temporary HOME and stubbed claude and codex CLIs.
# Usage: tests/install-test.sh

set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

export HOME="$WORK_DIR/home"
export XDG_STATE_HOME="$HOME/.local/state"
export GIT_CONFIG_GLOBAL="$WORK_DIR/gitconfig"
git config --global user.name test
git config --global user.email test@example.com
git config --global init.defaultBranch main
mkdir -p "$HOME/.claude" "$WORK_DIR/bin"

cat >"$WORK_DIR/bin/codex" <<'EOF'
#!/bin/bash
# Stub: "mcp get" fails until "mcp add" records the server; plugins and
# marketplaces are line lists. Ids containing "broken" fail to install.
set -e
plugins="$HOME/.stub-codex-plugins" markets="$HOME/.stub-codex-markets"
touch "$plugins" "$markets"
drop() { grep -vxF "$2" "$1" >"$1.tmp" || true; mv "$1.tmp" "$1"; }
case "$1 $2 $3" in
  "login status ") [[ ! -f "$HOME/.stub-codex-logged-out" ]] ;;
  "plugin list --json") [[ ! -f "$HOME/.stub-codex-list-fails" ]] || { echo "network error" >&2; exit 1; }
    jq -R '{pluginId: .}' "$plugins" | jq -s '{installed: .}' ;;
  "mcp get "*) [[ -f "$HOME/.stub-codex-mcp" ]] ;;
  "mcp add "*) touch "$HOME/.stub-codex-mcp" ;;
  "plugin marketplace list") jq -R '{name: .}' "$markets" | jq -s '{marketplaces: .}' ;;
  "plugin marketplace add") printf '%s\n' "${4#*/}" >>"$markets" ;;
  "plugin marketplace remove") drop "$markets" "$4" ;;
  "plugin add "*) [[ "$3" != *broken* ]] || { echo "install failed: $3" >&2; exit 1; }; printf '%s\n' "$3" >>"$plugins" ;;
  "plugin remove "*) drop "$plugins" "$3" ;;
  *) echo "unexpected: $*" >&2; exit 1 ;;
esac
EOF

cat >"$WORK_DIR/bin/claude" <<'EOF'
#!/bin/bash
# Stub: keeps installed plugins and marketplaces as line lists.
set -e
plugins="$HOME/.stub-plugins" markets="$HOME/.stub-markets"
touch "$plugins" "$markets"
drop() { grep -vxF "$2" "$1" >"$1.tmp" || true; mv "$1.tmp" "$1"; }
case "$1 $2 $3" in
  "plugin list --json") jq -R '{id: .}' "$plugins" | jq -s . ;;
  "plugin marketplace list") jq -R '{name: .}' "$markets" | jq -s . ;;
  "plugin marketplace add") printf '%s\n' "${4#*/}" >>"$markets" ;;
  "plugin marketplace remove") drop "$markets" "$4" ;;
  "plugin install "*) printf '%s\n' "${@: -1}" >>"$plugins" ;;
  "plugin uninstall "*) drop "$plugins" "${@: -1}" ;;
  *) echo "unexpected: $*" >&2; exit 1 ;;
esac
EOF
chmod +x "$WORK_DIR/bin/codex" "$WORK_DIR/bin/claude"
export PATH="$WORK_DIR/bin:$PATH"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
# step <label>: a progress line, so a run of a minute or two never looks stuck.
STEP=0
STEPS="$(grep -c "^step " "${BASH_SOURCE[0]}")"
step() { STEP=$((STEP + 1)); printf "  [%2d/%d] %s\n" "$STEP" "$STEPS" "$1"; }
state() { jq -r "$1" "$XDG_STATE_HOME/menvctl/state.json"; }

# Release v1.0.0 from a copy of the working tree.
SRC="$WORK_DIR/src"
rsync -a --exclude .git "$REPO_ROOT/" "$SRC/"
# Test-only shared keys for the v1.1.0 removal cases: one left untouched locally,
# one whose parent changes type locally.
jq '. + {"menvctlDropped": "shared", "menvctlNested": {"a": 1}}' "$SRC/claude/settings.shared.json" \
  >"$SRC/s.tmp" && mv "$SRC/s.tmp" "$SRC/claude/settings.shared.json"
git -C "$SRC" init -q
git -C "$SRC" add -A
git -C "$SRC" commit -qm v1.0.0
git -C "$SRC" tag v1.0.0
git clone -q --bare "$SRC" "$WORK_DIR/origin.git"
git -C "$SRC" remote add origin "$WORK_DIR/origin.git"

REPO="$HOME/menvctl"
git clone -q "$WORK_DIR/origin.git" "$REPO"
INSTALL="$REPO/menvctl"
SETTINGS="$HOME/.claude/settings.json"

# Local settings and an existing skill directory that must survive.
printf '{"theme":"light","permissions":{"deny":["Bash(rm -rf /)"]}}\n' >"$SETTINGS"
mkdir -p "$HOME/.agents/skills/swiftui-pro"

# --- v1.0.0 install ---
step "Simulated v1.0.0: first install"
/bin/bash "$INSTALL" --yes >"$WORK_DIR/install.log"

for skill_dir in "$REPO"/skills/*/; do
  skill_name="$(basename "$skill_dir")"
  for skills_dir in "$HOME/.agents/skills" "$HOME/.claude/skills"; do
    [[ "$(readlink "$skills_dir/$skill_name")" == "$REPO/skills/$skill_name" && -d "$skills_dir/$skill_name" ]] ||
      fail "skill not linked to the repo: $skills_dir/$skill_name"
  done
done
[[ "$(readlink "$HOME/.codex/AGENTS.md")" == "$REPO/codex/AGENTS.md" ]] || fail "AGENTS.md"
[[ "$(readlink "$HOME/.claude/CLAUDE.md")" == "$REPO/claude/CLAUDE.md" ]] || fail "CLAUDE.md"
ls -d "$HOME"/.menvctl-backup/*/.agents/skills/swiftui-pro >/dev/null || fail "existing skill not backed up"
ls -d "$HOME"/.agents/skills/*backup* >/dev/null 2>&1 && fail "backup left inside skills dir"
[[ -f "$HOME/.stub-codex-mcp" ]] || fail "MCP not registered"
grep -qxF "ponytail@ponytail" "$HOME/.stub-plugins" || fail "ponytail not installed"
grep -qxF "ponytail" "$HOME/.stub-markets" || fail "ponytail marketplace not added"
for id in $(jq -r '.codex.plugins[].id' "$REPO/packages.json"); do
  grep -qxF "$id" "$HOME/.stub-codex-plugins" || fail "codex plugin not installed: $id"
done
[[ "$(jq -r .theme "$SETTINGS")" == light ]] || fail "local key dropped"
jq -e '.permissions.deny | index("Bash(rm -rf /)")' "$SETTINGS" >/dev/null || fail "local deny dropped"
jq -e '.permissions.deny | index("Bash(git push origin main)")' "$SETTINGS" >/dev/null || fail "shared deny missing"
jq -e '.env.GSTACK_CODEX_MODEL' "$SETTINGS" >/dev/null || fail "shared env missing"
grep -qF "menvctl\" check" "$HOME/.zshrc" || fail "update notice not added"
[[ "$(state .version)" == v1.0.0 ]] || fail "state version"
[[ "$(readlink "$HOME/.local/bin/menvctl")" == "$INSTALL" ]] || fail "menvctl not linked into ~/.local/bin"
# Later commands run through the PATH link, as a user would.
MENVCTL="$HOME/.local/bin/menvctl"

# Files ponytail creates at runtime, and the download claude plugin uninstall keeps.
mkdir -p "$HOME/.claude/ponytail-modes" "$HOME/.claude/plugins/cache/ponytail/ponytail/5.3.2"
touch "$HOME/.claude/ponytail-statusline.sh"

step "Second run changes nothing"
# A second run changes nothing: settings, links, plugins, and marketplaces stay identical.
snapshot() {
  cat "$SETTINGS" "$HOME/.stub-plugins" "$HOME/.stub-markets" "$HOME/.zshrc" \
    "$HOME/.stub-codex-plugins" "$HOME/.stub-codex-markets"
  for link in "$HOME"/.agents/skills/* "$HOME"/.claude/skills/* "$HOME/.codex/AGENTS.md" "$HOME/.claude/CLAUDE.md"; do
    printf '%s -> %s\n' "$link" "$(readlink "$link")"
  done
}
before="$(snapshot)"
/bin/bash "$MENVCTL" --yes >"$WORK_DIR/again.log"
[[ "$(snapshot)" == "$before" ]] || fail "second run changed state"
grep -qE '^  [+-] ' "$WORK_DIR/again.log" && fail "second run planned changes"

# Local edits made before the update: one dropped key changed, one parent changed type.
jq '.env.GSTACK_CODEX_MODEL = "local-model" | .menvctlNested = "mine"' "$SETTINGS" >"$SETTINGS.tmp" &&
  mv "$SETTINGS.tmp" "$SETTINGS"

# --- v1.1.0 ---
step "Simulated v1.1.0: plugins, skills, and settings change"
# Claude: ponytail -> superpowers. Codex: drop figma, add a plugin that fails to
# install, stop linking swiftui-pro (Claude keeps it). Both: delete liquid-glass.
# Add a skill no agent lists. Drop settings keys.
jq '.claude.plugins = [.claude.plugins[] | select(.id != "ponytail@ponytail")]
      + [{"id": "superpowers@claude-plugins-official", "repo": "anthropics/claude-plugins-official", "cleanup": []}]
  | .codex.plugins = [.codex.plugins[] | select(.id != "figma@openai-curated-remote")]
      + [{"id": "broken@openai-curated-remote", "cleanup": []}]
  | .codex.skills -= ["swiftui-pro", "liquid-glass"]
  | .claude.skills -= ["liquid-glass"]' \
  "$SRC/packages.json" >"$SRC/packages.json.tmp" && mv "$SRC/packages.json.tmp" "$SRC/packages.json"
jq 'del(.env, .menvctlDropped, .menvctlNested)' "$SRC/claude/settings.shared.json" >"$SRC/s.tmp" && mv "$SRC/s.tmp" "$SRC/claude/settings.shared.json"
rm -rf "$SRC/skills/liquid-glass"
mkdir -p "$SRC/skills/zz-unlisted"
printf -- '---\nname: zz-unlisted\n---\n' >"$SRC/skills/zz-unlisted/SKILL.md"
awk '{ print } /^## \[Unreleased\]/ { print "\n## [1.1.0] - 2026-11-01\n\n- Replaced ponytail with superpowers." }' \
  "$SRC/CHANGELOG.md" >"$SRC/c.tmp" && mv "$SRC/c.tmp" "$SRC/CHANGELOG.md"
git -C "$SRC" add -A
git -C "$SRC" commit -qm "Replace ponytail with superpowers"
git -C "$SRC" tag v1.1.0
git -C "$SRC" push -q origin HEAD:main --tags

# wait_for_cache <tag>: the background refresh has written this tag.
wait_for_cache() {
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    [[ "$(cat "$XDG_STATE_HOME/menvctl/latest-release" 2>/dev/null)" == "$1" ]] && return 0
    sleep 0.5
  done
  return 1
}

step "Update notice for the simulated v1.1.0"
# The notice refreshes in the background, then shows on a later shell start.
/bin/bash "$MENVCTL" check >/dev/null
wait_for_cache v1.1.0 || fail "release cache not refreshed"
/bin/bash "$MENVCTL" check | grep -qF "v1.1.0 is available" || fail "update notice not shown"

# --- update ---
step "Update to simulated v1.1.0: add, remove, clean up"
/bin/bash "$MENVCTL" update --yes >"$WORK_DIR/update.log" 2>&1

grep -qF "Replaced ponytail with superpowers." "$WORK_DIR/update.log" || fail "release notes not shown"
grep -qF "## [1.0.0]" "$WORK_DIR/update.log" && fail "installed release notes repeated"

grep -qxF "superpowers@claude-plugins-official" "$HOME/.stub-plugins" || fail "superpowers not installed"
grep -qxF "ponytail@ponytail" "$HOME/.stub-plugins" && fail "ponytail not uninstalled"
grep -qxF "ponytail" "$HOME/.stub-markets" && fail "ponytail marketplace left behind"
grep -qxF "claude-plugins-official" "$HOME/.stub-markets" || fail "official marketplace removed"
[[ -e "$HOME/.claude/ponytail-modes" || -e "$HOME/.claude/ponytail-statusline.sh" ]] && fail "ponytail files left behind"
[[ -e "$HOME/.claude/plugins/cache/ponytail" ]] && fail "ponytail plugin cache left behind"
ls "$HOME"/.menvctl-backup/*/.claude/ponytail-statusline.sh >/dev/null || fail "ponytail files not backed up"
[[ -e "$HOME/.agents/skills/liquid-glass" || -L "$HOME/.agents/skills/liquid-glass" ]] && fail "dropped codex skill left"
[[ -L "$HOME/.claude/skills/liquid-glass" ]] && fail "dropped claude skill left"
jq -e 'has("menvctlDropped")' "$SETTINGS" >/dev/null && fail "dropped settings key left"
[[ "$(jq -r .env.GSTACK_CODEX_MODEL "$SETTINGS")" == local-model ]] || fail "locally edited dropped key removed"
[[ "$(jq -r .menvctlNested "$SETTINGS")" == mine ]] || fail "locally retyped dropped key removed"
[[ "$(jq -r .theme "$SETTINGS")" == light ]] || fail "local key dropped on update"
jq -e '.permissions.deny | index("Bash(rm -rf /)")' "$SETTINGS" >/dev/null || fail "local deny dropped on update"
[[ "$(state .version)" == v1.1.0 ]] || fail "state version after update"
[[ "$(state '[.plugins.claude[].id] | index("ponytail@ponytail")')" == null ]] || fail "ponytail still in state"

# Per-agent skills: one source, linked only where packages.json lists it.
[[ -e "$HOME/.agents/skills/swiftui-pro" || -L "$HOME/.agents/skills/swiftui-pro" ]] && fail "codex-dropped skill left in Codex"
[[ "$(readlink "$HOME/.claude/skills/swiftui-pro")" == "$REPO/skills/swiftui-pro" ]] || fail "claude lost a skill only Codex dropped"
[[ -L "$HOME/.agents/skills/zz-unlisted" || -L "$HOME/.claude/skills/zz-unlisted" ]] && fail "unlisted skill linked"
grep -qF "skills/zz-unlisted is not listed for any agent" "$WORK_DIR/update.log" || fail "unlisted skill not warned"

# Codex plugins: removed when dropped; a failed install is reported, not fatal, and not recorded.
grep -qxF "figma@openai-curated-remote" "$HOME/.stub-codex-plugins" && fail "dropped codex plugin not removed"
grep -qxF "github@openai-curated-remote" "$HOME/.stub-codex-plugins" || fail "kept codex plugin removed"
grep -qF "Failed to install Codex plugin broken@openai-curated-remote" "$WORK_DIR/update.log" || fail "failed install not reported"
[[ "$(state '[.plugins.codex[].id] | (index("broken@openai-curated-remote") // index("figma@openai-curated-remote"))')" == null ]] ||
  fail "failed or dropped codex plugin recorded"
[[ -z "$(/bin/bash "$MENVCTL" check)" ]] || fail "notice shown after update"
/bin/bash "$MENVCTL" update --yes | grep -qF "Already up to date" || fail "second update not a no-op"

step "Local-only and prerelease tags are ignored"
# A tag that exists only in the local clone is not offered.
git -C "$REPO" tag v9.0.0
/bin/bash "$MENVCTL" update --yes | grep -qF "Already up to date" || fail "update took a local-only tag"
git -C "$REPO" tag -d v9.0.0 >/dev/null

# A prerelease tag is neither announced nor installed.
git -C "$SRC" tag v1.2.0-rc.1
git -C "$SRC" push -q origin --tags
rm -f "$XDG_STATE_HOME/menvctl/latest-release"
/bin/bash "$MENVCTL" check >/dev/null
wait_for_cache v1.1.0 || fail "prerelease treated as latest"
[[ -z "$(/bin/bash "$MENVCTL" check)" ]] || fail "notice shown for a prerelease"
/bin/bash "$MENVCTL" update --yes | grep -qF "Already up to date" || fail "update took a prerelease"

step "Tampered state cannot touch other files"
# A tampered state entry cannot delete or move files outside the plugin cache and agent dirs.
mkdir -p "$HOME/Documents"
touch "$HOME/Documents/keep"
STATE_FILE="$XDG_STATE_HOME/menvctl/state.json"
jq '.plugins.claude += [{"id": "Documents@../..", "cleanup": ["~/Documents"]},
                 {"id": "evil@claude-plugins-official", "cleanup": ["~/Documents", "~/.claude/../Documents"]}]' \
  "$STATE_FILE" >"$STATE_FILE.tmp" && mv "$STATE_FILE.tmp" "$STATE_FILE"
/bin/bash "$MENVCTL" --yes >"$WORK_DIR/tamper.log" 2>&1
[[ -f "$HOME/Documents/keep" ]] || fail "tampered state moved or deleted files"
grep -qF "Skipped invalid plugin id: Documents@../.." "$WORK_DIR/tamper.log" || fail "invalid plugin id not rejected"
grep -qF "Skipped cleanup path outside" "$WORK_DIR/tamper.log" || fail "outside cleanup path not rejected"
grep -qF 'Skipped cleanup path with ".."' "$WORK_DIR/tamper.log" || fail "traversing cleanup path not rejected"

# --- reconfigure: Claude only, first skill excluded, update notice off ---
step "Reconfigure: Claude only, a skill excluded, notice off"
first_skill="$(basename "$(ls -d "$REPO"/skills/*/ | sed -n 1p)")"
second_skill="$(basename "$(ls -d "$REPO"/skills/*/ | sed -n 2p)")"
printf 'n\ny\ny\ny\nn\n1\n\nn\ny\n' | /bin/bash "$MENVCTL" --reconfigure >"$WORK_DIR/reconfigure.log"
grep -qF 'menvctl" check' "$HOME/.zshrc" && fail "update notice left in .zshrc after turning it off"
ls "$HOME"/.menvctl-backup/*/.zshrc >/dev/null || fail ".zshrc not backed up before editing"
[[ -z "$(find "$HOME/.agents/skills" -type l)" ]] || fail "codex skills kept after disabling Codex"
[[ -L "$HOME/.claude/skills/$first_skill" ]] && fail "excluded skill still linked"
[[ "$(readlink "$HOME/.claude/skills/$second_skill")" == "$REPO/skills/$second_skill" ]] || fail "selected skill unlinked"
[[ "$(state '.choices.excluded_skills[0]')" == "$first_skill" ]] || fail "exclusion not saved"
/bin/bash "$MENVCTL" --yes >/dev/null
[[ -L "$HOME/.claude/skills/$first_skill" ]] && fail "exclusion not kept on later runs"
[[ "$(readlink "$HOME/.claude/skills/$second_skill")" == "$REPO/skills/$second_skill" &&
  -d "$HOME/.claude/skills/$second_skill" ]] || fail "selected skill lost on later runs"

# --- v1.2.0: every skill removed ---
step "Simulated v1.2.0: every skill removed; declined update rolls back"
rm -rf "$SRC/skills"
git -C "$SRC" add -A
git -C "$SRC" commit -qm "Remove all skills"
git -C "$SRC" tag v1.2.0
git -C "$SRC" push -q origin HEAD:main --tags
installed_head="$(git -C "$REPO" rev-parse HEAD)"

# With the notice turned off, check stays silent even when a newer release is cached.
printf 'v1.2.0\n' >"$XDG_STATE_HOME/menvctl/latest-release"
[[ -z "$(/bin/bash "$MENVCTL" check)" ]] || fail "notice shown while turned off"

# A declined update puts the previous checkout back, so linked files match the installed version.
printf 'n\n' | /bin/bash "$MENVCTL" update >"$WORK_DIR/declined.log"
[[ "$(git -C "$REPO" rev-parse HEAD)" == "$installed_head" ]] || fail "declined update kept the new checkout"
[[ "$(state .version)" == v1.1.0 ]] || fail "declined update changed the recorded version"

# A local branch named like the release does not shadow the tag.
git -C "$REPO" branch v1.2.0 "$installed_head"
/bin/bash "$MENVCTL" update --yes >"$WORK_DIR/update-1.2.log"
[[ "$(git -C "$REPO" rev-parse HEAD)" == "$(git -C "$SRC" rev-parse 'v1.2.0^{commit}')" ]] ||
  fail "update checked out a branch instead of the release tag"
[[ "$(state .version)" == v1.2.0 ]] || fail "state version after v1.2.0"
[[ -z "$(find "$HOME/.claude/skills" -type l)" ]] || fail "skill links left after every skill was removed"

# --- v1.3.0 tagged while this clone is on main: update applies in place ---
step "Simulated v1.3.0: update in place on main"
git -C "$REPO" checkout -q main
git -C "$REPO" pull -q --ff-only origin main
git -C "$SRC" commit -q --allow-empty -m "Release v1.3.0"
git -C "$SRC" tag v1.3.0
git -C "$SRC" push -q origin HEAD:main --tags
git -C "$REPO" pull -q --ff-only origin main
/bin/bash "$MENVCTL" update --yes >"$WORK_DIR/update-1.3.log"
[[ "$(git -C "$REPO" symbolic-ref -q --short HEAD)" == main ]] || fail "update left the branch it was already on"
[[ "$(state .version)" == v1.3.0 ]] || fail "state version after in-place update"

# --- v1.4.0 adds a Codex plugin while Codex is logged out ---
step "Simulated v1.4.0: Codex logged out, plugin list fails"
jq '.codex.plugins += [{"id": "late@openai-curated-remote", "cleanup": []}]' "$SRC/packages.json" \
  >"$SRC/packages.json.tmp" && mv "$SRC/packages.json.tmp" "$SRC/packages.json"
git -C "$SRC" commit -qam "Add a Codex plugin"
git -C "$SRC" tag v1.4.0
git -C "$SRC" push -q origin HEAD:main --tags
touch "$HOME/.stub-codex-logged-out"
# Turn Codex back on (the reconfigure above turned it off).
jq '.choices.codex = 1' "$STATE_FILE" >"$STATE_FILE.tmp" && mv "$STATE_FILE.tmp" "$STATE_FILE"
/bin/bash "$MENVCTL" update --yes >"$WORK_DIR/update-1.4.log" 2>&1
grep -qF "## [1." "$WORK_DIR/update-1.4.log" && fail "release notes older than the installed version shown"
grep -qF "Codex is not logged in" "$WORK_DIR/update-1.4.log" || fail "logged-out Codex not explained"
grep -qF "Failed to install Codex plugin late" "$WORK_DIR/update-1.4.log" && fail "logged-out install still attempted"
[[ "$(state .version)" == v1.4.0 ]] || fail "logged-out Codex blocked the rest of the update"
rm "$HOME/.stub-codex-logged-out"
/bin/bash "$MENVCTL" --yes >/dev/null 2>&1
grep -qxF "late@openai-curated-remote" "$HOME/.stub-codex-plugins" || fail "plugin not installed after login"

# A failed plugin list skips plugin changes and keeps the record, so later removals still work.
recorded_before="$(state '.plugins.codex')"
touch "$HOME/.stub-codex-list-fails"
/bin/bash "$MENVCTL" --yes >"$WORK_DIR/list-fails.log" 2>&1
grep -qF "Could not list Codex plugins" "$WORK_DIR/list-fails.log" || fail "failed plugin list not reported"
[[ "$(state '.plugins.codex')" == "$recorded_before" ]] || fail "failed plugin list erased the plugin record"
rm "$HOME/.stub-codex-list-fails"

# --- capture and release, on a separate authoring machine ---
step "capture: hand-installed skills and plugins"
export HOME="$WORK_DIR/author-home"
export XDG_STATE_HOME="$HOME/.local/state"
mkdir -p "$HOME/.claude"
AUTHOR="$HOME/menvctl"
AUTHOR_STATE="$XDG_STATE_HOME/menvctl/state.json"
git clone -q "$WORK_DIR/origin.git" "$AUTHOR"
/bin/bash "$AUTHOR/menvctl" --yes >/dev/null 2>&1

# Installed by hand: a skill of my own, a skill a tool owns, and a Claude plugin.
mkdir -p "$HOME/.claude/skills/my-skill" "$HOME/.claude/skills/tool-skill"
printf -- '---\nname: my-skill\n---\n' >"$HOME/.claude/skills/my-skill/SKILL.md"
printf -- '---\nname: tool-skill\n---\n' >"$HOME/.claude/skills/tool-skill/SKILL.md"
touch "$HOME/.claude/skills/tool-skill/.gstack-owned"
# Codex's own skill directory is not where menvctl links, so capture itself must move it.
mkdir -p "$HOME/.codex/skills/codex-skill"
printf -- '---\nname: codex-skill\n---\n' >"$HOME/.codex/skills/codex-skill/SKILL.md"
# A Codex skill linked from a project elsewhere: the link goes, the project stays.
mkdir -p "$WORK_DIR/projects/ext-skill"
printf -- '---\nname: ext-skill\n---\n' >"$WORK_DIR/projects/ext-skill/SKILL.md"
ln -s "$WORK_DIR/projects/ext-skill" "$HOME/.codex/skills/ext-skill"
claude plugin install handmade@claude-plugins-official
/bin/bash "$AUTHOR/menvctl" capture --yes >"$WORK_DIR/capture.log" 2>&1
jq -e '.claude.skills | index("my-skill")' "$AUTHOR/packages.json" >/dev/null || fail "hand-made skill not captured"
jq -e '.claude.plugins | any(.id == "handmade@claude-plugins-official")' "$AUTHOR/packages.json" >/dev/null ||
  fail "hand-installed plugin not captured"
jq -e '.claude.skills | index("tool-skill")' "$AUTHOR/packages.json" >/dev/null && fail "tool-owned skill captured"
[[ -f "$AUTHOR/skills/my-skill/SKILL.md" ]] || fail "captured skill not copied into the repo"
[[ "$(readlink "$HOME/.claude/skills/my-skill")" == "$AUTHOR/skills/my-skill" ]] || fail "captured skill not linked from the repo"
ls -d "$HOME"/.menvctl-backup/*/.claude/skills/my-skill >/dev/null || fail "captured skill original not backed up"
jq -e '.codex.skills | index("codex-skill")' "$AUTHOR/packages.json" >/dev/null || fail "Codex skill not captured for Codex"
[[ -e "$HOME/.codex/skills/codex-skill" ]] && fail "captured Codex skill left in place, so Codex would load it twice"
ls -d "$HOME"/.menvctl-backup/*/.codex/skills/codex-skill >/dev/null || fail "captured Codex skill not backed up"
[[ "$(readlink "$HOME/.agents/skills/codex-skill")" == "$AUTHOR/skills/codex-skill" ]] || fail "captured Codex skill not linked"
[[ -e "$HOME/.codex/skills/ext-skill" || -L "$HOME/.codex/skills/ext-skill" ]] && fail "captured link left in Codex's skill dir"
[[ -f "$WORK_DIR/projects/ext-skill/SKILL.md" ]] || fail "capture touched a project outside the agent dirs"
[[ "$(readlink "$HOME/.agents/skills/ext-skill")" == "$AUTHOR/skills/ext-skill" ]] || fail "captured linked skill not linked from the repo"

# n leaves the item untouched, and capture offers it again next time.
mkdir -p "$HOME/.claude/skills/other-skill"
printf -- '---\nname: other-skill\n---\n' >"$HOME/.claude/skills/other-skill/SKILL.md"
# Output is captured first: grep -q stopping early would SIGPIPE capture under pipefail.
output="$(printf 'n\n' | /bin/bash "$AUTHOR/menvctl" capture)"
grep -qF "No items added" <<<"$output" || fail "n did not skip"
jq -e '.claude.skills | index("other-skill")' "$AUTHOR/packages.json" >/dev/null && fail "skipped skill added"
[[ -f "$HOME/.claude/skills/other-skill/SKILL.md" ]] || fail "skipped skill moved"
output="$(printf 'n\n' | /bin/bash "$AUTHOR/menvctl" capture)"
grep -qF "Claude skill other-skill" <<<"$output" || fail "skipped skill not offered again"
rm -rf "$HOME/.claude/skills/other-skill"

# Two different skills with the same name: the second is refused and left in place.
mkdir -p "$HOME/.claude/skills/dup-skill" "$HOME/.codex/skills/dup-skill"
printf -- '---\nname: dup-skill\n---\nClaude version\n' >"$HOME/.claude/skills/dup-skill/SKILL.md"
printf -- '---\nname: dup-skill\n---\nCodex version\n' >"$HOME/.codex/skills/dup-skill/SKILL.md"
/bin/bash "$AUTHOR/menvctl" capture --yes >"$WORK_DIR/capture-dup.log" 2>&1
grep -qF "skills/dup-skill already holds a different skill" "$WORK_DIR/capture-dup.log" || fail "same-name skill conflict not reported"
jq -e '.codex.skills | index("dup-skill")' "$AUTHOR/packages.json" >/dev/null && fail "conflicting skill added for Codex"
grep -qF "Codex version" "$HOME/.codex/skills/dup-skill/SKILL.md" || fail "conflicting skill original moved or changed"
rm -rf "$HOME/.codex/skills/dup-skill"

step "release: refuses old versions, no changes, secrets, failing checks; writes missing notes"
# release refuses: an old version, no CHANGELOG section, a secret, failing tests.
remote_tag() { git -C "$AUTHOR" ls-remote --tags origin "refs/tags/$1"; }
# refused <message> <command...>: the command fails and prints the message (pipefail would
# otherwise report the expected failure instead of the grep).
refused() {
  local message="$1" output
  shift
  if output="$("$@" 2>&1)"; then return 1; fi
  grep -qF "$message" <<<"$output"
}
refused "is not newer than" /bin/bash "$AUTHOR/menvctl" release 1.4.0 || fail "released a version that is not newer"

# Nothing changed since the last release: refused, nothing written.
git clone -q "$WORK_DIR/origin.git" "$WORK_DIR/clean-clone"
refused "Nothing changed since v1.4.0" /bin/bash "$WORK_DIR/clean-clone/menvctl" release 1.4.1 ||
  fail "release with no changes not refused"
[[ -z "$(git -C "$WORK_DIR/clean-clone" status --porcelain)" ]] || fail "refused release changed files"

# No CHANGELOG section: release writes one from the changes since v1.4.0. Besides the
# captured items, drop a Codex plugin and edit a rule file.
jq '.codex.plugins = [.codex.plugins[] | select(.id != "late@openai-curated-remote")]' "$AUTHOR/packages.json" \
  >"$AUTHOR/p.tmp" && mv "$AUTHOR/p.tmp" "$AUTHOR/packages.json"
printf '\n- Review in small steps.\n' >>"$AUTHOR/codex/AGENTS.md"
MENVCTL_RELEASE_TEST=true /bin/bash "$AUTHOR/menvctl" release 1.5.0 </dev/null >"$WORK_DIR/notes.log" 2>&1
grep -qF "one was written from the changes since v1.4.0" "$WORK_DIR/notes.log" || fail "missing notes not generated"
notes="$(awk '/^## \[1\.5\.0\]/ { found = 1; next } found && /^## \[/ { exit } found' "$AUTHOR/CHANGELOG.md")"
for expected in '### Added' '- Claude skill `my-skill`' '- Codex skill `codex-skill`' \
  '- Claude plugin `handmade@claude-plugins-official`' '### Removed' '- Codex plugin `late@openai-curated-remote`' \
  '### Changed' '- `codex/AGENTS.md`'; do
  grep -qxF -- "$expected" <<<"$notes" || fail "generated notes lack: $expected"
done
grep -qE 'packages\.json|CHANGELOG\.md|skills/my-skill' <<<"$notes" && fail "generated notes list files already itemized"
[[ -z "$(remote_tag v1.5.0)" ]] || fail "generating notes published something"
# A second run uses the section already written instead of adding another.
MENVCTL_RELEASE_TEST=true /bin/bash "$AUTHOR/menvctl" release 1.5.0 </dev/null >/dev/null 2>&1
[[ "$(grep -c '^## \[1\.5\.0\]' "$AUTHOR/CHANGELOG.md")" == 1 ]] || fail "notes generated twice"
printf 'token=%s\n' "ghp_$(printf '%036d' 0)" >"$AUTHOR/leak.txt"
MENVCTL_RELEASE_TEST=true refused "Possible secrets" /bin/bash "$AUTHOR/menvctl" release 1.5.0 || fail "secret not caught"
rm "$AUTHOR/leak.txt"
MENVCTL_RELEASE_TEST=false refused "Sandbox check failed" /bin/bash "$AUTHOR/menvctl" release 1.5.0 || fail "failing tests not caught"

# A file the tests leave behind is scanned too.
printf '#!/bin/bash\nprintf "token=%%s\\n" "ghp_$(printf %%036d 0)" >"%s/generated.log"\n' "$AUTHOR" >"$WORK_DIR/leaky-test"
chmod +x "$WORK_DIR/leaky-test"
MENVCTL_RELEASE_TEST="$WORK_DIR/leaky-test" refused "Possible secrets" /bin/bash "$AUTHOR/menvctl" release 1.5.0 ||
  fail "secret written by the tests not caught"
rm "$AUTHOR/generated.log"

# A token committed and then deleted is still in the history the push would publish.
base="$(git -C "$AUTHOR" rev-parse HEAD)"
printf 'token=%s\n' "ghp_$(printf '%036d' 0)" >"$AUTHOR/leak.txt"
git -C "$AUTHOR" add leak.txt
git -C "$AUTHOR" commit -qm "Add leak" -- leak.txt
git -C "$AUTHOR" rm -q leak.txt
git -C "$AUTHOR" commit -qm "Remove leak" -- leak.txt
MENVCTL_RELEASE_TEST=true refused "Possible secrets" /bin/bash "$AUTHOR/menvctl" release 1.5.0 || fail "secret in commit history not caught"
# The same history already on a private remote is still unpublished on origin.
git clone -q --bare "$AUTHOR" "$WORK_DIR/private.git"
git -C "$AUTHOR" remote add private "$WORK_DIR/private.git"
git -C "$AUTHOR" fetch -q private
MENVCTL_RELEASE_TEST=true refused "Possible secrets" /bin/bash "$AUTHOR/menvctl" release 1.5.0 ||
  fail "secret on a private remote treated as published"
git -C "$AUTHOR" remote remove private
git -C "$AUTHOR" reset -q --soft "$base"

# A token at the top of a large file: the scan must not stop reading early and miss it.
{ printf 'token=%s\n' "ghp_$(printf '%036d' 0)"; head -c 4000000 /dev/zero | tr '\0' 'x'; } >"$AUTHOR/big.txt"
git -C "$AUTHOR" add big.txt
git -C "$AUTHOR" commit -qm "Add big" -- big.txt
git -C "$AUTHOR" rm -q big.txt
git -C "$AUTHOR" commit -qm "Remove big" -- big.txt
MENVCTL_RELEASE_TEST=true refused "Possible secrets" /bin/bash "$AUTHOR/menvctl" release 1.5.0 || fail "secret in a large diff not caught"
git -C "$AUTHOR" reset -q --soft "$base"

# A token inside a binary file, in the working tree and in history.
printf 'bin\0token=%s\n' "ghp_$(printf '%036d' 0)" >"$AUTHOR/blob.bin"
MENVCTL_RELEASE_TEST=true refused "Possible secrets" /bin/bash "$AUTHOR/menvctl" release 1.5.0 || fail "secret in a binary file not caught"
git -C "$AUTHOR" add blob.bin
git -C "$AUTHOR" commit -qm "Add blob" -- blob.bin
git -C "$AUTHOR" rm -q blob.bin
git -C "$AUTHOR" commit -qm "Remove blob" -- blob.bin
MENVCTL_RELEASE_TEST=true refused "Possible secrets" /bin/bash "$AUTHOR/menvctl" release 1.5.0 || fail "secret in binary history not caught"

# origin fetches from a private repo that has this history but pushes to the public one.
git clone -q --bare "$AUTHOR" "$WORK_DIR/private-fetch.git"
git -C "$AUTHOR" remote set-url origin "$WORK_DIR/private-fetch.git"
git -C "$AUTHOR" remote set-url --push origin "$WORK_DIR/origin.git"
git -C "$AUTHOR" fetch -q origin
MENVCTL_RELEASE_TEST=true refused "Possible secrets" /bin/bash "$AUTHOR/menvctl" release 1.5.0 ||
  fail "history on the fetch URL treated as published on the push URL"
# Several push URLs: release cannot tell which is public, so it refuses.
git -C "$AUTHOR" remote set-url --add --push origin "$WORK_DIR/private-fetch.git"
MENVCTL_RELEASE_TEST=true refused "several push URLs" /bin/bash "$AUTHOR/menvctl" release 1.5.0 ||
  fail "release with several push URLs not refused"
git -C "$AUTHOR" remote set-url origin "$WORK_DIR/origin.git"
git -C "$AUTHOR" config --unset-all remote.origin.pushurl
git -C "$AUTHOR" fetch -q --prune origin
git -C "$AUTHOR" reset -q --soft "$base"

# A file named like a grep option must not end the scan early.
printf 'x\n' >"$AUTHOR/--invalid-option"
printf 'token=%s\n' "ghp_$(printf '%036d' 0)" >"$AUTHOR/new-leak.txt"
MENVCTL_RELEASE_TEST=true refused "Possible secrets" /bin/bash "$AUTHOR/menvctl" release 1.5.0 ||
  fail "an option-like file name hid a secret"
rm -f -- "$AUTHOR/--invalid-option" "$AUTHOR/new-leak.txt"

# A textconv that masks tokens must not hide them in history.
printf '*.txt diff=redact\n' >>"$AUTHOR/.git/info/attributes"
git -C "$AUTHOR" config diff.redact.textconv "sed s/ghp_/MASKED/"
printf 'token=%s\n' "ghp_$(printf '%036d' 0)" >"$AUTHOR/masked.txt"
git -C "$AUTHOR" add masked.txt
git -C "$AUTHOR" commit -qm "Add masked" -- masked.txt
git -C "$AUTHOR" rm -q masked.txt
git -C "$AUTHOR" commit -qm "Remove masked" -- masked.txt
MENVCTL_RELEASE_TEST=true refused "Possible secrets" /bin/bash "$AUTHOR/menvctl" release 1.5.0 || fail "textconv hid a secret in history"
git -C "$AUTHOR" config --unset diff.redact.textconv
git -C "$AUTHOR" reset -q --soft "$base"

# The server rejects the branch but would accept the tag: nothing may be published.
printf '#!/bin/sh\ncase "$1" in refs/heads/*) exit 1 ;; esac\n' >"$WORK_DIR/origin.git/hooks/update"
chmod +x "$WORK_DIR/origin.git/hooks/update"
printf 'y\n' | MENVCTL_RELEASE_TEST=true /bin/bash "$AUTHOR/menvctl" release 1.5.0 >/dev/null 2>&1 && fail "release succeeded against a rejecting server"
[[ -z "$(remote_tag v1.5.0)" ]] || fail "tag published although the branch was rejected"
git -C "$AUTHOR" rev-parse -q --verify refs/tags/v1.5.0 >/dev/null && fail "local tag kept after a failed push"
rm "$WORK_DIR/origin.git/hooks/update"

# Only the release tag is published, not other annotated tags in the history,
# even with push.followTags turned on.
git -C "$AUTHOR" tag -a private-review -m "private note" HEAD
git -C "$AUTHOR" config push.followTags true
[[ -z "$(remote_tag v1.5.0)" ]] || fail "a refused release was published"

step "release publishes only with a yes, only its own refs"
# Declined, and no answer at all, publish nothing.
printf 'n\n' | MENVCTL_RELEASE_TEST=true /bin/bash "$AUTHOR/menvctl" release 1.5.0 >/dev/null
MENVCTL_RELEASE_TEST=true /bin/bash "$AUTHOR/menvctl" release 1.5.0 </dev/null >/dev/null
[[ -z "$(remote_tag v1.5.0)" ]] || fail "release published without a yes"

# Accepted: committed, tagged, pushed, and recorded here without leaving main.
MENVCTL_RELEASE_TEST=true /bin/bash "$AUTHOR/menvctl" release 1.5.0 --yes >"$WORK_DIR/release.log" 2>&1
[[ -n "$(remote_tag v1.5.0)" ]] || fail "release tag not pushed"
[[ -z "$(remote_tag private-review)" ]] || fail "release published an unrelated tag"
[[ "$(git -C "$AUTHOR" ls-remote origin refs/heads/main | cut -f1)" == "$(git -C "$AUTHOR" rev-parse HEAD)" ]] ||
  fail "release commit not pushed"
[[ "$(git -C "$AUTHOR" symbolic-ref -q --short HEAD)" == main ]] || fail "release left main"
[[ "$(git -C "$AUTHOR" rev-parse --abbrev-ref '@{upstream}')" == origin/main &&
  "$(git -C "$AUTHOR" rev-parse origin/main)" == "$(git -C "$AUTHOR" rev-parse HEAD)" ]] ||
  fail "release left the branch without an up-to-date upstream"
[[ -z "$(git -C "$AUTHOR" status --porcelain)" ]] || fail "release left uncommitted changes"
commit_message="$(git -C "$AUTHOR" log -1 --format=%B)"
grep -qF 'Claude plugin `handmade@claude-plugins-official`' <<<"$commit_message" || fail "release commit lacks its notes"
[[ "$(jq -r .version "$AUTHOR_STATE")" == v1.5.0 ]] || fail "release not recorded on the authoring machine"

printf 'PASS\n'
