# macOS Support

OpenReader is written with cross-platform Python libraries, so the app source can run on macOS. The Windows `.exe` cannot run on macOS, so Mac users need a macOS build.

## Why a Separate Mac Build Is Needed

- Windows `.exe` files and macOS `.app` bundles are different operating-system package formats.
- PyInstaller bundles the Python interpreter and native dependencies for the operating system it is running on.
- A build made on Windows is therefore a Windows app, while a build made on macOS is a macOS app.
- macOS also has Gatekeeper security checks. For smooth public distribution, apps should be code-signed and notarized with Apple Developer credentials.

## Current Mac Compatibility

The app is designed to be Mac-compatible where the underlying libraries are available:

- PySide6 provides the native desktop UI.
- PyMuPDF provides PDF rendering, search, merge, split, and compression.
- The app accepts an initial PDF path from `sys.argv`.
- The macOS build uses PyInstaller `--argv-emulation` so Finder "Open With" document events are converted into command-line arguments when possible.
- The macOS build generates a native `.icns` icon from the project icon source before packaging.

## Build on macOS

Requirements:

- macOS
- Python 3.11 or newer
- Git, if cloning the repository

Clone and build:

```bash
git clone https://github.com/sparshsam/openreader.git
cd openreader
chmod +x scripts/build_macos.sh
./scripts/build_macos.sh
```

The app bundle is created at:

```text
dist/OpenReader.app
```

Run it:

```bash
open "dist/OpenReader.app"
```

## Use "Open With" on macOS

After building:

1. Right-click a PDF in Finder.
2. Choose **Open With > Other...**.
3. Select `dist/OpenReader.app`.
4. Optionally choose **Always Open With**.

## Security Warning

Personal builds are usually unsigned and not notarized. macOS may warn that the app cannot be verified.

For personal use, you can usually allow it in:

```text
System Settings > Privacy & Security
```

For public distribution, use Apple Developer ID code signing and notarization.

## OCR on macOS

Normal PDF text selection does not need OCR.

For scanned/image-only PDFs, OCR depends on Tesseract OCR data being available to PyMuPDF. If OCR data is missing, the app will show a clear message and continue working for normal PDFs.
