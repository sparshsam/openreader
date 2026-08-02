# Release and Versioning

OpenReader uses semantic version tags to publish packaged builds.

## Version Source of Truth

- `__version__` in `main.py` is the canonical source. Set it to the next release version.
- `scripts/inject_version.py` propagates the version to every canonical source so
  they stay in lockstep: `main.py`, `packages/mcp-server/pyproject.toml`,
  `packages/mcp-server/src/openreader_mcp.egg-info/PKG-INFO`, and both MSIX
  manifests (`AppxManifest.xml` / `AppInstaller.xml`, mapped to a 4-part
  version). Run `python scripts/inject_version.py X.Y.Z` after bumping `main.py`.
- MSIX manifests are only rewritten for strict semver versions; dev/test builds
  (`-dev`, `-test`) bump the code/MCP sources but leave the manifests to CI.
- Tags must use the format `vMAJOR.MINOR.PATCH`, for example `v1.2.2`.
- CI injects the tag version for release builds via `scripts/inject_version.py`.

## Release Architecture

OpenReader uses **update detection only** — the app never downloads or runs installers.

- **Update detection** — the app queries the GitHub API and opens the releases page in a browser
- **Update application** — handled by the Microsoft Store (automatic) or manual download
- **Legacy Setup.exe** — retained as a manual recovery installer only

See [docs/updater-architecture.md](docs/updater-architecture.md) for details.

## Canonical Release Assets

The release workflow attaches these assets:

```text
OpenReader.msix                    (MSIX package — recommended for advanced users)
OpenReader-Setup.exe               (legacy Inno Setup installer — manual recovery)
OpenReader-Windows.zip             (portable/manual recovery package)
OpenReader-macOS-Apple-Silicon.zip (macOS Apple Silicon — experimental)
OpenReader-macOS-Intel.zip         (macOS Intel — experimental)
```

The MSIX package is unsigned when built on CI (requires `MakeAppx.exe` from Windows SDK).
GitHub Release MSIX packages require Windows Developer Mode for sideloading.
The Microsoft Store signs the production MSIX with its Store identity —
no separate code-signing certificate is needed.

## How to Cut a Release

1. Make sure `main` is green in GitHub Actions.
2. Update `CHANGELOG.md`.
3. Commit all release notes/docs changes.
4. Create and push a semantic version tag:

   ```bash
   git tag v1.2.2
   git push origin v1.2.2
   ```

5. GitHub Actions runs `.github/workflows/release.yml`.
6. The workflow builds Windows (MSIX + Setup.exe + ZIP), macOS Apple Silicon, and macOS Intel packages.
7. The workflow creates the GitHub Release and attaches all assets.

## Update Detection

Update behaviour is channel-aware (v1.2.7). `pdfreader_lib/install_source.py`
detects how OpenReader was installed:

- **MSIX / Microsoft Store** — the app never calls GitHub. Help → Check for
  Updates shows the Software Updates dialog ("Updates are managed by the
  Microsoft Store") with an *Open Microsoft Store* button.
- **Setup.exe / portable ZIP** — the app queries GitHub:
  1. Calls `https://api.github.com/repos/sparshsam/openreader/releases/latest`
  2. Reads `tag_name` and compares against `__version__`
  3. If newer, shows the Software Updates dialog with current → latest, release
     notes, and a last-checked timestamp
  4. *Skip This Version* persists (`updateSkipVersion`) so the same release
     isn't re-announced; *Open Releases Page* opens GitHub Releases
- **Source** — no auto-update; developers `git pull` and rebuild.

Source builds usually run with a `-dev` version and are not the primary update
target.

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
gh release view --repo sparshsam/openreader --json tagName,assets
```

Or via the same API used by the app:

```bash
curl https://api.github.com/repos/sparshsam/openreader/releases/latest
```

## MSIX Signing

The MSIX package is unsigned for GitHub Release builds.

1. **Microsoft Store** — Live at
   [apps.microsoft.com/detail/9MXDVW2645LL](https://apps.microsoft.com/detail/9MXDVW2645LL).
   The Store signs the package automatically with its Store identity.
2. **Sideloading** — Unsigned MSIX from GitHub Releases requires Windows
   Developer Mode. Local test-signing scripts are in `packaging/msix/`.
3. **No self-procured code-signing cert** — The Store handles production signing.
   Do not purchase a separate code-signing certificate.

See [docs/store-submission-checklist.md](docs/store-submission-checklist.md) and
[docs/windows-distribution.md](docs/windows-distribution.md) for details.
