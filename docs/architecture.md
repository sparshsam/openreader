# Architecture — PDFReader by Sparsh

> **Version:** 0.4.0  
> **Status:** Architecture Hardening — modular extraction from monolithic `main.py`

## Overview

PDFReader by Sparsh is a local-first, cross-platform PDF reader built with
**Python**, **PySide6** (Qt), and **PyMuPDF** (fitz). It provides tabbed
PDF viewing, text search, annotations, PDF manipulation (merge/split/compress),
auto-updating, and an optional library search index.

```
┌─────────────────────────────────────────────────────────────────┐
│                        main.py                                  │
│  PdfReaderWindow (QMainWindow)                                   │
│  PdfPageLabel  _LibraryDialog  _LibrarySearchResultsDialog       │
│  _CompareDialog                                                   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              pdfreader_lib/  (service modules)            │    │
│  │                                                           │    │
│  │  pdf_validator.py  tab_state.py  theme_manager.py         │    │
│  │  pdf_tools.py      updater.py                             │    │
│  │  search_index.py   comparison.py  (existing)              │    │
│  └──────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Module map

### `main.py`
The application entry point. Defines:

- **`PdfReaderWindow`** — `QMainWindow` subclass that composes all services.
  Owns the tab bar, controls bar, search bar, scroll area, status bar.
  Delegates non-UI logic to `pdfreader_lib` modules.
- **`PdfPageLabel`** — `QLabel` subclass that handles mouse-drag text
  selection and sticky-note placement on the rendered page.
- **`_LibraryDialog`** — folder management and full-text search dialog.
- **`_LibrarySearchResultsDialog`** — results list for library search.
- **`_CompareDialog`** — side-by-side PDF diff viewer.

Launch path: `main()` → `QApplication` → `PdfReaderWindow`.

### `pdfreader_lib/__init__.py`
Re-exports the public API of all service modules for convenient
single-line imports.

### `pdfreader_lib/pdf_validator.py`
*Pure functions — no Qt dependency.*

- **`PdfSafetyError`** — custom exception for validation failures.
- **`validate_pdf_path(file_name, max_size_bytes)`** — checks existence,
  extension, size, and PDF magic bytes.
- **`validate_document_pages(document, max_page_dimension)`** — verifies
  each page has sensible bounds.
- **`safe_open_pdf(file_name, ...)`** — combines path validation, document
  opening, and page validation in one call.

### `pdfreader_lib/tab_state.py`
*Pure data — no Qt dependency.*

- **`TabData`** — `@dataclass` holding all per-tab state: document ref,
  path, current page, zoom, search state, selection, OCR cache.

### `pdfreader_lib/theme_manager.py`
- **`ThemeManager`** — encapsulates theme selection logic (auto/light/dark)
  and applies the Catppuccin-based `DARK_STYLESHEET` to a `QWidget`.
- **`DARK_STYLESHEET`** — the full dark-mode Qt stylesheet string.
- **`THEME_AUTO` / `THEME_LIGHT` / `THEME_DARK`** — constants.

### `pdfreader_lib/pdf_tools.py`
*Pure document-processing functions — no Qt dependency.*

- **`merge_pdfs(file_names, output_path)`** — combines multiple PDFs.
- **`split_every_page(document, ...)`** — one PDF per page.
- **`extract_pages(document, ...)`** — selected page range to a file.
- **`parse_page_ranges(text, page_count)`** — user string to page indices.
- **`compress_pdf(source_path, output_path)`** — re-save with max compression.

### `pdfreader_lib/updater.py`
*QObject-based service.*

- **`PdfUpdater`** — manages the full update lifecycle:
  `check_for_updates` → `_on_update_check_reply` → `_start_download` →
  `_on_download_finished` → `_apply_update`.
- **`parse_version(tag)`** — extracts `(major, minor, patch)` from tag.
- **`select_update_apply_method(system, ...)`** — determines the right
  updater for the platform + asset combo.
- **`validate_download_metadata(...)`** — sanity-checks asset/tag before
  applying.

### `pdfreader_lib/search_index.py` *(pre-existing)*
SQLite FTS5 full-text search index with offline TF-IDF ranking.
Manages watched folders, re-indexing, and querying.

### `pdfreader_lib/comparison.py` *(pre-existing)*
Text-level PDF diff engine. Extracts text per page, aligns pages, and
produces `DiffResult` with `DiffSegment` lists for the `_CompareDialog`.

## Data flow

```
User action (button click / menu)
        │
        ▼
PdfReaderWindow method
        │
        ├── delegates to pdfreader_lib function
        │       │
        │       ▼ returns result / raises PdfSafetyError
        │
        └── handles UI (QMessageBox, statusBar, progress)
```

### Example: Open PDF

1. `open_pdf()` opens file dialog
2. `load_pdf(file_name)` calls `pdf_validator.safe_open_pdf()`
3. On success, creates a `TabData`, stores it in `self.tabs`
4. `_restore_state()` loads tab state into live instance vars
5. `render_page()` renders the first page onto `PdfPageLabel`

### Example: Check for update

1. `_updater.check_for_updates(self.update_action)` sends GET to GitHub API
2. `_on_update_check_reply` parses response, compares versions
3. If newer, shows `QMessageBox` with download option
4. On accept, `_start_download()` downloads asset via `QNetworkAccessManager`
5. `_on_download_finished()` saves to temp dir, calls `_apply_update()`
6. `_apply_update_windows_zip()` creates a `.bat` updater script,
   launches it, and closes the app

## Key design decisions

| Decision | Rationale |
|----------|-----------|
| **Composition over inheritance** | `PdfUpdater` is a composed `QObject`, not a mixin. Cleaner lifecycle and testability. |
| **Pure functions for validation & tools** | `pdf_validator.py` and `pdf_tools.py` have zero Qt imports — testable with plain `pytest`. |
| **TabData as plain dataclass** | No Qt dependency, serializable, swappable between tabs without UI overhead. |
| **ThemeManager encapsulates theme state** | Single source of truth for theme constants and dark-mode calculation. |
| **`_safe_open_pdf` wrapper in main.py** | Preserves backward compatibility for methods (e.g., `merge_pdfs`) that call `self._safe_open_pdf()`. |
| **`HAS_LIB_MODULES` guard** | Library and comparison features degrade gracefully when optional deps are missing. |

## Testing strategy

| Layer | Tool | Covers |
|-------|------|--------|
| Service tests | `pytest` | `pdf_validator`, `tab_state`, `theme_manager`, `pdf_tools`, `updater` helpers — 37 tests |
| Main module import | `python -c "from main import ..."` | Import chain, no segfault |
| CI | GitHub Actions (release/build) | Packaged exe builds |

## Security

- **PDF size limit:** 500 MB (configurable via `MAX_PDF_SIZE_BYTES`).
- **Render limit:** 80 MP (prevents OOM from pathological PDFs).
- **Validation chain:** Path → extension → file size → magic bytes → page
  dimensions. Every PDF is checked before `fitz.open()`.
- **Updater:** Downloads go to a temp directory; extracted to a subfolder
  named `extracted_{tag}`; the batch script cleans up after itself.
- **`subprocess` usage:** Only in the Windows updater (batch script launch).
  Flagged with `# nosec` for security audit transparency.
