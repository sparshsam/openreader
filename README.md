# PDFReader by Sparsh

A simple, local-first, non-commercial PDF reader built with Python, PySide6, and PyMuPDF.

PDFReader by Sparsh is meant to be a clean desktop utility: open PDFs, read them one page at a time, search, copy text, merge, split, and save compressed copies without uploading documents anywhere.

## Screenshots

![PDFReader by Sparsh main window](assets/screenshot-main.png)

![PDFReader by Sparsh search view](assets/screenshot-search.png)

## Why I Built This

I built PDFReader by Sparsh as a local-first alternative for reading and handling PDFs without uploading private documents to cloud services. The project helped me learn desktop GUI development, PDF processing, OCR fallback handling, and Windows executable packaging while creating a practical tool people can actually use.

## Features

- Native-looking PySide6 desktop UI.
- Open PDFs from disk.
- Open PDFs directly from Windows **Open with**.
- macOS source/build support, including a GitHub Actions macOS app build.
- Display one page at a time.
- Previous/next page navigation.
- Page number indicator and jump-to-page input.
- Fit-width view plus zoom in/out controls.
- Search text across the PDF.
- Previous/next search result navigation.
- Drag-select and copy text from the visible page.
- OCR-assisted selection fallback for scanned/image-only PDFs when Tesseract OCR data is available.
- Merge multiple PDFs into one.
- Split the open PDF into one file per page.
- Extract a page range like `1-3,5`.
- Save an optimized/compressed copy of the open PDF.
- Remembers the last opened folder with `QSettings`.
- Custom Windows app icon.

## Privacy

PDFReader by Sparsh processes PDFs locally. It does not use network services and does not upload PDFs.

## License and Use

PDFReader by Sparsh is free to use, share, study, and modify for non-commercial purposes under the [PolyForm Noncommercial License 1.0.0](LICENSE).

Commercial use, resale, paid redistribution, or bundling in a commercial product is not permitted without separate written permission from the copyright holder.

Note: earlier published versions may have been released under MIT. This license applies to the current codebase and releases from this license change forward.

## Requirements

- Windows for the packaged `.exe`
- macOS for source builds or macOS GitHub Actions artifacts
- Python 3.11 or newer for development

The packaged `.exe` does not require Python to be installed.

## Install From Release

Download the latest Windows executable from the GitHub Releases page, then run:

```text
PDFReader by Sparsh.exe
```

Windows may show a SmartScreen warning because community builds are not code-signed. Only run executables from sources you trust.

## Run From Source

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

## Build the Windows EXE

```powershell
.\scripts\build_windows.ps1
```

The executable will be created at:

```text
dist\PDFReader by Sparsh.exe
```

You can also run PyInstaller directly:

```powershell
pyinstaller --noconsole --onefile --name "PDFReader by Sparsh" --icon ".\assets\pdfreader_by_sparsh.ico" main.py
```

## Build the macOS App

The Windows `.exe` does not run on macOS. Mac users need a macOS build because PyInstaller packages native binaries for the operating system it runs on.

On a Mac:

```bash
git clone https://github.com/sparshsam/pdfreader-by-sparsh.git
cd pdfreader-by-sparsh
chmod +x scripts/build_macos.sh
./scripts/build_macos.sh
```

The app bundle will be created at:

```text
dist/PDFReader by Sparsh.app
```

See [docs/macos.md](docs/macos.md) for macOS setup, "Open With" notes, icon generation, OCR notes, and code-signing/notarization caveats.

## Use as Default PDF App

Windows does not allow apps to silently take over file defaults. To make this your default PDF app:

1. Right-click a PDF file.
2. Choose **Open with > Choose another app**.
3. Pick `PDFReader by Sparsh.exe`.
4. Select **Always use this app to open .pdf files**.
5. Click **OK**.

## OCR Notes

Normal text selection works for PDFs that already contain text.

For scanned/image-only PDFs, the app attempts OCR through PyMuPDF's Tesseract integration. If Tesseract OCR data is not available on the computer, the app shows a clear message and continues working for normal PDFs.

## Compatibility Notes

- Windows users can download and run the `.exe` release.
- macOS users need a `.app` built on macOS. The repository includes a macOS build script and CI workflow, but a Windows-built `.exe` cannot be converted into a native Mac app.
- Unsigned macOS builds may trigger Gatekeeper warnings. For broad distribution, Apple recommends Developer ID signing and notarization.

## Roadmap

- Dark mode.
- Recent files list.
- Multi-tab PDF support.
- Highlight and annotation tools.
- Better OCR setup instructions.
- Windows installer package.
- Code signing for smoother public downloads.

## Project Structure

```text
.
├── assets/                  # App icon asset
├── docs/                    # Platform notes
├── scripts/                 # Build scripts
├── tools/                   # Developer utilities, including icon generation
├── main.py                  # Main PySide6 app
├── requirements.txt         # Runtime/build dependencies
├── PDFReader by Sparsh.spec # PyInstaller spec
├── LICENSE
├── CONTRIBUTING.md
├── SECURITY.md
└── CHANGELOG.md
```

## License

PolyForm Noncommercial License 1.0.0. See [LICENSE](LICENSE).
