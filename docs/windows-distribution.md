# Windows Distribution Strategy

**Version:** 1.2.0+  
**Status:** In-progress migration from Inno Setup to MSIX/App Installer

## Overview

PDFReader by Sparsh has historically been distributed via Inno Setup installer
(`Setup.exe`) and portable ZIP archive. Starting with v1.2.0, the Windows
distribution strategy is migrating to **MSIX** — Microsoft's modern packaging
format — with **App Installer** integration for Windows-managed updates.

## Distribution Formats

| Format | File | Status | Purpose |
|--------|------|--------|---------|
| **MSIX** | `PDFReader-by-Sparsh.msix` | ✅ New (v1.2.0) | Primary distribution target. Supports App Installer for automatic updates. |
| **Inno Setup** | `PDFReader-by-Sparsh-Setup.exe` | ⚠️ Legacy | Existing installer — kept as fallback. Requires admin rights. No longer supports in-app updates. |
| **Portable ZIP** | `PDFReader-by-Sparsh-Windows.zip` | ⚠️ Legacy | Portable/manual recovery package. No updates. |

## MSIX Packaging

### Requirements

- **Windows 10 1809+** (build 17763 or later)
- **Windows SDK** (for `MakeAppx.exe`) — optionally Visual Studio Build Tools
- **Code-signing certificate** (required for distribution outside Developer Mode)

### Build Process

The MSIX package is built from the PyInstaller output directory:

```
PyInstaller build → Staging directory → MakeAppx → MSIX → Sign → Distribution
```

The build:
1. Runs PyInstaller to produce `dist/PDFReader by Sparsh/`
2. Copies files into an MSIX staging directory
3. Patches `AppxManifest.xml` with the release version
4. Runs `MakeAppx.exe pack` to create the MSIX
5. Signs the MSIX with a code-signing certificate (when available)

See `packaging/msix/build-msix.ps1` for the full build script.

### GitHub Actions CI

The `release.yml` workflow builds an unsigned MSIX as a CI artifact. Because
a code-signing certificate has not yet been procured, the MSIX artifact is
unsigned and requires Windows Developer Mode for sideloading.

**Tracking:** Code-signing certificate purchase and integration is tracked
as a future improvement. See [CHANGELOG](../CHANGELOG.md).

## App Installer Updates

The `AppInstaller.xml` file enables Windows App Installer to manage updates:

1. The MSIX is published as a GitHub Release asset
2. The AppInstaller XML on the release page points to the MSIX URL
3. Windows checks for updates on launch and periodically in the background
4. Updates download and install silently (no UAC for per-user installs)

The app itself no longer downloads or runs installers. See
[updater-architecture.md](updater-architecture.md) for the full architecture.

## Code Signing

For the MSIX to be installable without Developer Mode, it must be signed with
a code-signing certificate trusted by the user's machine. Options:

| Option | Cost | Trust |
|--------|------|-------|
| Individual/OV code-signing cert | ~$200-300/year | Standard — trusted by Windows |
| EV code-signing cert | ~$300-500/year | Higher — immediate SmartScreen reputation |
| Self-signed | Free | Local only — requires manual trust |

Without signing, users must enable Developer Mode:
`Settings → Privacy & security → For developers → Developer Mode`

## Legacy Inno Setup Installer

The Inno Setup installer (`installer/setup.iss`) is retained as a legacy
fallback for users who prefer it or need it for compatibility. Key differences
from MSIX:

| Aspect | MSIX | Inno Setup |
|--------|------|------------|
| **Admin required** | No (per-user) | Yes |
| **Update mechanism** | Windows App Installer | Manual download only |
| **Clean uninstall** | Automatic | Partial (some registry may remain) |
| **File association** | Declared in manifest | Registry-based |
| **Install location** | Managed by Windows | `Program Files` |
| **Self-update from app** | No (Windows handles it) | No (removed in v1.2.0) |

## Migration Path

For existing users:

1. **v1.1.x users** can install the MSIX alongside their existing installation
   (they are independent). User settings in `%APPDATA%` are shared.
2. **New installs** should use the MSIX when signed or Developer Mode is acceptable.
3. **v1.2.0+** will shift toward MSIX as the primary distribution format.

## Open Items

- [ ] Procure code-signing certificate
- [ ] Integrate signing into CI workflow (requires secure key storage)
- [ ] Set up App Installer index file on GitHub Pages for update discovery
- [ ] Validate MSIX on Windows 10 1809, 21H2, 22H2, and Windows 11
- [ ] Validate App Installer update flow end-to-end
- [ ] Determine whether to make MSIX the default download on the releases page
