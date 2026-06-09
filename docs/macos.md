# macOS Support

PDFReader by Sparsh is built with cross-platform libraries (PySide6, PyMuPDF)
so the source can run on macOS. Packaged releases are distributed as **ZIP
archives** (updater canonical) and **DMG disk images** (polished install UX).

## Installing from DMG (Recommended)

1. Go to the [Releases page](https://github.com/sparshsam/pdfreader-by-sparsh/releases/latest).
2. Download the **DMG** that matches your Mac:
   - Apple Silicon (M1/M2/M3/M4): `PDFReader-by-Sparsh-macOS-Apple-Silicon-{version}.dmg`
   - Intel: `PDFReader-by-Sparsh-macOS-Intel-{version}.dmg`
3. Double-click the `.dmg` to mount it.
4. Drag **PDFReader by Sparsh.app** into the **Applications** folder (the
   DMG window shows a shortcut to /Applications).
5. Eject the DMG.
6. Open the app from **Applications** or Spotlight.

### First Launch

macOS may show a warning: **"PDFReader by Sparsh" cannot be opened because
it is from an unidentified developer.** See the [Gatekeeper section](#gatekeeper)
below for how to handle this.

## Installing from ZIP (Portable / Manual)

Download the `.zip` matching your Mac's architecture, extract it, and run
`PDFReader by Sparsh.app` from the extracted folder. No admin rights needed.
The updater uses ZIP assets — see [Update Behavior](#update-behavior).

## Why a Separate Mac Build Is Needed

- Windows `.exe` files and macOS `.app` bundles are different package formats.
- PyInstaller bundles native binaries for the OS it runs on — a Windows build
  cannot run on macOS and vice versa.
- macOS also requires separate builds for Apple Silicon and Intel (they use
  different native library binaries).

## Apple Silicon vs Intel

| Architecture | CI Runner | Asset Name Prefix |
|-------------|-----------|-------------------|
| Apple Silicon (M1–M4) | `macos-15` (ARM) | `PDFReader-by-Sparsh-macOS-Apple-Silicon` |
| Intel | `macos-15-intel` | `PDFReader-by-Sparsh-macOS-Intel` |

The in-app updater selects the correct asset automatically based on
`platform.machine()`:

- `arm64` / `aarch64` → Apple Silicon
- Everything else → Intel

## Gatekeeper

Unsigned apps trigger Gatekeeper warnings. Here's how to handle them:

### "Cannot be opened because it is from an unidentified developer"

1. Open **System Settings → Privacy & Security**.
2. Scroll down to the **Security** section.
3. You will see a message: **"PDFReader by Sparsh" was blocked from opening
   because it is not from an identified developer.**
4. Click **Open Anyway**.
5. Enter your password (or use Touch ID) to confirm.
6. The app will launch. You only need to do this once per version.

### "PDFReader by Sparsh is damaged and can't be opened"

This usually means the quarantine attribute was set incorrectly. Fix it
from Terminal:

```bash
# Check the quarantine attribute
xattr "PDFReader by Sparsh.app"

# Remove it if needed
xattr -d com.apple.quarantine "PDFReader by Sparsh.app"
```

This can happen when the app is downloaded through certain browsers or
unarchivers that set the quarantine flag but Gatekeeper can't verify the
app identity.

### Why Gatekeeper blocks the app

- The builds are **not code-signed** with an Apple Developer ID certificate
  (signing costs $99/year for the Apple Developer Program).
- The builds are **not notarized** by Apple (requires signing first).
- macOS treats unsigned apps as potentially unsafe.
- There is no malware risk — the warning is about the **lack of a signed
  developer identity**, not about the app's safety.

See [docs/macos-signing.md](macos-signing.md) for the code signing and
notarization roadmap.

### Quarantine Attribute

macOS automatically adds a quarantine attribute (`com.apple.quarantine`) to
files downloaded from the internet. This is what triggers the Gatekeeper
check on first launch. The "Open Anyway" flow removes this attribute.

## Update Behavior

- The **built-in auto-updater** checks GitHub Releases and detects new
  versions on launch.
- The updater looks for the **ZIP asset** matching the Mac's architecture
  (`PDFReader-by-Sparsh-macOS-Apple-Silicon.zip` or `-Intel.zip`).
- The updater **does not use the DMG** — DMGs are for initial install only.
- Updates replace the `.app` bundle in place (the app is inside
  `/Applications` or wherever the user installed it).
- User settings (Qt QSettings) are stored under
  `~/Library/Preferences/com.Sparsh.PDFReader-by-Sparsh.plist` and are
  preserved across updates.
- Library index data lives under `~/.pdfreader/library/` and is preserved.

### Updater Limitations on macOS

| Limitation | Details |
|------------|---------|
| **No app relocation** | The updater replaces the existing `.app` in-place. If the user moved the app, the update writes to the original path. |
| **Gatekeeper re-trigger** | After an update, Gatekeeper may warn again because the new `.app` is a fresh download. The "Open Anyway" flow is needed again. |
| **ZIP only** | The updater only supports ZIP-based updates, not DMG. This is intentional — ZIP update is simpler and more reliable for in-place replacement. |
| **No delta updates** | The full `.app` bundle is replaced each update. No binary diff or incremental patching. |

## Build on macOS

### Prerequisites

- macOS (Apple Silicon or Intel)
- Python 3.11 or newer
- Git (for cloning)

### Build Steps

```bash
git clone https://github.com/sparshsam/pdfreader-by-sparsh.git
cd pdfreader-by-sparsh
chmod +x scripts/build_macos.sh
./scripts/build_macos.sh
```

The app bundle is created at:

```text
dist/PDFReader by Sparsh.app
```

Run it:

```bash
open "dist/PDFReader by Sparsh.app"
```

### Build DMG

After building the `.app`, optionally create a polished DMG:

```bash
# Install create-dmg first
brew install create-dmg

# Create the DMG
./scripts/create_dmg.sh
```

Output:

```text
dist/PDFReader-by-Sparsh-{version}-Apple-Silicon.dmg
# or
dist/PDFReader-by-Sparsh-{version}-Intel.dmg
```

## "Open With" on macOS

To open PDFs directly with PDFReader by Sparsh:

1. Right-click a PDF in Finder.
2. Choose **Open With → Other...**.
3. Navigate to `PDFReader by Sparsh.app` (in `/Applications` if installed, or
   in `dist/` if building from source).
4. Check **Always Open With**.
5. Click **Open**.

## Known macOS Limitations

| Limitation | Details |
|------------|---------|
| **No code signing** | Gatekeeper warns on first launch of every new version. |
| **No notarization** | Apple has not reviewed the app. No stapled ticket. |
| **No sandbox** | The app runs with full user permissions. No App Sandbox enforcement. |
| **No hardended runtime** | The app is not compiled with the hardened runtime (requires code signing). |
| **Bundle not moved** | The updater replaces the `.app` in-place — it won't move it to /Applications if the user ran it from Downloads. |
| **No .icns on first build** | The icon is generated from `create_icon.py` which requires PySide6. First build always generates it. |
| **Tesseract OCR** | Requires separate Tesseract install for scanned PDFs (see OCR Setup in README). Not bundled. |

## OCR on macOS

Normal PDF text selection does not need OCR. For scanned/image-only PDFs,
the app falls back to OCR via PyMuPDF's Tesseract integration. Install
Tesseract with:

```bash
brew install tesseract
```

No restart needed — PyMuPDF finds it automatically. See the [OCR Setup
section in README](../README.md#ocr-setup) for details.
