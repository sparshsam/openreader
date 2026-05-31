# Changelog

## Unreleased

- Changed project licensing from MIT to PolyForm Noncommercial License 1.0.0 for future versions.
- Added PDF safety pre-validation, render size limits, bounded search/OCR memory use, sanitized error dialogs, security scanning workflow, sensitive-file ignore patterns, and disabled UPX in release builds.

## 0.1.0

- Native PySide6 desktop PDF reader.
- PDF rendering with PyMuPDF.
- Open PDFs from disk or through Windows "Open with".
- Page navigation, jump to page, fit width, and zoom controls.
- Text search with previous/next match navigation.
- Drag-select and copy text from PDF pages.
- OCR-assisted selection fallback when Tesseract OCR data is available.
- Merge multiple PDFs.
- Split PDFs by page or page range.
- Save compressed PDF copies.
- Custom app icon and PyInstaller Windows build.
- macOS source build script and GitHub Actions macOS app build workflow.

## v0.1.8 - 2026-05-31

- **Switched PyInstaller from `--onefile` to `--onedir` mode.**
  - The `_MEI*` temp-folder extraction caused `python311.dll` load failures on certain Windows configurations.
  - With `--onedir`, all DLLs live in an `_internal\` folder next to the EXE — no extraction, no temp directory issues.
- **ZIP-based releases.** Windows builds now produce a ZIP containing the EXE + `_internal\` folder.
- **Auto-update overhaul.**
  - Downloads a ZIP instead of a single EXE.
  - Extracts, copies the `_internal\` folder and EXE over the current install, then restarts.
  - Handles both `--onefile` (.exe) and `--onedir` (.zip) updates for backwards compatibility.
- **Version injection fix.** CI now fetches tags so `git describe` works, giving each build its correct version.
- **Removed workarounds.** Dropped `--runtime-tmpdir` and `Unblock-File` code — no longer needed without temp extraction.
