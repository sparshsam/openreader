# Winget Support Preparation

**Status:** 🔜 Not yet published

## Package Identity

| Field | Value |
|---|---|
| Package identifier | `SparshSam.OpenReader` |
| Package family name | `SparshSam.OpenReader_yh0byntbzd2qw` |
| Publisher | `Sparsh Sam` |
| License | AGPL-3.0 |
| Installer type | MSIX |

## Requirements

Before submitting to [winget-pkgs](https://github.com/microsoft/winget-pkgs):

- [x] GitHub Releases must have predictable asset naming (done — `OpenReader.msix`)
- [x] Release workflow produces consistent artifacts (done)
- [ ] **Microsoft Store certification is approved** (blocking — wait for Store approval)
- [ ] Stable release validation passes a Store-signed installation cycle
- [ ] Winget manifest is prepared (see below)
- [ ] Automated PR via winget release workflow is considered

## Manifest Structure

```text
manifests/
  s/
    SparshSam/
      OpenReader/
        1.2.2.0.yaml
```

### Manifest Template (prepare, do not submit)

```yaml
PackageIdentifier: SparshSam.OpenReader
PackageVersion: 1.2.2.0
PackageLocale: en-US
Publisher: Sparsh Sam
PublisherUrl: https://github.com/sparshsam
PublisherSupportUrl: https://github.com/sparshsam/pdfreader-by-sparsh/issues
Author: Sparsh Sam
PackageName: OpenReader
PackageUrl: https://github.com/sparshsam/pdfreader-by-sparsh
License: AGPL-3.0
LicenseUrl: https://github.com/sparshsam/pdfreader-by-sparsh/blob/main/LICENSE
ShortDescription: Privacy-first, local-only PDF utility.
Moniker: openreader
Tags:
  - pdf
  - reader
  - privacy
  - local-first
InstallerType: msix
Installers:
  - Architecture: x64
    InstallerUrl: https://github.com/sparshsam/pdfreader-by-sparsh/releases/download/v1.2.2/OpenReader.msix
    InstallerSha256: [REPLACE WITH ACTUAL SHA256]
PackageFamilyName: SparshSam.OpenReader_yh0byntbzd2qw
ManifestType: singleton
ManifestVersion: 1.0.0
```

## Release Checklist Addition

Add this step to `RELEASE.md` after the existing validation checklist:

> - [ ] After Store approval and stable release validation, prepare Winget manifest update:
>   1. Fork [winget-pkgs](https://github.com/microsoft/winget-pkgs)
>   2. Create `manifests/s/SparshSam/OpenReader/<version>/`
>   3. Copy manifest template with updated version + SHA256
>   4. Submit PR

## Versioning

Winget uses the MSIX 4-part version string (e.g. `1.2.2.0`), which matches the version
in `AppxManifest.xml`. Each new release requires a new manifest directory.

## Update Flow

After initial submission, the winget bot automatically detects new releases and
opens PRs to update the manifest. No manual submission is needed for subsequent releases.

## Notes

- Do not submit Winget until Store certification is approved.
- Do not submit Winget before validating a Store-signed installation cycle.
- The SHA256 hash in the manifest must match the MSIX attached to the GitHub Release.
