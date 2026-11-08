---
name: mac-app-release
description: Set up and run Sparkle auto-updates and tag-triggered GitHub Actions releases (Developer ID signing, notarization, appcast, release notes) for a macOS app distributed outside the App Store, from public or private GitHub repositories. Use whenever the user wants in-app updates, "자동 업데이트", Sparkle, a release workflow, notarized builds from CI, or asks to cut, tag or publish a new version ("릴리스해줘", "새 버전 배포") of a Mac app — even if Sparkle or CI is not named.
---

# Mac App Release

Two modes. Pick by what the project already has:

- **Setup**: no `scripts/release-build.sh` or `.github/workflows/release.yml` yet, or the user asks to add updates or CI releases.
- **Release**: those files exist and the user wants a new version out.

Follow the user's git rules throughout: show what will be committed, pushed, tagged or registered as a secret, and wait for approval. Tags and secrets are outward-facing.

## How the pieces fit

```
git tag vX.Y.Z ─push─► release.yml ─► release-build.sh ─► notarized zip + EdDSA signature
                          │                                  │
                          ├─ validate (tag on main, newer, not already published)
                          └─ publish draft release → appcast → make public
App (Sparkle) ── reads appcast ── downloads zip ── checks signature against SUPublicEDKey ── installs
```

- **Version comes from the tag only.** `vX.Y.Z` sets `MARKETING_VERSION=X.Y.Z` and `CURRENT_PROJECT_VERSION=X*10000+Y*100+Z`. Sparkle compares the integer, so it always grows. Nobody edits versions in Xcode.
- **The same script builds in CI and locally.** `release-build.sh` does archive → Developer ID export → notarize → zip → Sparkle signature. Running it locally first (the rehearsal) catches signing and notarization failures before a tag is spent.
- **Nothing becomes public until verified.** CI checks the signature against the key inside the built app, uploads to a draft release, then publishes. A private feed's branch is pushed after publishing; if that push alone fails, follow the recovery entry in `references/pitfalls.md`.

## Setup mode

Work through these in order. Read each reference when you reach its step, not before.

1. **Collect facts** from the project: Xcode project path, scheme, app name, bundle id, team id, deployment target, whether the app is sandboxed, build settings that come from git-ignored files (for example an xcconfig with private values), and whether the GitHub repo is public or private.
2. **Choose the feed mode** and confirm with the user:
   - `public` repo: the feed is `https://github.com/<owner>/<repo>/releases/latest/download/appcast.xml`. No token.
   - `private` repo: the feed is the `appcast` branch read through `raw.githubusercontent.com`, and each Mac enters a read-only GitHub token once. Do not make a private repo's binaries public to avoid the token. The binary may contain values that must stay private.
3. **Ask for all user-only steps at once**, so the user is not interrupted later. These are listed in `references/signing.md` under "What only the user can do": web certificate upload, App Store Connect API key, and the GitHub token for private repos.
4. **Integrate Sparkle in the app**: `references/sparkle-app.md`. Build and confirm `SUFeedURL`, `SUPublicEDKey` and, if sandboxed, the entitlements are in the built app.
5. **Signing material and secrets**: `references/signing.md`. Create the CSR, build the p12 and test-import it, generate the Sparkle key, register the secrets, and back everything up.
6. **Copy the templates** into the project and fill in every `<PLACEHOLDER>`:
   - `templates/release.env` → `scripts/release.env`
   - `templates/release-build.sh` → `scripts/release-build.sh`
   - `templates/verify-update.swift` → `scripts/verify-update.swift`
   - `templates/release.yml` → `.github/workflows/release.yml`

   Then run `grep -rn '<[A-Z_]*>' scripts .github` and make sure it prints nothing.
7. **Rehearse locally** (see below) until it passes, including notarization.
8. **First release**: commit, merge to `main`, then run release mode. The installed copy usually predates Sparkle, so tell the user to install this first version by hand on each Mac (and, for private repos, enter the token in Settings). Every later version updates itself.

## Release mode

1. Check that the working tree is clean, the release commit is on `main` or will be merged there, and CI is green.
2. **Propose the version.** Find the last tag with `git describe --tags --abbrev=0`. Suggest a patch bump for fixes, minor for features, major for breaking changes, and confirm with the user.
3. **Draft release notes** from commits since the last tag: `git log --no-merges --format='- %s' <last-tag>..main`. Rewrite them for the user, not for developers: drop chore/refactor/test entries, group under short headings when there are many, and keep the user's language. Show the draft and let the user edit it.
4. **Create a draft release with the notes** before tagging. CI reuses a draft's notes; without a draft it falls back to raw commit subjects.
   `gh release create vX.Y.Z --draft --target main --title "<App> X.Y.Z" --notes-file notes.md`
5. **Rehearse** if signing material, Xcode or dependencies changed since the last release. Otherwise skip it.
6. **Tag and push** after approval: `git tag -a vX.Y.Z -m "<App> X.Y.Z" main && git push origin vX.Y.Z`.
7. **Watch CI** with `gh run watch <id> --exit-status`. On failure, read `gh run view <id> --log-failed`. Check `references/pitfalls.md` before guessing. A run that fails before its Publish step publishes nothing, so fix the cause and re-run it through `workflow_dispatch` with the same tag. If the fix needs a source change, use a new patch version. If only the private feed push failed, the release is already public: restore the feed by hand, as pitfalls.md describes, and do not re-run.
8. **Verify what users will get**: the feed shows the new version, and the asset downloads and passes `spctl --assess --type execute` after unzipping. For private feeds, add the token header. Then tell the user that "Check for Updates…" will find it.

## Rehearsal

Run from the repo root. It uses the same script as CI, with local files instead of secrets:

```sh
VERSION=0.0.1 OUT="$(mktemp -d)" \
P12_PATH=<path/to/DeveloperID.p12> P12_PASSWORD="$(cat <path/to/p12_password.txt>)" \
ASC_KEY_PATH=<path/to/AuthKey_XXXX.p8> ASC_KEY_ID=<key id> ASC_ISSUER_ID=<issuer id> \
SPARKLE_ACCOUNT=<keychain account used for generate_keys> \
bash scripts/release-build.sh
```

- Add `SKIP_NOTARIZE=1` for a fast signing-only pass. Run at least one full pass before the first release, because notarization is the slowest step to debug in CI.
- When it exits, the script restores the user's keychain search list and deletes its build folder. Only the zip and `build.env` stay in `OUT`, so no extra copy of the app is left behind to confuse the Dock.

## References

- `references/sparkle-app.md`: app integration (SPM, Info.plist, sandbox, the token-aware updater, settings UI)
- `references/signing.md`: Developer ID p12, App Store Connect API key, Sparkle key, secrets, backups
- `references/pitfalls.md`: symptom → cause → fix for every failure seen so far. Read it when anything fails.
