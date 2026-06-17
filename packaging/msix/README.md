# MSIX Packaging for PDFReader by Sparsh

This directory contains the MSIX/App Installer packaging configuration for PDFReader by Sparsh.

## Overview

MSIX is Microsoft's modern packaging format for Windows applications. It provides:

- **Clean install/uninstall** — no leftover registry keys or files
- **Identity-based app management** — Windows knows the app is installed
- **App Installer integration** — updates are handled by Windows, not the app
- **Per-machine or per-user install** — no admin elevation required for per-user installs
- **Automatic updates** — App Installer checks for updates on launch and in the background

## Files

| File | Purpose |
|------|---------|
| `AppxManifest.xml` | MSIX package manifest — identity, capabilities, visual assets |
| `AppInstaller.xml` | App Installer file — enables automatic updates from GitHub Releases |
| `build-msix.ps1` | PowerShell build script — creates and signs the MSIX package |
| `README.md` | This file |

## Prerequisites (Windows Build Machine)

1. **Windows 10 1809+** (build 17763+)
2. **Windows SDK** (includes `MakeAppx.exe`)
   - Install from: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/
   - Or via Visual Studio Installer → "Desktop development with C++"
3. **PyInstaller-built application** — run the project's build script first:
   ```powershell
   .\scripts\build_windows.ps1
   ```
4. **Code-signing certificate** (optional for sideloading, required for distribution):
   - A code-signing certificate (.pfx) from a trusted CA (DigiCert, Sectigo, etc.)
   - Self-signed certificates work for local testing in Developer Mode

## Building

### Quick build (unsigned — local sideload only)

```powershell
# From repo root, after PyInstaller build:
.\packaging\msix\build-msix.ps1 -ExeDir ".\dist\PDFReader by Sparsh" -Version "1.2.0.0"
```

### Signed build (for distribution)

```powershell
.\packaging\msix\build-msix.ps1 `
    -ExeDir ".\dist\PDFReader by Sparsh" `
    -Version "1.2.0.0" `
    -PfxPath ".\certificate.pfx" `
    -PfxPassword "your-password"
```

## Output

The script generates:

| File | Description |
|------|-------------|
| `PDFReader-by-Sparsh.msix` | MSIX package — the application payload |
| `PDFReader-by-Sparsh.msix` (signed) | Signed MSIX ready for distribution |

## Installing

### Via App Installer (recommended)

1. Download `PDFReader-by-Sparsh.msix` from GitHub Releases
2. Double-click the `.msix` file — Windows App Installer handles the rest
3. Or open `PDFReader-by-Sparsh.appinstaller` (if using the AppInstaller protocol)

### Via PowerShell (sideloading)

```powershell
Add-AppxPackage -Path .\PDFReader-by-Sparsh.msix
```

If unsigned and not in Developer Mode, Windows will block installation. Enable
**Developer Mode** in Settings → Privacy & security → For developers, or use a
signed package.

## Updating

Updates are handled by **Windows App Installer**, not by PDFReader itself:

1. A new MSIX is published as a GitHub Release asset
2. The AppInstaller.xml on the release points to the latest package
3. Windows checks for updates:
   - Every time the app launches
   - Periodically in the background (managed by Windows)
4. Updates download and install silently — no UAC prompt for per-user installs

The app's Help → Check for Updates menu only opens the GitHub Releases page
in a browser. It does not download or run any installer.

## Visual Assets

The AppxManifest references logo assets under an `assets/` subdirectory within
the package. The build script creates minimal placeholders. For production
packaging, replace these with properly sized application icons:

| Asset | Size | Purpose |
|-------|------|---------|
| `assets/icon-44x44.png` | 44×44 | App list / Taskbar |
| `assets/icon-150x150.png` | 150×150 | Start menu medium tile |
| `assets/icon-71x71.png` | 71×71 | Start menu small tile |
| `assets/icon-310x150.png` | 310×150 | Wide tile |
| `assets/icon-620x300.png` | 620×300 | Splash screen |

All assets should be generated from the application icon
(`assets/pdfreader_by_sparsh.ico` or a corresponding PNG source).

## Known Limitations

- **MSIX package contents are read-only** — the app cannot write to its own
  install directory. All user data (settings, cache) goes to `%LOCALAPPDATA%`.
- **Registration-free COM** — if the app depends on system-wide COM
  registration, it must be declared in the manifest.
- **File system access** — the app has access to `%LOCALAPPDATA%`, `%APPDATA%`,
  and user-requested file paths (via file picker or drag-and-drop).
- **Code signing** — without a valid code-signing certificate, the MSIX can
  only be sideloaded in Developer Mode.

## Security

The MSIX format is inherently more secure than traditional installers:

- **No admin elevation** for per-user installs
- **Package identity** — the app runs with a known identity
- **Declared capabilities** — the app can only do what the manifest allows
- **Clean uninstall** — no orphaned registry entries or files
- **Read-only package** — prevents tampering with installed files

## Legacy Installer

The Inno Setup installer (`installer/setup.iss`) remains available as a
legacy/manual fallback. The MSIX package is the recommended distribution
format for v1.2.0+.
