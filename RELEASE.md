# Release and Versioning

PDFReader by Sparsh uses semantic version tags to publish packaged builds.

## Version Source of Truth

- Development source keeps `__version__` in `main.py` as a `-dev` version.
- Packaged release builds inject the release version from the Git tag.
- Tags must use the format `vMAJOR.MINOR.PATCH`, for example `v0.3.1`.
- The injected runtime version removes the leading `v`, so `v0.3.1` becomes `__version__ = "0.3.1"` in packaged builds.

## Canonical Release Assets

The in-app updater only looks at assets attached to:

```text
https://api.github.com/repos/sparshsam/pdfreader-by-sparsh/releases/latest
```

The release workflow must attach these assets:

```text
PDFReader-by-Sparsh-Windows.zip          (updater package — do not download unless instructed)
PDFReader-by-Sparsh-Setup.exe            (Windows installer — recommended for normal use)
PDFReader-by-Sparsh-macOS-Apple-Silicon.zip
PDFReader-by-Sparsh-macOS-Intel.zip
```

The updater uses only `PDFReader-by-Sparsh-Windows.zip`. The `-Setup.exe` is the recommended download for normal Windows users.
Do not rename or remove the canonical ZIP assets without updating `main.py`.

## How to Cut a Release

1. Make sure `main` is green in GitHub Actions.
2. Update `CHANGELOG.md`.
3. Commit all release notes/docs changes.
4. Create and push a semantic version tag:

   ```bash
   git tag v0.3.1
   git push origin v0.3.1
   ```

5. GitHub Actions runs `.github/workflows/release.yml`.
6. The workflow builds Windows, macOS Apple Silicon, and macOS Intel packages.
7. The workflow creates the GitHub Release and attaches the canonical ZIP assets.

## Auto-Update Discovery

The app's updater:

1. Calls the GitHub latest release API.
2. Reads `tag_name`.
3. Compares `tag_name` against the packaged app's injected `__version__`.
4. Selects the platform asset by exact canonical filename.
5. Downloads and applies the package for supported packaged builds.

Source builds usually run with a `-dev` version and are not the primary auto-update target. Developers should update source builds with `git pull` and rebuild locally.

## Validation Checklist

After publishing a tag:

- [ ] The release workflow completed successfully.
- [ ] The GitHub Release exists for the pushed tag.
- [ ] The release contains `PDFReader-by-Sparsh-Windows.zip` (updater).
- [ ] The release contains `PDFReader-by-Sparsh-macOS-Apple-Silicon.zip`.
- [ ] The release contains `PDFReader-by-Sparsh-macOS-Intel.zip`.
- [ ] Downloaded packaged builds show the tag-injected version in **Help > About**.
- [ ] `releases/latest` returns the new tag and all assets (including Setup.exe).
- [ ] An older packaged build detects the newer version.
- [ ] The updater selects the correct asset for Windows.
- [ ] The updater selects the Apple Silicon asset on arm64 macOS.
- [ ] The updater selects the Intel asset on Intel macOS.

You can inspect the latest release assets with:

```bash
gh release view --repo sparshsam/pdfreader-by-sparsh --json tagName,assets
```

Or via the same API used by the app:

```bash
curl https://api.github.com/repos/sparshsam/pdfreader-by-sparsh/releases/latest
```

## Troubleshooting

### `update_None` Appears

Problem:

The updater reports that an update was saved to a path like:

```text
%TEMP%\PDFReader-Updates\update_None
```

Cause:

Older updater builds could lose download metadata before the download-finished
handler ran. When the asset name or release tag was missing, the updater
synthesized a fallback filename from shared mutable fields instead of preserving
the selected release asset name.

Resolution:

The updater now binds immutable metadata directly to the `QNetworkReply` with
`asset_name` and `latest_tag` properties. The download-finished handler reads
those reply properties, saves Windows updates only as
`PDFReader-by-Sparsh-Windows.zip`, and fails loudly if metadata is missing.
Windows ZIP updates are routed only when the canonical Windows asset name is
present, preventing silent manual-install fallbacks.
