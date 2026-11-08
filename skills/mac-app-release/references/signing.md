# Signing material and secrets

CI signs with a **Developer ID Application certificate exported as a p12**. Do not plan around Xcode's cloud-managed Developer ID certificate. It works on the developer's Mac, but an App Store Connect API key cannot use it in CI (`Cloud signing permission error`), and its private key cannot be exported.

## What only the user can do

Ask for all three up front, in one message:

1. **Upload the CSR** you generated (step 1 below) at <https://developer.apple.com/account/resources/certificates/add>: choose Developer ID Application, upload the file, then download the `.cer`. This must be done by the team's **Account Holder**. Xcode's Manage Certificates shows "only the Account Holder" when another account is signed in, but the web page usually works for the owner.
2. **Create an App Store Connect team API key**: Users and Access → Integrations → Team Keys, role Admin. Download the `.p8`, which can be downloaded only once. The user needs to give you the Key ID, the Issuer ID and the file path. A separate key per app means revoking one does not stop another app's releases.
3. **Private feed only: create a fine-grained GitHub token** at <https://github.com/settings/personal-access-tokens/new>. Select only this repository and give it Contents: Read-only (Metadata is added automatically). It goes into the app's Settings on each Mac, not into CI. Never ask for the token in chat.

## 1. Developer ID certificate → p12

First check whether a usable identity already exists. The private key has to be on this Mac:

```sh
security find-identity -v -p codesigning | grep "Developer ID Application"
```

If one exists, export it with its private key from Keychain Access to a `.p12`. Otherwise create a new one. Put everything in a folder the user backs up (an iCloud folder is fine), with `umask 077`:

```sh
umask 077
openssl genrsa -out developer_id.key 2048
openssl req -new -key developer_id.key -out DeveloperID.certSigningRequest \
  -subj "/emailAddress=<user email>/CN=<user name>/C=<country>"
open -R DeveloperID.certSigningRequest      # the user uploads this file on the web page
```

After the user saves the `.cer` next to it, run:

```sh
openssl x509 -inform der -in developerID_application.cer -out developer_id.pem
# the certificate must match the key
[ "$(openssl x509 -in developer_id.pem -noout -modulus)" = "$(openssl rsa -in developer_id.key -noout -modulus)" ]
openssl rand -hex 24 > p12_password.txt
/usr/bin/openssl pkcs12 -export -inkey developer_id.key -in developer_id.pem \
  -name "Developer ID Application" -out DeveloperID.p12 -passout file:p12_password.txt
```

Use **`/usr/bin/openssl` (LibreSSL)** for the p12. A Homebrew OpenSSL 3/4 p12 uses algorithms that `security import` rejects with "MAC verification failed (wrong password?)".

Test-import it the way CI will. This also proves the password is right:

```sh
K="$(mktemp -d)/t.keychain-db"; P=$(openssl rand -hex 16)
security create-keychain -p "$P" "$K" && security unlock-keychain -p "$P" "$K"
security import DeveloperID.p12 -k "$K" -P "$(cat p12_password.txt)" -T /usr/bin/codesign
security find-identity -v -p codesigning "$K"     # expect one "Developer ID Application: … (<TEAM_ID>)"
security delete-keychain "$K"
```

The certificate does not change the app's designated requirement (team id + bundle id). Existing installs therefore keep their sandbox container, Keychain items and bookmarks after updating to a build signed with the new certificate.

## 2. Sparkle EdDSA key

Use the tools from the resolved package: `<DerivedData>/SourcePackages/artifacts/sparkle/Sparkle/bin/`. You can also download them from the Sparkle release that matches `Package.resolved`. Use one keychain account per app, for example the bundle id:

```sh
generate_keys --account <bundle id>        # prints the public key for SUPublicEDKey
generate_keys --account <bundle id> -p     # prints it again later
generate_keys --account <bundle id> -x <backup folder>/sparkle_private_key.txt   # backup, umask 077
```

Back the key up before the first release. When an app already has a key, never generate a new one: move the existing one instead. If the key is lost, Sparkle can still accept an update signed with a new key, as long as the old and new builds are signed with the same Developer ID. This only works for zip and other archives, not for a DMG checked with `SUVerifyUpdateBeforeExtraction`. Follow [Sparkle's key rotation guide](https://sparkle-project.org/documentation/#rotating-signing-keys) before telling the user to reinstall.

## 3. Secrets

| Secret | Value |
|---|---|
| `DEVELOPER_ID_P12_BASE64` | `base64 < DeveloperID.p12` |
| `DEVELOPER_ID_P12_PASSWORD` | the contents of `p12_password.txt` |
| `ASC_KEY_P8` | the contents of the `.p8` file |
| `ASC_KEY_ID`, `ASC_ISSUER_ID` | from App Store Connect |
| `SPARKLE_PRIVATE_KEY` | the `generate_keys -x` export |
| `LOCAL_XCCONFIG` | only if `LOCAL_XCCONFIG_PATH` is set in `release.env`: the contents of that git-ignored file |

Register the secrets from files, so values never appear in the terminal or the chat:

```sh
R=<owner>/<repo>
base64 < DeveloperID.p12 | gh secret set DEVELOPER_ID_P12_BASE64 -R $R
gh secret set DEVELOPER_ID_P12_PASSWORD -R $R < p12_password.txt
gh secret set ASC_KEY_P8 -R $R < AuthKey_XXXX.p8
gh secret set ASC_KEY_ID -R $R --body <key id>
gh secret set ASC_ISSUER_ID -R $R --body <issuer id>
K=$(mktemp -d) && (umask 077; generate_keys --account <bundle id> -x "$K/sk") && gh secret set SPARKLE_PRIVATE_KEY -R $R < "$K/sk"; S=$?; rm -rf "$K"; [ $S -eq 0 ]
gh secret set LOCAL_XCCONFIG -R $R < <path to the git-ignored xcconfig>   # if used
gh secret list -R $R
```

GitHub never shows a secret again after it is set. The only copies are the backup folder and, for the Sparkle key, the login keychain.
