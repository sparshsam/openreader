# Project Status

Last updated: 2026-06-17

## Current State

- Repository: `sparshsam/pdfreader-by-sparsh`
- Local path: `/home/spars/Archived-Repos/pdfreader-by-sparsh`
- Active branch: `main`
- Local status after release work: clean and synced with `origin/main`
- Latest live release: `v1.1.11`
- Latest stable functional release: `v1.1.10`

## Recent Releases

### v1.1.10

Released the installer-based Windows updater fix.

- Windows in-app updates now select `OpenReader-Setup.exe`.
- `OpenReader-Windows.zip` remains available for portable/manual recovery use.
- Inno Setup now owns UAC elevation and replacement under `C:\Program Files`.
- Release workflow requires `OpenReader-Setup.exe`; release fails if it is missing.
- Release URL: `https://github.com/sparshsam/pdfreader-by-sparsh/releases/tag/v1.1.10`

### v1.1.11

Released as a dummy updater validation release.

- No functional app changes beyond version/docs bump.
- Purpose: let installed `v1.1.10` builds detect a newer release and test `v1.1.10 -> v1.1.11` update flow.
- Expected updater asset: `OpenReader-Setup.exe`.
- Release URL: `https://github.com/sparshsam/pdfreader-by-sparsh/releases/tag/v1.1.11`

## Verification Completed

- PR checks passed for both release PRs.
- `v1.1.10` GitHub release workflow passed.
- `v1.1.11` GitHub release workflow passed.
- Both releases include all canonical assets:
  - `OpenReader-Setup.exe`
  - `OpenReader-Windows.zip`
  - `OpenReader-macOS-Apple-Silicon.zip`
  - `OpenReader-macOS-Intel.zip`
- `releases/latest` points to `v1.1.11`.
- Branch protection review requirement was restored to `1`.
- Temporary release branches were deleted/pruned.

## Next Test

Install `v1.1.10` on Windows, then use **Help -> Check for Updates**.

Expected result:

1. App detects `v1.1.11`.
2. App downloads `OpenReader-Setup.exe`.
3. UAC prompt appears via PowerShell `Start-Process -Verb RunAs`.
4. Inno Setup applies update.
5. App relaunches as `v1.1.11`.
6. Updater diagnostics are written to `%TEMP%\PDFReader-Updates\updater-debug.log`.
