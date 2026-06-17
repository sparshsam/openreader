# Release and Versioning

PDFReader by Sparsh uses semantic version tags to publish packaged builds.

## Version Source of Truth

- Development source keeps `__version__` in `main.py` as a `-dev` version.
- Packaged release builds inject the release version from the Git tag.
- Tags must use the format `vMAJOR.MINOR.PATCH`, for example `v1.2.0`.
- The injected runtime version removes the leading `v`, so `v1.2.0` becomes `__version__ = "1.2.0"` in packaged builds.

## Release Architecture (v1.2.0+)

**Starting with v1.2.0, in-app self-updating has been removed.** The app no longer
downloads or runs installers. Windows distribution is migrating to MSIX/App Installer:

- **Update detection** — the app queries the GitHub API and opens the releases page
- **Update application** — handled by Windows App Installer (MSIX) or manual download
- **Legacy Setup.exe** — retained as a manual installer only; no in-app update triggering

See [docs/updater-architecture.md](docs/updater-architecture.md) for details.

## Canonical Release Assets

The release workflow attaches these assets:

```text
PDFReader-by-Sparsh.msix                    (MSIX package — recommended for v1.2.0+)
PDFReader-by-Sparsh-Setup.exe               (legacy Inno Setup installer — manual use only)
PDFReader-by-Sparsh-Windows.zip             (portable/manual recovery package)
PDFReader-by-Sparsh-macOS-Apple-Silicon.zip (macOS Apple Silicon — source-build testing)
PDFReader-by-Sparsh-macOS-Intel.zip         (macOS Intel — source-build testing)
```

The MSIX package is built unsigned (requires `MakeAppx.exe` from Windows SDK).
Until a code-signing certificate is procured, MSIX installation requires Windows
Developer Mode for sideloading.

## How to Cut a Release

1. Make sure `main` is green in GitHub Actions.
2. Update `CHANGELOG.md`.
3. Commit all release notes/docs changes.
4. Create and push a semantic version tag:

   ```bash
   git tag v1.2.0
   git push origin v1.2.0
   ```

5. GitHub Actions runs `.github/workflows/release.yml`.
6. The workflow builds Windows (MSIX + Setup.exe + ZIP), macOS Apple Silicon, and macOS Intel packages.
7. The workflow creates the GitHub Release and attaches all assets.

## Update Detection

The app's Help → Check for Updates:

1. Calls `https://api.github.com/repos/sparshsam/pdfreader-by-sparsh/releases/latest`
2. Reads `tag_name` and compares against `__version__`
3. If a newer version exists, shows a dialog with release notes
4. User clicks "Open Releases Page" → browser opens GitHub Releases
5. User downloads the MSIX (or Setup.exe) and installs manually

Source builds usually run with a `-dev` version and are not the primary update
target. Developers should update source builds with `git pull` and rebuild locally.

## Validation Checklist

After publishing a tag:

- [ ] The release workflow completed successfully.
- [ ] The GitHub Release exists for the pushed tag.
- [ ] The release contains `PDFReader-by-Sparsh.msix` (MSIX package, if MakeAppx was available).
- [ ] The release contains `PDFReader-by-Sparsh-Setup.exe` (legacy installer).
- [ ] The release contains `PDFReader-by-Sparsh-Windows.zip` (portable/recovery).
- [ ] The release contains `PDFReader-by-Sparsh-macOS-Apple-Silicon.zip`.
- [ ] The release contains `PDFReader-by-Sparsh-macOS-Intel.zip`.
- [ ] Downloaded packaged builds show the tag-injected version in **Help > About**.
- [ ] `releases/latest` returns the new tag
- [ ] An older packaged build detects the newer version (status bar message on launch, dialog via Help → Check for Updates).

You can inspect the latest release assets with:

```bash
gh release view --repo sparshsam/pdfreader-by-sparsh --json tagName,assets
```

Or via the same API used by the app:

```bash
curl https://api.github.com/repos/sparshsam/pdfreader-by-sparsh/releases/latest
```

## MSIX Signing

The MSIX package is currently unsigned. For it to be installable without
Developer Mode, a code-signing certificate must be procured and the CI
workflow updated to sign the package:

1. Purchase an OV or EV code-signing certificate from a trusted CA
2. Store the certificate securely as a GitHub Actions secret
3. Update `release.yml` to sign the MSIX with `signtool.exe` post-build

See [docs/windows-distribution.md](docs/windows-distribution.md) for more details.
