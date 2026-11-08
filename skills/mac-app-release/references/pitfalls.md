# Pitfalls

Each entry: symptom → cause → fix. All of them happened in real setups.

## Signing and notarization

- **`exportArchive Cloud signing permission error` / `No signing certificate "Developer ID Application" found` in CI**
  → The export relied on Xcode's cloud-managed Developer ID certificate. An API key cannot use it.
  → Sign with a p12 in a temporary keychain (`release-build.sh`). See signing.md.

- **Xcode "Manage Certificates" → + → Developer ID: "This operation can only be performed by the Account Holder"**
  → Xcode is signed in with an account that is not the team's Account Holder.
  → Create the certificate from a CSR on developer.apple.com as the Account Holder.

- **`security import` → "MAC verification failed during PKCS12 import (wrong password?)" although the password is right**
  → The p12 was made with OpenSSL 3/4, which uses AES/PBKDF2 algorithms.
  → Rebuild it with `/usr/bin/openssl` (LibreSSL).

- **A local signing test removes the login keychain from the search list**
  → `security list-keychains -d user -s <temp>` replaces the whole list.
  → `release-build.sh` saves the list and restores it on exit. Do the same in any ad-hoc test.

- **Notarization rejected because nested Sparkle code is not signed or has no timestamp**
  → The app was signed by hand with `--deep`, or the export step was skipped.
  → Archive, then `-exportArchive` with `method developer-id`. Export re-signs the XPC services, Autoupdate and Updater.app correctly. Never use `--deep`.

## Sparkle and feeds

- **Private repo: the appcast fails to parse even though the token works**
  → Sparkle overwrites `Accept` on the appcast request with `application/rss+xml,*/*`. The GitHub contents API ignores that header and returns JSON metadata.
  → Serve the feed from `raw.githubusercontent.com/<owner>/<repo>/appcast/appcast.xml`, which returns the file whatever `Accept` says. Send only `Authorization` in `httpHeaders`.

- **Private repo: the update download returns JSON or 404**
  → The enclosure URL must be the asset API URL (`api.github.com/repos/…/releases/assets/<id>`) with `Accept: application/octet-stream`. The browser download URL needs a session cookie, not a token.
  → `AppUpdater` sets the header in `willDownloadUpdate`. `release.yml` writes the asset API URL.
  → URLSession drops `Authorization` when it is redirected to GitHub's storage host. That is expected and fine.

- **Private feed: the release is published, but the push to the `appcast` branch failed** (network error or branch protection)
  → Re-running the workflow cannot fix it, because validation refuses a published tag.
  → Restore the feed from the copy attached to the release. Do not rebuild or replace assets:
    ```sh
    D=$(mktemp -d) && gh release download vX.Y.Z -R <owner>/<repo> -p appcast.xml -D "$D"
    git -C "$D" init -q -b appcast && git -C "$D" add appcast.xml && git -C "$D" commit -q -m "chore: restore appcast"
    git -C "$D" push --force https://github.com/<owner>/<repo>.git appcast
    ```
    If branch protection caused the failure, exclude `appcast` from the rule first.

- **Update never offered after switching versioning schemes**
  → Sparkle compares `CFBundleVersion`. Going from an older large build number to a smaller one hides every update.
  → The scheme `X*10000+Y*100+Z` is larger than typical small integer builds (1, 2, …) and dotted builds (`1.1.0`). Validation reads the latest release's `appcast.xml` and stops if the new build number is not above it. When that happens, raise the major version.

- **The first version installed by hand does not update, or the user expects the old app to update**
  → Copies from before Sparkle have no updater.
  → Install the first Sparkle release by hand on every Mac. With a private feed, enter the token there too.

## GitHub Actions

- **`Unrecognized named-value: 'runner'` at a job-level `env`**
  → The `runner` context is not available in `jobs.<id>.env`.
  → Compute paths inside a step and write them to `$GITHUB_ENV`.

- **A build setting from a git-ignored xcconfig is empty in CI**
  → The file is not in the checkout.
  → Store it in the `LOCAL_XCCONFIG` secret and set `LOCAL_XCCONFIG_PATH` to the exact path that the tracked xcconfig `#include?`s. A wrong path builds silently with empty values, so `release.yml` refuses a path whose folder does not exist and logs the path it wrote.

- **An older release overwrites the feed**
  → Two tag runs overlapped and the slower one published last.
  → `concurrency: { group: release, cancel-in-progress: false }`. Validation also rejects versions that are not newer than the latest published release.

- **Release notes contain only a "Full Changelog" link**
  → `--generate-notes` lists merged pull requests. Direct pushes to `main` produce none.
  → Create the draft with written notes before tagging (release mode, step 4). The workflow falls back to commit subjects.

- **A retagged release builds the old commit**
  → The remote tag still points at the old commit, or the run used a cached ref.
  → Delete the remote tag (`git push origin :refs/tags/vX.Y.Z`) and the local one, re-tag, and push. Do this only while no release is published for that tag. Otherwise use a new patch version.
