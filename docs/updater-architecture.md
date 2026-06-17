# Updater Architecture

**Version:** 1.2.0+  
**Status:** Redesigned — self-update removed, MSIX/App Installer adopted

## History

### v1.0.0–v1.1.11: In-App Self-Updating (Removed)

Prior to v1.2.0, PDFReader included a complex self-update system:

1. **Check for updates** — GitHub API call to find the latest release
2. **Download** — Download `Setup.exe` or ZIP to a temp directory
3. **Apply** — Launch PowerShell with UAC elevation to run the installer, or
   extract ZIP and run a batch script that copied files over the running app

This approach had several problems:
- **Self-replacement** — the running app attempted to overwrite its own files
- **UAC elevation** — updating required admin rights, which failed silently
  when launched from a non-admin context
- **Fragile batch scripts** — the ZIP-based updater used complex `.bat` files
  with retry loops and elevation detection
- **Installer conflicts** — Inno Setup's `/SILENT` mode didn't always work
  with running app detection, and the app sometimes relaunched before the
  installer finished
- **Platform gaps** — macOS auto-update was never implemented (the method
  was referenced but didn't exist)

### v1.2.0: MSIX/App Installer Adoption

In v1.2.0, the self-update system was removed and replaced with **Windows
App Installer** integration. The running app no longer downloads or executes
installers.

## Current Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PDFReader App                           │
│                                                                 │
│  Help → Check for Updates                                       │
│       ↓                                                         │
│  GitHub API: GET /repos/.../releases/latest                     │
│       ↓                                                         │
│  If newer version exists → Show dialog with "Open Releases Page"│
│       ↓                                                         │
│  User clicks → Browser opens GitHub Releases                    │
│       ↓                                                         │
│  User downloads MSIX and installs (Windows handles rest)        │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Windows App Installer                      │
│                                                                 │
│  • Checks for updates on app launch                             │
│  • Checks for updates periodically in background                │
│  • Downloads new MSIX silently                                  │
│  • Installs update quietly (no UAC for per-user installs)       │
│  • Next app launch uses the new version                         │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Update Detection (main.py)

The app retains update **detection** but not update **application**:

| Method | Purpose | Retained? |
|--------|---------|-----------|
| `_parse_version` | Parse semver tags for comparison | ✅ |
| `_classify_update_response` | Classify GitHub API responses | ✅ |
| `check_for_updates_silent` | Background check on launch | ✅ (show status bar only) |
| `check_for_updates` | Interactive Help → Check for Updates | ✅ (opens browser only) |
| `_on_update_check_reply` | Handle API response, show dialog | ✅ (opens releases page) |
| `_log_update` | Log update diagnostics | ✅ |
| `_start_download` | Download Setup.exe | ❌ Removed |
| `_on_download_finished` | Handle download completion | ❌ Removed |
| `_apply_update` | Route to platform-specific updater | ❌ Removed |
| `_apply_update_windows_installer` | Launch Setup.exe via PowerShell | ❌ Removed |
| `_apply_update_windows_zip` | Extract ZIP and run batch updater | ❌ Removed |
| `_check_post_update` | Verify post-update state | ❌ Removed |

### 2. MSIX Packaging (packaging/msix/)

- **AppxManifest.xml** — Package identity, capabilities, visual assets
- **AppInstaller.xml** — Update source configuration for Windows App Installer
- **build-msix.ps1** — Build script using MakeAppx.exe

### 3. GitHub Actions (release.yml)

The CI pipeline builds the MSIX from the PyInstaller output and attaches it
to the GitHub Release. Until a code-signing certificate is procured, the MSIX
is unsigned (requires Developer Mode for sideloading).

## Update Flow (User Perspective)

### First Install

1. User downloads `PDFReader-by-Sparsh.msix` from GitHub Releases
2. User double-clicks the MSIX file
3. Windows App Installer installs the app
4. App launches normally

### Post-Launch Update Check

1. App starts
2. If "Automatically Check for Updates" is enabled (default), a background
   HTTP request checks GitHub for a newer release
3. If a newer version exists, a brief status bar message appears
4. No dialog is shown automatically — the user can open Help → Check for
   Updates for details

### Manual Update

1. User opens **Help → Check for Updates**
2. App queries GitHub API for the latest release
3. If newer: dialog shows version info and release notes
4. User clicks **"Open Releases Page"**
5. Browser opens GitHub Releases page
6. User downloads and installs the new MSIX
7. Windows App Installer handles the rest

## Security Model

- **No in-app download** — the app never downloads executables
- **No UAC elevation** — the app never requests admin rights for updates
- **No self-replacement** — the app never overwrites its own files
- **Windows-managed updates** — MSIX packages are validated by Windows before
  installation
- **GitHub API only** — the only network request is the update check API call

## Limitations

- **MSIX is unsigned** — requires Developer Mode or a signed package for
  installation
- **App Installer requires Windows 10 1809+** — older versions need the
  legacy installer
- **No background auto-update** — Windows App Installer checks on launch and
  periodically, but the user must still initiate the update from the app
  (or wait for Windows background check)
- **macOS updates** — not covered by this architecture; macOS remains a
  source-build platform

## Future Work

- [ ] Code-signing certificate procurement
- [ ] CI integration for signed MSIX builds
- [ ] App Installer index file on GitHub Pages for direct `.appinstaller` links
- [ ] End-to-end validation of the App Installer update flow
- [ ] Windows 11 validation
