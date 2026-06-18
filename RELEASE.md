# Release and Versioning

OpenReader uses semantic version tags to publish packaged builds.

## Version Source of Truth

- `__version__` in `main.py` is the canonical source. Set it to the next release version.
- Tags must use the format `vMAJOR.MINOR.PATCH`, for example `v1.2.1`.
- The injected runtime version removes the leading `v`, so `v1.2.1` becomes `__version__ = "1.2.1"` in packaged builds.
- CI injects the tag version for release builds via `scripts/inject_version.py`.

## Release Architecture (v1.2.0+)

**Starting with v1.2.0, update detection replaces in-app self-updating.** The app no longer
downloads or runs installers. Windows distribution is migrating to MSIX/App Installer:

- **Update detection** — the app queries the GitHub API and opens the releases page
- **Update application** — handled by Windows App Installer (MSIX) or manual download
- **Legacy Setup.exe** — retained as a manual installer only; no update detection support

See [docs/updater-architecture.md](docs/updater-architecture.md) for details.

## Canonical Release Assets

The release workflow attaches these assets:

```text
OpenReader.msix                    (MSIX package — recommended for v1.2.0+)
OpenReader-Setup.exe               (legacy Inno Setup installer — manual use only)
OpenReader-Windows.zip             (portable/manual recovery package)
OpenReader-macOS-Apple-Silicon.zip (macOS Apple Silicon — source-build testing)
OpenReader-macOS-Intel.zip         (macOS Intel — source-build testing)
```

The MSIX package is built unsigned (requires `MakeAppx.exe` from Windows SDK).
GitHub Release MSIX packages require Windows Developer Mode for sideloading.
The Microsoft Store will sign the production MSIX with its Store identity —
no separate code-signing certificate is needed.

## How to Cut a Release

1. Make sure `main` is green in GitHub Actions.
2. Update `CHANGELOG.md`.
3. Commit all release notes/docs changes.
4. Create and push a semantic version tag:

   ```bash
   git tag v1.2.1
   git push origin v1.2.1
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
- [ ] The release contains `OpenReader.msix` (MSIX package, if MakeAppx was available).
- [ ] The release contains `OpenReader-Setup.exe` (legacy installer).
- [ ] The release contains `OpenReader-Windows.zip` (portable/recovery).
- [ ] The release contains `OpenReader-macOS-Apple-Silicon.zip`.
- [ ] The release contains `OpenReader-macOS-Intel.zip`.
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

The MSIX package is currently unsigned. The distribution plan is:

1. **Microsoft Store** — Submit the unsigned MSIX to the Microsoft Store. The Store
   signs the package automatically with its Store identity. **v1.2.1 is the first
   Store release candidate.**
2. **Sideloading** — Unsigned MSIX from GitHub Releases requires Windows
   Developer Mode. Local test-signing scripts are in `packaging/msix/`.
3. **No self-procured code-signing cert** — The Store handles production signing.
   Do not purchase a separate code-signing certificate.

See [docs/store-submission-checklist.md](docs/store-submission-checklist.md) and
[docs/windows-distribution.md](docs/windows-distribution.md) for details.
