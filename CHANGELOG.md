# Changelog

## v0.1.9 - 2026-05-31

- **Dark mode.** System-aware Catppuccin Mocha theme with Auto/Light/Dark toggle in View → Theme.
- **Recent files.** Last 10 PDFs accessible from File → Open Recent with dead-file cleanup.
- **Multi-tab PDF support.** Open several documents in one window with QTabBar tabs. Ctrl+T new tab, Ctrl+W close tab. Each tab remembers page, zoom, search, and selection.
- **Menu bar.** File (Open Recent, Close Tab/All, Quit), View (Theme, Zoom), Tools (Merge/Split/Compress), Help (Updates, About).
- **macOS auto-update overhaul.** Rewrote shell updater with retry logic, process-wait via PID, quarantine clearance (xattr -cr), and stable script path outside extract dir.
- **Fit Width menu item** synced with button state.
- Rebased on v0.1.8 onedir fixes from the update-main branch.

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
