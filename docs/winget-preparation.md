# Winget Publication

**Community repository status:** 🟡 Manifest prepared; Windows validation and PR submission pending
**Microsoft Store status:** ✅ [Live in Microsoft Store](https://apps.microsoft.com/detail/9MXDVW2645LL)

## Package Identity

| Field | Value |
|---|---|
| Community package identifier | `SparshSam.OpenReader` |
| Microsoft Store product ID | `9MXDVW2645LL` |
| Package family name | `SparshSam.OpenReader_yh0byntbzd2qw` |
| Publisher | `Sparsh Sam` |
| License | AGPL-3.0-only |
| Community installer type | Inno Setup |

The Microsoft Store and Winget community repository are separate sources. The Store
listing can be installed directly with:

```powershell
winget install --id 9MXDVW2645LL --source msstore
```

The `winget-pkgs` schema does not support a Store listing as an installer. The
community manifest therefore uses the versioned `OpenReader-Setup.exe` release
asset and exposes the stable `SparshSam.OpenReader` identifier:

```powershell
winget install --id SparshSam.OpenReader --exact
```

The GitHub `OpenReader.msix` is deliberately not used by the community manifest:
v1.2.2 is unsigned and cannot install on a normal Windows configuration. Store
certification does not add a signature to the separately published GitHub asset.

## Prepared Manifest

The submit-ready multi-file manifest is tracked at:

```text
packaging/winget/manifests/
  s/SparshSam/OpenReader/1.2.2/
    SparshSam.OpenReader.yaml
    SparshSam.OpenReader.installer.yaml
    SparshSam.OpenReader.locale.en-US.yaml
```

Verified release metadata:

| Field | Value |
|---|---|
| Release | `v1.2.2` |
| Published | 2026-06-18 |
| Asset | `OpenReader-Setup.exe` |
| SHA-256 | `2FC3EC8D7439B21379FBB82A7E4E4F5B15B8E32E678B98DDFC9A1743EED359B2` |
| Inno product code | `{D3A7F9E1-4B2C-4A8F-9E6D-1C5B3A7F9E01}_is1` |

## Validation and Submission

Complete these steps on Windows after the GitHub repository rename is live:

```powershell
# Confirm no package or open PR already uses the identifier.
winget search --id SparshSam.OpenReader --exact

# Validate schema and semantics.
winget validate --manifest .\packaging\winget\manifests\s\SparshSam\OpenReader\1.2.2

# Test an unattended install from the local manifest.
winget settings --enable LocalManifestFiles
winget install --manifest .\packaging\winget\manifests\s\SparshSam\OpenReader\1.2.2 --silent

# Submit with winget-create after its GitHub authentication step.
wingetcreate submit .\packaging\winget\manifests\s\SparshSam\OpenReader\1.2.2
```

Before submission, verify that installation succeeds in Windows Sandbox, OpenReader
launches, version `1.2.2` is shown, `winget list --id SparshSam.OpenReader --exact`
correlates the installed package, and uninstall succeeds.

## Release Checklist

- [x] Stable release asset naming (`OpenReader-Setup.exe`)
- [x] Stable release workflow
- [x] Microsoft Store certification approved
- [x] Multi-file Winget 1.12 manifest prepared
- [x] Release hashes independently verified
- [ ] Repository renamed and new release URL confirmed
- [ ] Local manifest validated with Winget on Windows
- [ ] Silent install, launch, detection, upgrade, and uninstall tested in Windows Sandbox
- [ ] Manifest submitted to `microsoft/winget-pkgs`
- [ ] Submission PR merged and `winget install --id SparshSam.OpenReader --exact` verified

## Future Releases

Winget package versions follow the semantic GitHub release version (`1.2.2`), not
the four-part internal MSIX version (`1.2.2.0`). For each stable release:

1. Publish and test `OpenReader-Setup.exe`.
2. Run `wingetcreate update SparshSam.OpenReader -u <versioned-installer-url>`.
3. Validate the generated manifest in Windows Sandbox.
4. Submit one package-version PR to `microsoft/winget-pkgs`.

Do not assume that Winget will automatically open update PRs. Configure a separate
release automation only after the first community manifest is merged.
