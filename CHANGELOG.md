# Changelog

## v0.4.1 - 2026-06-09

- **Repo Governance Polish.** Added professional GitHub issue templates:
  - `.github/ISSUE_TEMPLATE/bug_report.yml` — structured form with environment, reproduction steps, screenshots
  - `.github/ISSUE_TEMPLATE/feature_request.yml` — problem/solution/scope checkbox
  - `.github/ISSUE_TEMPLATE/documentation_issue.yml` — type dropdown, file location
- **Polished PR template** at `.github/PULL_REQUEST_TEMPLATE.md` with checklist, type of change, testing instructions.
- **Refined SUPPORT.md** — added supported platforms table, known limitations, updater limitations, and unsupported workflows.
- **Refined CONTRIBUTING.md** — added test commands, code quality checks, license agreement, and template references.
- **Refined RELEASE.md** — updated validation checklist to include pytest and Setup.exe, added CI jobs reference table, added troubleshooting section.
- **CI enhancement** — pytest service-level tests added to the Validate job in `.github/workflows/ci.yml`.
- **Bumped `__version__`** to `0.4.1-dev`.
- All changes are documentation/governance only — no application code or UX changes.

## v0.3.6 - 2026-06-08

- Published the Windows installer as `PDFReader-by-Sparsh-Setup.exe` on GitHub Releases.
- Fixed Inno Setup [Files] source path resolution so the installer correctly includes the PyInstaller build output.
- Fixed GitHub Actions Windows release packaging to reliably install Inno Setup via Chocolatey.
- Removed broken install-time DirExists check that prevented files from being copied during installation.
- Kept `PDFReader-by-Sparsh-Windows.zip` as the canonical updater and portable/manual asset.
- Updated download documentation to recommend the installer for normal Windows users.
- Asset validation in release workflow now checks for all 4 required assets.
- No product feature changes.

## v0.3.5 - 2026-06-08

- Updated Inno Setup installer to accept dynamic version from CI (was hardcoded to v0.2.0).
- Added SetupIconFile for installer executable.
- Fixed build_windows.ps1 to use --onedir mode (was --onefile, inconsistent with release.yml).
- Strengthened CI workflow with compile-check, regression tests, and security audit.
- Added CODEOWNERS file for repository governance.
- Updated release.yml to build and upload Inno Setup installer alongside ZIP.
- Updated README badges to reference unified CI and release workflows.
- Added download counter badge to README.


## v0.3.4 - 2026-06-08

- Fixed post-update check messaging so already-current builds show an up-to-date message instead of a generic connection error.
- Added HTTP status code inspection to distinguish network failures from HTTP errors (403 rate limit, 404 not found, 5xx server errors).
- Applied status-specific user-facing messages for each error type.
- Added structured debug logging of update-check decisions to the updater log.
- Added 11 regression tests covering already-latest, update-available, network-error, HTTP-error, and JSON-error outcomes.

## v0.3.3 - 2026-06-08

- Validation release for the fixed Windows auto-update metadata flow.
- Confirms the intended update path from v0.3.2 to v0.3.3 using canonical GitHub Release assets.
- No PDF feature changes.


## v0.3.2 - 2026-06-05

- Fixed Windows auto-update downloads losing release asset metadata and saving as `update_None`.
- Bound updater download metadata directly to each `QNetworkReply`.
- Saved Windows updater downloads using the canonical `PDFReader-by-Sparsh-Windows.zip` filename.
- Added diagnostic updater logging in `%TEMP%\PDFReader-Updates\updater-debug.log`.
- Added regression checks for updater asset selection, metadata validation, and Windows ZIP routing.

## v0.3.1 - 2026-06-05

- Added tag-driven GitHub Release publishing workflow with canonical updater asset names.
- Updated updater platform asset selection to use exact release asset filenames.
- Documented release/versioning, updater discovery, validation checklist, and agent maintenance rules.

## v0.3.0 - 2026-05-31

- **Workspace session restoration.** Saves open PDF paths and page numbers on close. Restores on next launch (prompt or auto via File menu toggle).
- **Full-library indexed search.** SQLite FTS5 index over entire folders of PDFs. Library dialog (View → Library Search / Ctrl+Shift+F) shows tracked folders, full-text search across all indexed docs with ranked results.
- **PDF version comparison.** Side-by-side diff of two PDFs (Tools → Compare PDFs). Uses difflib for text-level differencing. Color-coded: red for deletions, green for insertions, strikethrough for replacements.
- **Offline semantic search.** TF-IDF cosine similarity index (no external ML dependencies). Toggle "Semantic" checkbox in the search bar for meaning-based matching across indexed library.
- **New toolbar buttons:** Compare, Library, Semantic toggle.
- **Modular refactor.** Core library and comparison logic extracted to `pdfreader_lib/search_index.py` and `pdfreader_lib/comparison.py`.
- **Auto-update fix.** Added retry logic and logging to Windows ZIP updater (log file, 3 retries, 2s post-exit delay).
- **Screenshots updated** to show v0.3.0 UI with tabs, annotations, dark mode.

## v0.2.0 - 2026-05-31

- **Highlight and annotation tools.** Drag-select text and apply highlight, underline, or strikethrough. Sticky notes via click-to-place mode. All saved as native PDF annotations (not overlays). Colors: yellow highlight, blue underline, red strikethrough.
- **Annotation auto-save.** Incremental PDF save after each annotation — no manual save needed.
- **Annotation management.** Delete annotations per-page or per-document via Tools → Annotations menu. View → Show Annotations toggle to render/hide.
- **Windows installer.** Inno Setup script at `installer/setup.iss` with `.pdf` file association, Start Menu entry, and desktop shortcut.
- **Per-platform OCR guide.** Windows, macOS, and Linux Tesseract installation instructions in the README.
- **Features table expanded.** New rows for multi-tab, annotations, dark mode, recent files, auto-update, installer.
- **Repo description updated.** Reflects all current capabilities.

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
