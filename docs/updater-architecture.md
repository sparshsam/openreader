# Updater Architecture

**Version:** 1.2.0+  
**Status:** Self-update removed — MSIX/App Installer adopted

## History

### v1.0.0–v1.1.11: In-App Self-Updating (Removed)

Prior to v1.2.0, OpenReader (formerly PDFReader by Sparsh) included a complex
self-update system:

1. **Check for updates** — GitHub API call to find the latest release
2. **Download** — Download `Setup.exe` or ZIP to a temp directory
3. **Apply** — Launch PowerShell with UAC elevation to run the installer, or
   extract ZIP and run a batch script that copied files over the running app

This approach had several problems:
- **Self-replacement** — the running app attempted to overwrite its own files
- **UAC elevation** — updating required admin rights, which failed silently
  when launched from a non-admin context
- **Fragile batch scripts** — the ZIP-based updater used 120-line `.bat` files
  with retry loops and elevation detection
- **Installer conflicts** — Inno Setup's `/SILENT` mode didn't always work
  with running app detection
- **Platform gaps** — macOS auto-update was never implemented

### v1.2.0: MSIX/App Installer Adoption

The self-update system has been removed. Update responsibility belongs to
Windows packaging, not application code.

## ⚠️ Frozen Identity

The Microsoft Store identity is permanently frozen. See
[windows-distribution.md](windows-distribution.md#-frozen-identity-msix--microsoft-store)
for the complete table of frozen values.

| Field | Value |
|-------|-------|
| Identity Name | `SparshSam.OpenReader` |
| Publisher | `CN=E6186421-BF8A-47E0-A89C-0F513DFF91C0` |
| Package Family Name | `SparshSam.OpenReader_yh0byntbzd2qw` |
| Store ID | `9MXDVW2645LL` |
| Executable | `OpenReader.exe` |

**Identity Name and Publisher must never change.** Changing either after public
release breaks upgrade continuity. Store Display Name may change without
breaking upgrades.

## Current Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       OpenReader App                            │
│                                                                 │
│  Help → Check for Updates                                       │
│       ↓                                                         │
│  GitHub API: GET /repos/.../releases/latest                     │
│       ↓                                                         │
│  If newer → Dialog with "Open Releases Page" (browser)          │
│       ↓                                                         │
│  User downloads MSIX from GitHub / Microsoft Store              │
│       ↓                                                         │
│  Windows handles installation and future updates                │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│             Windows Packaging (Store / App Installer)            │
│                                                                 │
│  Microsoft Store:                                               │
│  • Automatic updates via Windows Update                         │
│  • No user action required                                      │
│                                                                 │
│  App Installer (future):                                        │
│  • Checks update URI on launch                                  │
│  • Background periodic checks                                   │
│  • Silent download + install                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Distribution Channels

| Channel | Status | Update Mechanism |
|---------|--------|-----------------|
| Microsoft Store | 🔒 Reserved | Windows Update (automatic) |
| GitHub Releases (MSIX) | ✅ Active | Manual download (unsigned — Developer Mode) |
| Winget | 🔜 Future | `winget install SparshSam.OpenReader` |
| GitHub Releases (Setup.exe) | ⚠️ Legacy | Manual download only — no in-app updates |

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
| All download/apply methods | — | ❌ Removed (~611 lines) |

### 2. MSIX Packaging (packaging/msix/)

- **AppxManifest.xml** — Frozen Store identity, capabilities, visual assets
- **AppInstaller.xml** — Update source configuration (future use)
- **build-msix.ps1** — Build script using MakeAppx.exe

### 3. GitHub Actions (release.yml)

The CI pipeline builds the MSIX from the PyInstaller output and attaches it
to the GitHub Release as `OpenReader.msix`.

## Update Flow (User Perspective)

### First Install
1. **Store:** Search "OpenReader" → Install
2. **GitHub:** Download `OpenReader.msix` → Double-click → Enable Developer Mode if unsigned
3. **Legacy:** Download `OpenReader-Setup.exe` → Run as Administrator

### Manual Update Check
1. Help → Check for Updates
2. If newer → dialog with "Open Releases Page"
3. Browser opens GitHub Releases
4. User downloads and installs

### Future: Automatic Updates
Once Store submission is active or App Installer is deployed:
1. Windows handles updates transparently
2. App never downloads or runs installers
3. No user interaction needed

## Security Model

- **No in-app download** — the app never downloads executables
- **No UAC elevation** — the app never requests admin rights for updates
- **No self-replacement** — the app never overwrites its own files
- **Windows-managed updates** — MSIX packages are validated by Windows
- **GitHub API only** — the only network request is the update check

## Limitations

- MSIX is unsigned for GitHub release builds — requires Developer Mode
- App Installer update flow is not yet active
- macOS does not have an MSIX equivalent; remains source-build only

## Future Work

- [ ] Submit MSIX to Microsoft Store
- [ ] Deploy App Installer hosting infrastructure
- [ ] Submit Winget manifest
- [ ] End-to-end validation on Windows 10/11
