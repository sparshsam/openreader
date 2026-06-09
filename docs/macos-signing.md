# macOS Code Signing & Notarization — Roadmap

> **Status:** Not implemented. This document outlines the path to signed
> and notarized macOS releases.

## Why Signing & Notarization Matter

Apple's Gatekeeper on macOS 14+ (Sonoma) treats unsigned apps differently:

| Scenario | User Experience |
|----------|----------------|
| **Signed + notarized** | User downloads, opens, runs. No warnings. |
| **Signed only** | Gatekeeper verifies the developer identity but still warns that the app has not been checked by Apple. |
| **Unsigned** (current) | Gatekeeper blocks the app. User must go to **System Settings → Privacy & Security** and click **Open Anyway** for every new version. Quarantine attribute (`com.apple.quarantine`) is set by default. |

## Prerequisites

To sign and notarize macOS builds, you need:

1. **Apple Developer account** — Individual ($99/year) or Organization.
2. **Developer ID Application certificate** — Issued by Apple for distributing outside the Mac App Store.
3. **Developer ID Installer certificate** — For signing installer packages (optional if using DMG only).
4. **App-specific password** — For `notarytool` authentication (or Xcode-alt token).

## Implementation Steps

### Phase 1: Code Signing the App Bundle

```bash
# Sign the app bundle with Developer ID
codesign --force --options runtime \
  --sign "Developer ID Application: Your Name (TEAMID)" \
  --entitlements scripts/entitlements.plist \
  "dist/PDFReader by Sparsh.app"

# Verify signing
codesign -dv --verbose=4 "dist/PDFReader by Sparsh.app"
```

Required entitlements (`scripts/entitlements.plist`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>com.apple.security.cs.disable-library-validation</key>
  <true/>
  <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
  <true/>
  <key>com.apple.security.cs.allow-dyld-environment-variables</key>
  <true/>
</dict>
</plist>
```

> **Why these entitlements?** PyInstaller bundles a Python runtime that
> loads dynamic libraries and uses JIT-like patterns. Without
> `disable-library-validation`, the hardened runtime would block loading
> of Python extension modules (.so files) bundled inside the app.

### Phase 2: Notarization

```bash
# Compress for notarization
ditto -c -k --sequesterRsrc --keepParent \
  "dist/PDFReader by Sparsh.app" \
  "dist/PDFReader-by-Sparsh-for-notarization.zip"

# Submit to Apple
xcrun notarytool submit \
  "dist/PDFReader-by-Sparsh-for-notarization.zip" \
  --apple-id "your@email.com" \
  --team-id "TEAMID" \
  --password "@keychain:AC_PASSWORD" \
  --wait

# Staple the ticket to the app bundle
xcrun stapler staple "dist/PDFReader by Sparsh.app"

# Verify staple
stapler validate "dist/PDFReader by Sparsh.app"
```

### Phase 3: Sign the DMG

If distributing via DMG, sign the DMG itself so Gatekeeper doesn't warn
when the user mounts it:

```bash
codesign --force --sign "Developer ID Application: Your Name (TEAMID)" \
  "dist/PDFReader-by-Sparsh-0.x.x-Apple-Silicon.dmg"
```

### Phase 4: CI Integration

The signing and notarization steps require:

- **macOS runner** (macos-15 or macos-15-intel) — already available.
- **Apple Developer credentials stored as GitHub Secrets:**
  - `MACOS_CERTIFICATE` — Base64-encoded Developer ID certificate + private key (`.p12` file).
  - `MACOS_CERTIFICATE_PWD` — Password for the `.p12` file.
  - `MACOS_NOTARY_APPLE_ID` — Apple ID email.
  - `MACOS_NOTARY_TEAM_ID` — Apple Developer Team ID.
  - `MACOS_NOTARY_PASSWORD` — App-specific password for notarytool.
- **Keychain setup step** in CI to import the certificate and unlock the keychain.

Example CI snippet for importing the certificate:

```yaml
- name: Import Apple Developer certificate
  env:
    MACOS_CERTIFICATE: ${{ secrets.MACOS_CERTIFICATE }}
    MACOS_CERTIFICATE_PWD: ${{ secrets.MACOS_CERTIFICATE_PWD }}
  run: |
    echo "$MACOS_CERTIFICATE" | base64 --decode > /tmp/certificate.p12
    security create-keychain -p temp temp.keychain
    security default-keychain -s temp.keychain
    security unlock-keychain -p temp temp.keychain
    security import /tmp/certificate.p12 -k temp.keychain \
      -P "$MACOS_CERTIFICATE_PWD" -T /usr/bin/codesign
    security set-key-partition-list \
      -S apple-tool:,apple:,codesign: -s -k temp temp.keychain
```

## Current Status

| Step | Status | Notes |
|------|--------|-------|
| Developer ID certificate | ❌ Not purchased | Requires Apple Developer enrollment ($99/yr). |
| Entitlements | ⚠️ Draft | Listed above, not tested. |
| `codesign` script | ❌ Not implemented | Will need `scripts/sign_macos.sh`. |
| Notarization script | ❌ Not implemented | Will need `scripts/notarize_macos.sh`. |
| CI integration | ❌ Not implemented | Secrets not configured. |
| Stapling | ❌ Not implemented | Requires successful notarization first. |
| DMG signing | ❌ Not implemented | Requires signing first. |

## Cost

- **Apple Developer Program:** $99/year (individual).
- **Developer ID certificate:** Included with the Developer Program.
- **Notarization:** Free with the Developer Program.
- **Total upfront cost:** $99 first year, then $99/year renewal.

## Alternative: Notarize Without Signing

As of macOS 14, Apple requires both signing **and** notarization for
Gatekeeper to treat the app as trusted. Signing alone is not sufficient,
and notarization without signing is not possible.

## Reference

- [Apple: Distributing apps outside the Mac App Store](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
- [Apple: Customizing the hardened runtime](https://developer.apple.com/documentation/security/hardened_runtime)
- [PyInstaller: Code signing macOS builds](https://pyinstaller.org/en/stable/usage.html#macos-code-signing)
