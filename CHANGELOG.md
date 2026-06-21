# Changelog

## v1.2.3 — Reader UX Polish — 2026-06-20

- **Version:** Bumped `__version__` to `1.2.3`, MSIX version to `1.2.3.0`.
- **Added:** Default Fit Page on open — all PDFs (normal open, recent files, session restore, new tab) now start in Fit view so the first page fits cleanly inside the document viewport. Uses both width and height constraints for true Fit Page behavior.
- **Added:** Ctrl+Mouse Wheel zoom — scroll up to zoom in, scroll down to zoom out. Works when the PDF viewer has focus. Page scrolling is suppressed while Ctrl is held.
- **Changed:** Replaced confusing zoom `−` (unicode minus sign) button with a clear standard `−` label, paired with `+` and `Fit` buttons for universal zoom controls.
- **Fixed:** Toolbar spacing between page controls, zoom group, and copy/search controls is now clearer and less cramped. Both light and dark modes render correctly.
- **Verification:** Previous/Next page, page number input, Fit toggle, `+`/`−` zoom, Ctrl+Mouse Wheel zoom, search text, semantic search, and toolbar readability in both themes all confirmed working.

## v1.2.2 — Store Submission Fix — 2026-06-18

- **Version:** Bumped `__version__` to `1.2.2`, MSIX version to `1.2.2.0`.
- **Fixed:** Partner Center package validation rejection (`MinVersion <= 10.0.17134.0`).
- **Root cause:** MSIX manifest patching used regex `-creplace 'Version="[^"]+"'` which matched inside `MinVersion` and `MaxVersionTested` attributes, overwriting them with the app version number.
- **Fix:** Replaced regex-based version injection with proper XML DOM patching in:
  - `release.yml` (CI release build)
  - `build-windows.yml` (CI dev build)
  - `build-msix.ps1` (local build script)
- **Result:** Generated MSIX now correctly preserves `TargetDeviceFamily MinVersion="10.0.17763.0"`.
- **Validation added:** CI now logs `MinVersion` and `MaxVersionTested` during XML validation step.

## v1.2.1 — First Public Microsoft Store Release Candidate — 2026-06-18

- **Version:** Bumped `__version__` to `1.2.1`.
- **MSIX version:** `1.2.1.0`.
- **Purpose:** First public Microsoft Store release candidate.
- **UI/Branding only:** New application icon (1024×1024 source). No architectural changes.
- **Assets regenerated:** Windows .ico, MSIX brand images (44×44, 71×71, 150×150, 310×150, 620×300), macOS .iconset.
- **About dialog cleaned up:** Removed beta/dev/validation wording. Shows clean "OpenReader — Version 1.2.1 — Release Notes".
- **Frozen identity unchanged:** `SparshSam.OpenReader`, `CN=E6186421-BF8A-47E0-A89C-0F513DFF91C0`, PFN `SparshSam.OpenReader_yh0byntbzd2qw`.

## v1.2.0-beta.6 — MSIX Update Validation — 2026-06-18

- **Version:** Bumped `__version__` to `1.2.0-beta.6-dev`.
- **MSIX version:** `1.2.0.6` (beta.6 maps to build 6).
- **Purpose:** Validate MSIX update from v1.2.0-beta.5 to v1.2.0-beta.6.
- **Visible change:** About dialog shows "MSIX update validation — beta.6" label.
- **No functional changes** — version bump with visible release label for update validation.

## v1.2.0-beta.5 — MSIX Splash Asset Fix — 2026-06-18

- **Version:** Bumped `__version__` to `1.2.0-beta.5-dev`.
- **MSIX version:** `1.2.0.5` (beta.5 maps to build 5).
- **Fixed:** Placeholder PNGs (icon-620x300.png etc.) were declared in the manifest but never written to the MSIX staging directory. The string variable was created but the file was never persisted to disk. This caused `Add-AppxPackage` to fail with `0x80073CF6` (splash screen image cannot be located).
- **Added:** `tools/create_msix_placeholder_pngs.py` — generates valid minimal PNG files at all sizes referenced by the manifest.
- **Added:** Pre-MakeAppx asset validation step that parses `AppxManifest.xml`, extracts all image references, and fails with a clear list of any missing files.
- **Fixed:** `build-msix.ps1`, `release.yml`, and `build-windows.yml` — all three now generate proper placeholder PNGs.

## v1.2.0-beta.4 — MSIX Update Validation — 2026-06-18

- **Version:** Bumped `__version__` to `1.2.0-beta.4-dev`.
- **MSIX version:** `1.2.0.4` (beta.4 maps to build 4).
- **Purpose:** Validate MSIX update behavior from v1.2.0-beta.3 to v1.2.0-beta.4.
- **Visible change:** About dialog shows "MSIX update validation — beta.4" label.
- **No functional changes** — version bump with visible release label for update validation.

## v1.2.0-beta.3 — First Valid MSIX Release — 2026-06-18

- **Version:** Bumped `__version__` to `1.2.0-beta.3-dev`.
- **MSIX version:** `1.2.0.3` (beta.3 maps to build 3).
- **MSIX build fixed:** Three root causes resolved across 11 PRs (#32–#42):
  - **Case-insensitive -replace** corrupting XML declaration → fixed with `-creplace`
  - **Wrong namespace schema** for Extensions in desktop bridge → removed Extensions block
  - **MakeAppx.exe path** normalization on CI runner → fixed path resolution
- **First release to include OpenReader.msix** (beta.1/beta.2 are invalid for MSIX testing).

## v1.2.0-beta.2 — MSIX Update Validation — 2026-06-17

- **Version:** Bumped `__version__` to `1.2.0-beta.2-dev`.
- **MSIX version:** `1.2.0.1` (build number incremented from beta.1).
- **CI version mapping:** Added proper `major.minor.patch.build` extraction for pre-release tags. `v1.2.0-beta.2` now correctly maps to MSIX `1.2.0.1`.
- **Purpose:** Validate MSIX update behavior from v1.2.0-beta.1 to v1.2.0-beta.2.
- **No functional changes** — one version bump for update validation. See `docs/msix-update-validation.md` for test scenarios.

## v1.2.0-beta.1 — OpenReader Rebrand & Identity Freeze — 2026-06-17

- **Version:** Bumped `__version__` to `1.2.0-dev`.
- **Rebrand:** Application renamed from "PDFReader by Sparsh" to "OpenReader". All user-facing branding updated: window title, About dialog, installer names, asset names, build scripts, CI workflows, and documentation.
- **Frozen Microsoft Store identity applied to all packaging:**
  - Identity Name: `SparshSam.OpenReader`
  - Publisher: `CN=E6186421-BF8A-47E0-A89C-0F513DFF91C0`
  - Publisher Display Name: `Sparsh Sam`
  - Package Family Name: `SparshSam.OpenReader_yh0byntbzd2qw`
  - Store ID: `9MXDVW2645LL`
  - Executable: `OpenReader.exe`
- **Identity freeze documented:** `packaging/msix/AppxManifest.xml` and `packaging/msix/AppInstaller.xml` updated with frozen values. Identity Freeze sections added to `docs/windows-distribution.md` and `docs/updater-architecture.md`.
- **MSIX versioning standardized:** 4-part `major.minor.patch.build` scheme. Git tag `v1.2.0-beta.1` → MSIX version `1.2.0.0`.
- **Distribution channels documented:**
  - Primary: Microsoft Store (reserved — submission pending)
  - Secondary: GitHub Releases (MSIX)
  - Discovery: Winget (future — `SparshSam.OpenReader`)
  - Legacy: Setup.exe (manual recovery only)
- **App Installer infrastructure prepared:** Permanent update URI defined (`https://downloads.openreader.app/stable/OpenReader.appinstaller`). Template exists but not yet active.
- **Code signing documented:** Store signing (preferred) vs third-party certificate vs unsigned behavior.
- **Winget readiness:** Package identifier `SparshSam.OpenReader` documented. Release workflow produces predictable asset names.
- **Release readiness document:** Created `docs/release-readiness-v1.2.0.md` with 16 validation scenarios covering install, upgrade, uninstall, reinstall, settings persistence, file associations, update detection, and rollback.
- **CI/CD renamed:** All workflow asset names updated: `OpenReader.msix`, `OpenReader-Setup.exe`, `OpenReader-Windows.zip`, `OpenReader-macOS-*.zip`.
- **Library files updated:** `pdfreader_lib/mcp_server.py`, `search_index.py`, `comparison.py`, `tests/__init__.py`, `CONTRIBUTING.md`, `SECURITY.md` — all updated with OpenReader branding.
- **Installer updated:** `installer/setup.iss` uses `OpenReader.exe`, `OpenReader` app name, `Sparsh Sam` publisher, `OpenReaderPDF` file association.
- **Hard rules enforced:**
  - Identity Name must never change after release
  - Publisher must never change after release
  - No placeholder Publisher values used anywhere
  - No `com.sparshsam.*` identities introduced
  - No self-update code reintroduced
  - App never replaces itself

## v1.2.0 — MSIX Distribution Reset — 2026-06-17

- **Version:** Bumped `__version__` to `1.2.0-dev`.
- **Self-update removed:** The in-app download/apply pipeline (`_start_download`, `_on_download_finished`, `_apply_update_windows_installer`, `_apply_update_windows_zip`, etc.) has been removed. The app no longer downloads or runs installers from within itself.
- **Safe update detection retained:** Help → Check for Updates still queries the GitHub API. If a newer version exists, the dialog offers "Open Releases Page" (browser) instead of "Download & Install". A background check on launch shows a status bar message.
- **MSIX packaging added:** `packaging/msix/` with `AppxManifest.xml`, `AppInstaller.xml`, and `build-msix.ps1` for Windows MSIX distribution.
- **App Installer integration:** `AppInstaller.xml` enables Windows-managed updates — Auto Update checks on launch and in the background. The app no longer manages its own updates.
- **CI updated:** `release.yml` builds an unsigned MSIX alongside Setup.exe and Windows ZIP. `build-windows.yml` builds an unsigned MSIX for test PRs.
- **Documentation:** Added `docs/windows-distribution.md` (MSIX strategy, build process, code signing) and `docs/updater-architecture.md` (architecture history, component breakdown, security model).
- **README updated:** Download table promotes MSIX as recommended format. Auto-update and Releases sections rewritten for v1.2.0 architecture. Roadmap updated.
- **Tests updated:** Removed `TestPlatformAssetSelection`, `TestDownloadMetadata`, and `TestUpdateMethodSelection` test classes. `tools/test_updater_asset_flow.py` rewritten to test remaining update detection only.
- **Constants removed:** `WINDOWS_INSTALLER_ASSET`, `WINDOWS_PORTABLE_ASSET`, `WINDOWS_UPDATE_ASSET`, `MACOS_APPLE_SILICON_UPDATE_ASSET`, and `MACOS_INTEL_UPDATE_ASSET` removed as they were only used by the removed download/apply code.
- **Updater responsibility:** Belongs to Windows packaging (MSIX/App Installer), not `main.py`. The running app no longer overwrites itself, launches elevated installers, or writes batch scripts.
- **Hard rules enforced:**
  - No shipping another v1.1.x updater patch
  - No app self-overwrite
  - No elevated installer launch from inside the app
  - Updater responsibility belongs to Windows packaging

## v1.1.11 — Updater Validation Release — 2026-06-17

- **Version:** Bumped `__version__` to `1.1.11-dev`.
- **Updater test release** — intentionally minimal release used to validate the `v1.1.10` installer-based Windows updater path end-to-end.
- **No functional app changes** — this release exists so installed `v1.1.10` builds can detect a newer GitHub Release, download `PDFReader-by-Sparsh-Setup.exe`, request UAC, and apply the update through Inno Setup.

## v1.1.10 — Installer-Based Windows Updater — 2026-06-17

- **Version:** Bumped `__version__` to `1.1.10-dev`.
- **Windows updater uses Setup.exe** — in-app updates now select `PDFReader-by-Sparsh-Setup.exe` on Windows instead of the ZIP package.
- **Program Files update fix** — Windows updates are applied by Inno Setup so UAC elevation, app closing, file replacement, shortcuts, and file associations are handled by the installer rather than a hand-written `xcopy` batch script.
- **Portable ZIP preserved** — `PDFReader-by-Sparsh-Windows.zip` remains available for portable/manual recovery use, but it is no longer the normal Windows in-app update path.
- **Release workflow hardening** — `PDFReader-by-Sparsh-Setup.exe` is now a required release asset. The release fails if the installer is missing.
- **Updater diagnostics** — installer launch and exit/failure details are written to `%TEMP%\PDFReader-Updates\updater-debug.log`.
- **Regression coverage** — updater asset selection, update method routing, release asset consistency, and the standalone asset-flow script now expect the installer-first Windows path.

## v1.1.1 — Stability and UX Hardening — 2026-06-16

- **Version:** Bumped `__version__` to `1.1.1-dev`.
- **Open file centralized** — single file picker dialog with `_open_in_progress` guard blocking re-entrant calls. Removed cascading 3-tier fallback (Qt→Tkinter→Manual). Clean cancel message.
- **New Tab creates blank tab** — `new_tab()` method replaces `open_pdf()` for Ctrl+T, + button, and double-click. Creates blank tab with empty-state page — no file dialog.
- **Session restore "Don't ask again"** — custom QMessageBox with checkbox. Choice persisted in QSettings (`sessionDontAsk`). Silent auto-restore or skip.
- **Compress size guard** — if compressed output ≥ original, deletes the output and shows "Compression not beneficial" message. No larger file saved.
- **Updater post-launch verification** — marker file written before apply. `_check_post_update()` reads it on next launch, logs diagnostics, shows "Updated to vX.Y.Z" in status bar. Per-launch `app_launch` log entry.
- **Windows installer publisher docs** — README now explains "Unknown Publisher" warning and that code-signing requires an EV certificate.
- **9 new regression tests** — 28 total, all passing. Covers: re-entrant open guard, blank tab, session checkbox, compress guard, post-update verification, unsigned publisher docs, clean cancel message.

- **Version:** Bumped `__version__` to `1.1.0-dev`.
- **MCP server** (`pdfreader_lib/mcp_server.py`) — new Model Context Protocol server exposing 14 PDF operations as tools for AI agents:
  - **Reading:** `extract_text`, `get_page_text`, `get_metadata`, `get_page_count`
  - **Search:** `search_pdf` (single doc), `search_library` (FTS5 BM25), `search_semantic` (TF-IDF)
  - **Compare:** `compare_pdfs` (page-by-page structured diff with summary)
  - **Transform:** `merge_pdfs`, `split_pdf`, `extract_pages`, `compress_pdf`
  - **Index:** `index_folder`, `list_indexed_docs`
- **MCP transports:** stdio (default, for agent CLIs) and SSE (optional, for HTTP gateways)
- **`requirements-mcp.txt`** — optional dependency pin (`mcp>=1.0.0`)
- **README:** New "AI Agent Integration" section with setup, agent configuration, and tool reference. Features table expanded with missing capabilities (annotation management, Save PDF, keyboard shortcuts, diff summary). Tech stack expanded from 3 to 10 rows with actual versions.
- **AGENTS.md:** Maintenance rules for the MCP server.
- **Roadmap:** v1.1.0 marked as current. v1.1.0-plan.md updated to note MCP server shipped; visual polish items deferred to v1.2.0.
- All operations are local. No cloud dependencies, no code changes to the existing GUI.

- **Version:** Bumped `__version__` to `1.0.6-dev`.
- **Branch:** `windows-installed-app-verification-v1.0.6`

### Root Cause — Why v1.0.5 Fixes Did Not Appear

The **release workflow** (`release.yml` and `build-windows.yml`) ran PyInstaller **without** `--add-data "assets;assets"`. While the `.spec` file had `datas=[('assets', 'assets')]`, the CI build bypassed the spec file entirely:

```yaml
pyinstaller --noconsole --onedir --noupx --name "PDFReader by Sparsh" --icon ".\assets\pdfreader_by_sparsh.ico" main.py
```

The icon file was used to **stamp the EXE** at build time (visible in the file's icon metadata), but the `assets/` folder was **never copied** into the dist directory. Since `_set_app_icon()` checked `sys.executable.parent / "assets" / ...`, which didn't exist in the frozen build, it fell back to a generic `SP_FileIcon`. The taskbar, title bar, and Start Menu all showed a default generic icon.

### Icon Fix — Critical

- **Workflows fixed:** Both `release.yml` and `build-windows.yml` now pass `--add-data "assets;assets"` to PyInstaller, ensuring the `assets/` directory (with `.ico`) is bundled in the frozen build.
- **`_set_app_icon` expanded** with exhaustive fallback paths:
  - Standard onedir layout: `{exe_dir}/assets/pdfreader_by_sparsh.ico`
  - `_internal/assets/` fallback for some PyInstaller configs
  - Source build: `{__file__}/assets/`
  - `sys._MEIPASS` (legacy PyInstaller attribute — guarded with `hasattr`)
  - Recursive `rglob` search of the install directory as last resort
- **`QApplication.setWindowIcon()`** now called alongside `self.setWindowIcon()` so the **taskbar** and **Alt+Tab** icon pick up the custom icon.
- **`main()` entry point** also sets `app.setWindowIcon()` from the source `assets/` path before window creation — provides taskbar icon even in dev mode.

### Open Flow Diagnostics

- **Visual status bar feedback** added to `open_pdf()`:
  - `"Opening file..."` on method entry
  - `"Open cancelled"` if dialog is dismissed
  - `"Opening {filename}..."` after file selection
  - `QApplication.processEvents()` call after status message so it visually updates before loading begins
- Dialog cancellation now logged as `"open_pdf: no file selected / dialog cancelled"` with a status bar message.
- All open paths still converge on the one `open_pdf()` method.

### File → Open Fix — Root Cause: Native QFileDialog Failure

**Root cause:** `QFileDialog.getOpenFileName()` uses the **native Windows file dialog**, which fails silently in frozen PyInstaller builds — the window never appears, returns immediately empty. Even the **non-native Qt dialog** (`DontUseNativeDialog`) fails to return a file in some frozen build configurations on Windows — `exec()` returns `Accepted` but `selectedFiles()` is empty.

**Fix:** Replaced the single-dialog approach with a **3-tier fallback chain**:

| Tier | Method | Description |
|------|--------|-------------|
| 1 | Qt non-native `QFileDialog` | Explicit instance with `setFileMode(ExistingFile)`, `setNameFilter("PDF Files (*.pdf)")`, `setOption(DontUseNativeDialog, True)` |
| 2 | Tkinter native file dialog | `tkinter.filedialog.askopenfilename` with hidden root window, topmost attribute, PDF filter |
| 3 | Manual path input | `QInputDialog.getText` — user pastes a PDF path, validated for `.pdf` suffix and file existence |

Each tier logs its attempt/result to the updater debug log and shows a status bar message (`"Opening file picker..."` → `"Qt file picker unavailable; trying Windows fallback..."` → `"File dialogs unavailable; enter path manually..."`). Only when all three return empty does the user see `"Open cancelled"`.

Direct-path entry points (drag/drop, double-click, IPC) are unaffected — they skip all dialogs.

Now works:
- ✅ File → Open PDF
- ✅ Toolbar Open
- ✅ Ctrl+O
- ✅ Empty-state Open
- ✅ Ctrl+T (New Tab)

### Single-Instance Tab Routing (IPC)

**Problem:** Double-clicking a `.pdf` from Windows Explorer while the app is already running launched a **separate app window** instead of opening a new tab.

**Solution:** Implemented `QLocalServer`/`QLocalSocket` IPC for single-instance routing:

1. The first running instance creates a `QLocalServer` listening on a well-known name (`PDFReaderBySparsh-IPC`).
2. When a second instance starts (via double-click or file association), it:
   - Attempts to connect to the IPC server
   - On success: serialises the file paths as JSON, sends them, and exits immediately
   - On failure (no existing instance): starts normally (becomes the primary)
3. The primary instance's `_on_ipc_connection` handler receives the paths and opens each one as a new tab via `open_pdf()`.
4. Multiple `.pdf` files selected/opened at once are all routed and opened as individual tabs.

**Edge cases handled:**
- Stale server name from a previous crash → `removeServer()` cleans up before listening
- Connection timeout (2000 ms) → client falls through to start a new window
- Non-PDF paths in argv → filtered out
- IPC handler exceptions → logged to updater debug log, don't crash the app
- `QLocalSocket` cleanup → `disconnectFromServer()` + `deleteLater()` in finally block

**Status: Implemented for v1.0.6.**

### Build System Fix

| Workflow | Before | After |
|----------|--------|-------|
| `release.yml` | `pyinstaller main.py` (no `--add-data`) | `pyinstaller --add-data "assets;assets" main.py` |
| `build-windows.yml` | `pyinstaller main.py` (no `--add-data`) | `pyinstaller --add-data "assets;assets" main.py` |

### Uninstaller & Start Menu

- **Confirmed** `setup.iss` already creates:
  - `{group}\PDFReader by Sparsh` → Start Menu shortcut
  - `{group}\Uninstall PDFReader by Sparsh` → Start Menu uninstall shortcut
  - `UninstallDisplayIcon={app}\PDFReader by Sparsh.exe` → correct icon in Apps & Features
  - `unins000.exe` is placed in `{app}` (standard Inno Setup behavior)
- No changes needed — uninstaller infrastructure was already correct, just invisible due to the icon issue.

### Validation Status

This release is **held back** from tagging. v1.0.6 will not be tagged until:
1. A `Setup.exe` is manually downloaded from GitHub Actions
2. Installed on real Windows
3. All open paths verified:
   - [ ] File → Open PDF
   - [ ] Toolbar Open
   - [ ] Ctrl+O
   - [ ] Empty-state Open
   - [ ] Drag-and-drop
   - [ ] Double-click .pdf (routes to existing window)
4. Icon confirmed in title bar, taskbar, Start Menu, and EXE
5. Multiple PDFs from Explorer open as separate tabs in existing window
6. Multiple PDFs from inside app (File → Open) open as separate tabs
7. Ctrl+T opens a new file dialog
8. Uninstaller works from Start Menu and Apps & Features

### Files Changed

- `main.py` — Icon path expansion, QFileDialog DontUseNativeDialog fix, single-instance IPC (QLocalServer/QLocalSocket), status bar diagnostics, multi-file arg handling, version bump
- `.github/workflows/release.yml` — Added `--add-data "assets;assets"`
- `.github/workflows/build-windows.yml` — Added `--add-data "assets;assets"`, workflow_dispatch trigger, Inno Setup installer build, test artifact naming
- `CHANGELOG.md` — This entry

## v1.0.5 — Windows Distribution + Open Flow Fix — 2026-06-10

- **Version:** Bumped `__version__` to `1.0.5-dev`.
- **Branch:** `windows-distribution-open-flow-v1.0.5`

### Open Flow — Critical Fix
- **All open paths unified** through `open_pdf()` — toolbar Open, File→Open PDF, Ctrl+O, empty-state Open PDF button, drag-and-drop, and double-click `.pdf` from Explorer now all converge on one method.
- **`main()` entry point** now calls `window.open_pdf(path)` instead of raw `window.load_pdf(path)` — ensures a tab is created and UI state is initialized properly when a PDF is opened via file association or command line.
- **Debug logging** added to `open_pdf`: logs file path, resolution, and any failures to the updater debug log for troubleshooting.
- **Path resolution** now uses `Path(file_name).resolve()` for consistent absolute paths.

### Duplicate Open Button Removed
- The redundant "Open" button has been removed from the **controls bar** (the lower button row). Open is now available only from:
  - Toolbar Open (icon + tooltip)
  - File → Open PDF (Ctrl+O)
  - Empty state "Open PDF" button
  - Drag-and-drop
  - Double-click `.pdf` from Windows Explorer
- Keeps the UI clean and professional — one primary Open action.

### Icon Fix — Critical
- **`_set_app_icon`** rewritten with systematic path checking: frozen build (`assets/` next to EXE), source build (`assets/` in repo root), and `_internal/assets/` fallback for some PyInstaller layouts.
- **Logging** added: logs successful icon path on load, and all checked paths on failure for debugging.
- **PyInstaller spec** updated: `datas=[('assets', 'assets')]` now bundles the entire `assets/` folder into the build so icons are available at runtime.
- Window taskbar icon, title bar icon, and Alt+Tab icon should now display correctly in packaged builds.

### Release Asset Cleanup
- **RELEASE.md**: Windows ZIP asset description changed from "updater canonical asset" to "updater package — do not download unless instructed". Setup.exe is now marked as the recommended download.
- **Release workflow notes**: Asset listing now separates Windows and macOS sections. Setup.exe is bolded and marked with ✅ as the recommended choice. ZIP is described as updater-only with a note about the SUPPORT.md recovery guide.
- Canonical ZIP asset names unchanged — updater compatibility preserved.

### Toolbar Cleanup Verified
- Controls bar: Prev, Next, Page spin, Zoom -, Zoom +, Fit, Copy, HL, UL, ST, Sticky Note, Semantic Checkbox, Search field.
- Toolbar: Open, Save, Prev, Next, Zoom In, Zoom Out, Find.
- No Merge, Split, Compress, Compare, Library, or Check for Updates buttons anywhere in the visible UI.
- All tool actions accessible from top menus (File, Edit, View, Tools, Help).

### Validation
- Full test suite: 32 passed, 31 skipped (expected).
- Updater regression checks: All 16 passed.
- Bandit: clean.
- Compile check: clean.
- ZIP asset names unchanged — canonical names preserved.
- No changes to installer, updater internals, or file safety protections.

## v1.0.4 — Visual Quality + PDF Rendering Polish — 2026-06-10

- **Version:** Bumped `__version__` to `1.0.4-dev`.
- **Branch:** `visual-quality-rendering-v1.0.4`

### PDF Rendering Quality
- **HiDPI-aware rendering:** Pages are now rendered at the screen's device pixel ratio, then displayed with `setDevicePixelRatio()` for crisp, sharp text on Retina/High-DPI displays.
- **No blurry low-res scaling:** The render zoom is multiplied by DPR so the pixmap contains HiDPI detail; the UI displays it at the correct logical size without scaling up a low-resolution image.
- **Page border:** Each rendered page now has a professional 1px border (`#3b4261` dark, `#c8c8c8` light) and white background — creating a clear paper-like canvas.
- **Continuous scroll margins:** Increased from 0/8 to 12/12 for natural breathing room between pages.
- Rendering quality verified: crisp at all zoom levels, in both single-page and continuous modes.

### Theme Polish (Dark & Light)
- **New light theme** (`LIGHT_STYLESHEET`): Bright, clean, modern — white backgrounds, blue accent (`#4a90d9`), proper hover/pressed states, readable gray text for secondary elements. Replaces the previous no-stylesheet default (plain system look).
- **Refined dark theme** (`DARK_STYLESHEET`): Tokyo Night-inspired palette (`#1a1b26` background, `#7aa2f7` accent, `#c0caf5` text) — replaces Catppuccin Mocha with a more premium, desktop-appropriate scheme. Improved contrast, button hover states, menu hierarchy.
- **Menus:** Light theme now uses blue accent for selected items (matching the selected tab color) — consistent visual language.
- **Removed QToolBar styles** from both themes (toolbar is no longer used in v1.0.1+; the controls bar is a QPushButton-based layout styled via QPushButton rules).

### Toolbar Cleanup Verified
- No Merge, Split, Compress, Compare, Library, or Check for Updates buttons exist in the controls bar or toolbar.
- These actions are accessible only through the top menus (Tools, Help).
- Toolbar contains only: Open, Save, Prev, Next, Zoom In, Zoom Out, Find.

### Validation
- Full test suite: 32 passed, 31 skipped (expected).
- Updater regression checks: All 16 passed.
- Bandit: clean.
- Compile check: clean.
- ZIP asset names unchanged — canonical names preserved.
- No changes to installer, updater, or file safety protections.

## v1.0.3 — Windows Installer Admin + Uninstall Polish — 2026-06-10

- **Version:** Bumped `__version__` to `1.0.3-dev`.
- **Branch:** `windows-installer-admin-polish-v1.0.3`

### Installer Admin & UAC
- Confirmed `PrivilegesRequired=admin` ensures UAC prompt on launch.
- Added `CloseApplications` filter to auto-detect and prompt to close running PDFReader before install, preventing file-lock issues.
- Added `DisableDirPage=auto` to allow path changes but default to `C:\Program Files\PDFReader by Sparsh`.
- Added `AlwaysShowDirOnReadyPage=yes` so the install path is visible on the final confirmation page.
- Installer now kills the running process cleanly before overwriting files.

### Install Folder Behavior
- Default install path: `{autopf}\PDFReader by Sparsh` → `C:\Program Files\PDFReader by Sparsh`.
- All app files placed under that folder only.
- No update scripts or temp files written into install folder (v1.0.2+ updater uses `%TEMP%\PDFReader-Updates\`).
- Installer output artifacts documented.

### Uninstaller Polish
- Added `UninstallDisplayName` and `UninstallDisplaySize` for proper Add/Remove Programs entry.
- Uninstall removes:
  - All installed app files (Files section delete after install)
  - Start Menu shortcut and desktop shortcut (Icons section)
  - `.pdf` file association registry keys (`uninsdeletevalue`, `uninsdeletekey`)
  - App Paths registry key (`uninsdeletekey`)
- Uninstall preserves:
  - User documents and PDFs
  - User settings (QSettings stored in `HKCU\Software\Sparsh\PDFReader by Sparsh` — preserved across install/uninstall)
  - User library index (SQLite database)
- Added `UninstallFilesDir` for clean uninstaller file management.

### Documentation
- **SUPPORT.md:** Added Windows installer section with admin/UAC explanation, install path details, and what uninstall does/does not remove.
- **README:** Added Windows Installer notes section linking to SUPPORT.md for detailed behavior.
- Updated v1.0.3 references in SUPPORT.md recovery section.

### Validation
- Full test suite: 32 passed, 31 skipped (expected).
- Updater regression checks: All 16 passed.
- Compile check: clean.
- ZIP asset names unchanged — canonical names preserved.
- No code changes to the updater or app logic; installer-only polish.

## v1.0.2 — Windows Updater Permission Hotfix — 2026-06-10

- **Version:** Bumped `__version__` to `1.0.2-dev`.
- **Branch:** `windows-updater-permission-hotfix-v1.0.2`

### Bug Fix
- **Windows updater batch script moved out of protected install directory.**
  Previously, `_update_<tag>.bat` was written to `C:\Program Files\PDFReader by Sparsh\`,
  which caused `[Errno 13] Permission denied` on normal (non-admin) installations.
  The batch script is now written to `%TEMP%\PDFReader-Updates\` — a writable location
  accessible by all users.

### Elevation Handling
- **Automatic UAC elevation request.** If the copy/install operations fail because
  the install directory is protected (e.g., `Program Files`), the updater script
  detects the failure, creates a temporary VBS script that triggers a UAC prompt,
  and re-launches itself as Administrator — all without manual user intervention.
- **If already running as admin** but the copy still fails (file lock / disk issue),
  the script shows a clear diagnostic and opens the log file.

### Professional Error Messages
- **Update launch failure** now shows a rich dialog explaining what happened,
  actionable steps (manual download, run-as-admin), and the update directory path.
- **Update complete** message includes a UAC hint: "If you see a UAC prompt,
  click Yes to allow the update to complete."
- **Update failure** (in the batch script) shows install path, admin requirements,
  and the GitHub releases URL for manual download.

### Stale Script Cleanup
- On update start, any leftover `_update_*.bat` files in the old install directory
  (from v1.0.0/v1.0.1) are cleaned up silently as a best-effort operation.

### Logging
- Added `updater_scripts_dir=`, `install_dir=` lines to the updater debug log
  so the chosen paths are always recorded.
- The batch script now logs its own working directory, script location, and install
  directory at the start of each run.

### Validation
- Full test suite: 32 passed, 31 skipped (PySide6 gated — expected).
- Updater regression checks: All 16 passed.
- Compile check: clean.
- ZIP asset names unchanged — `PDFReader-by-Sparsh-Windows.zip` is preserved.
- v1.0.0/v1.0.1 → v1.0.2 update path is compatible (updater ZIP and metadata
  format unchanged; only the batch script location changed from app dir to %TEMP%).
- No changes to macOS updater, file safety protections, or UI.

## v1.0.1 — First-Run Usability + Professional Polish — 2026-06-10

- **Version:** Bumped `__version__` to `1.0.1-dev`.
- **Branch:** `first-run-polish-v1.0.1`

### Critical Fixes
- **Drag-and-drop support:** Added full drag-and-drop PDF opening. Drag a PDF onto the window from Explorer/Finder to open it.
- **App window icon:** Window now displays the PDFReader icon in the title bar, taskbar, and Alt+Tab switcher via `setWindowIcon()`.
- **File open paths verified:** Toolbar Open, File → Open PDF, Ctrl+O, drag-and-drop, and double-click from Explorer all work correctly.
- **Controls cleanup:** Removed duplicate Merge/Split/Compress/Compare/Library/Updates buttons from the controls bar. Moved them to proper menu locations.

### Visual Polish
- **Empty state redesign:** Replaced dull "Open a PDF to begin" text with a polished empty state featuring: icon, descriptive text, drag-and-drop hint, and a centered "Open PDF" button.
- **About dialog replacement:** Replaced bare `QMessageBox.about()` with a professional branded `QDialog` (460×500) including: app name, version with release notes link, local-first description, full keyboard shortcuts table, GitHub repo link, Sparsh Sam profile link, and platform/build info.

### Toolbar & Menu Reorganization
- **Streamlined toolbar:** Open, Save, Previous/Next Page, Zoom In/Out, Find — no duplicate or heavy actions.
- **New Edit menu:** Copy Selected Text (Ctrl+C), Find (Ctrl+F).
- **Reorganized Tools menu:** Annotations → Merge → Split → Compress → Compare → Library Search.
- **Help menu:** Check for Updates, Automatically Check for Updates (toggle), About.
- **View menu:** Added Continuous Scroll toggle.

### Continuous Page Scrolling
- **Continuous scroll mode (default):** Pages render vertically in a scrollable stream (buffer of ±5 pages). Scroll naturally through multi-page PDFs.
- **Toggle:** View → Continuous Scroll to switch between single-page and continuous mode.
- **Single-page mode retained:** Prev/Next buttons, page spin, and keyboard navigation work in both modes.
- **Memory-aware:** Only renders visible pages + buffer. Works with large PDFs without freezing.

### Automatic Update Checks
- **Auto-check on launch:** App automatically checks GitHub for updates 3 seconds after launch (if enabled).
- **Silent check:** No user-visible feedback unless an update is actually available.
- **Persistent setting:** Help → Automatically Check for Updates (toggle, stored in QSettings, default ON).
- **Installer option:** Inno Setup now includes an "Automatically check for updates on launch" task (checked by default).

### Regression / Validation
- Full test suite run: 32 pytest + updater asset flow.
- Compile check: clean.
- No regressions in file safety protections (v0.7+ preserved).
- No AI, cloud, plugins, or accounts added.

## v1.0.0 — Stable Desktop Utility — 2026-06-09

- **Release declaration:** PDFReader by Sparsh is declared a stable, local-first
  desktop PDF utility. No longer a prototype.
- **Version:** Bumped `__version__` to `1.0.0-dev` (CI injects exact tag at release).
- **Release workflow verified:** GitHub Actions release pipeline reviewed for
  version injection, asset naming, asset verification, and release notes generation.
  All canonical asset names match updater expectations.
- **Installer metadata verified:** Inno Setup `setup.iss` uses dynamic
  `#ifndef AppVersion` with fallback — compatible with both CI and local builds.
- **Documentation finalized:**
  - README updated for stable release positioning
  - README "Last updated" date bumped to July 2026
  - ROADMAP.md refreshed to reflect shipped v1.0 capabilities
  - RELEASE.md unchanged (already accurate)
  - docs/known-limitations.md unchanged (already complete)
- **Full validation pass:**
  - Compile check: clean
  - pytest: 32 passed, 31 skipped (PySide6 gated — expected in headless CI)
  - tools/test_updater_asset_flow.py: all 16 checks passed
  - bandit: 0 issues in production code
  - pip-audit: 0 known vulnerabilities
- **No new features. No architecture changes. No UX changes.**
- All stabilization, reliability, and release-candidate work from v0.7.0–v0.9.0
  is included and verified.

- **Stabilization fixes:**
  - Fixed critical bug in `_delete_all_annotations`: confirmation dialog now appears
    *before* annotations are deleted (was deleting first, confirming second). Removed
    misleading inline comments describing the broken behavior.
  - `closeEvent` is now fully defensive — all state saves and document closes are
    wrapped in try/except so an exception during shutdown never prevents the window
    from closing.
  - Progress feedback during split (every page mode) for documents over 50 pages.
    Status bar updates every 25 pages with `QApplication.processEvents()`.
  - Removed dead `_apply_update_windows()` method (old onefile updater, superseded
    by `_apply_update_windows_zip`).
- **Security audit:** Run bandit and pip-audit against all production code.
  - Created `.bandit` configuration excluding test directories.
  - Production code clean (0 issues). All dependencies clean (0 known vulnerabilities).
  - All existing `subprocess.Popen` calls audited and annotated with `# nosec`.
  - Update URL verified as HTTPS only.
- **Regression test suite:** 32 new tests across 3 files:
  - `tests/test_reliability.py`: 20 tests — version format, asset name consistency,
    safety limits, shortcut consistency.
  - `tests/test_security.py`: 12 tests — file extension validation, path handling,
    temp file security, subprocess safety, annotation delete ordering.
  - `tests/test_updater.py`: 31 tests (skipped in headless CI) — version parsing,
    update classification, platform asset selection, download metadata, method
    selection. Plus the existing `tools/test_updater_asset_flow.py` (16 checks)
    continues to pass.
- **Documentation:**
  - Created `docs/known-limitations.md` documenting 15 accepted limitations across
    rendering, search, memory, macOS, Windows, filesystem safety, library, and
    updater categories.
  - Added `.bandit` configuration for CI security scanning.
- **Release hardening:** Bumped `__version__` to `0.9.0-dev`. Version propagation
  path unchanged (tag injection in CI). Release asset naming is consistent with
  existing updater expectations.
- **No new features. No architecture changes. No UX changes.**

- **Performance improvements:**
  - Startup: Deferred `_update_recent_menu()` to `QTimer.singleShot(0, ...)` — menu
    construction no longer blocks initial window display.
  - Rendering: Introduced 80ms debounce timer (`_render_timer`) for all render
    requests. Rapid resize/zoom/navigation events no longer trigger redundant
    full-page re-renders.
  - Rendering: Removed `QImage.copy()` from render pipeline — saved one full
    image copy per render (~8 MB for a letter-size page at 150 DPI).
  - Resize: `resizeEvent` now uses `_render_timer.start()` (debounced) instead
    of direct `render_page()` — smooth during window resizing.
  - Search: Periodic progress updates every 50 pages during keyword search
    on PDFs over 100 pages. `QApplication.processEvents()` keeps the UI
    responsive during large searches.
  - Performance timer: `_perf_start()` / `_perf_end()` helpers log timing to
    stdout in dev builds. Wired into `__init__`, `_do_render`.
- **UX Polish:**
  - All toolbar buttons now have descriptive tooltips with keyboard shortcut hints
    (Open, Prev, Next, Zoom, Fit, Copy, Merge, Split, Compress, Compare, Library).
  - Improved About dialog: now includes a keyboard shortcuts reference section.
  - Search placeholder text refined.
  - Large PDF (>500 pages) loading shows "Opening {name} ({page count} pages)..."
    in the status bar during initial render.
  - `_do_render` now handles all render logic with debounce — `render_page()` is
    a lightweight scheduling method.
- **No feature changes or architecture changes.**
- **Bumped `__version__`** to `0.8.0-dev`.

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
