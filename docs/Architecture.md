# Architecture

> System architecture and design decisions for OpenReader.

For the full design and product architecture playbook, see [Design Playbook](playbooks/DESIGN_PLAYBOOK.md) and [Product Architecture Playbook](playbooks/PRODUCT_ARCHITECTURE_PLAYBOOK.md).

---

## Overview

OpenReader is a local-first desktop PDF utility built with Python and PySide6 (Qt 6). Every operation — reading, searching, annotating, comparing, merging, splitting — runs on the user's machine. No cloud, no accounts, no telemetry.

```
┌─────────────────────────────────────────┐
│  main.py                                │
│  PySide6 (Qt 6) UI                      │
│  ┌─────────────────────────────────┐    │
│  │  pdfreader_lib/                 │    │
│  │  ├── search_index.py            │    │
│  │  ├── comparison.py              │    │
│  │  ├── form_fields.py             │    │
│  │  └── mcp_server.py              │    │
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │  PyMuPDF (MuPDF) — PDF engine   │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
            │
            ▼
     Local filesystem only
     (PDFs, SQLite indexes, OCR cache)
```

## Core Components

| Component | Module | Purpose |
|-----------|--------|---------|
| GUI | `main.py` | PySide6 application window, menus, unified toolbar, PDF viewer |
| PDF Engine | — | PyMuPDF (MuPDF bindings) for rendering, text extraction, annotation |
| Search | `pdfreader_lib/search_index.py` | SQLite FTS5 keyword index + TF-IDF semantic search |
| Comparison | `pdfreader_lib/comparison.py` | Page-by-page text diff with color-coded output |
| Forms | `pdfreader_lib/form_fields.py` | AcroForm field model, value read/write, type detection & advisory validation (v1.3.0+) |
| Editing model | `pdfreader_lib/edit_objects.py` | Qt-free text/signature/image objects, `OpenReaderData` metadata, atomic save, flattened export, signature detection |
| Editing UI | `pdfreader_lib/edit_gui.py` | Per-tab edit controller, page overlays, inline text editor, signature dialog, undo/redo |
| Signatures | `pdfreader_lib/signature_store.py` | Local-only PNG signature library with delete/clear controls |
| MCP Server | `pdfreader_lib/mcp_server.py` | Model Context Protocol server for AI agent integration (19 tools) |

## Key Architecture Decisions

1. **Local-first.** No network calls beyond the optional GitHub release update check. PDFs are never uploaded or transmitted.
2. **Single-process.** The GUI and all operations run in a single process. Heavy operations (search, compare, compress) show progress feedback.
3. **SQLite for indexing.** Library search uses SQLite FTS5 (keyword) and scikit-learn TF-IDF (semantic). Both are local, zero-configuration, and fast.
4. **MCP server as library.** The MCP server is built into `pdfreader_lib/` and can be used standalone or alongside the GUI. It shares the same underlying search and comparison modules.
5. **No self-update.** The app detects updates via GitHub API but never downloads or runs installers. MSIX updates are handled by Windows App Installer.
6. **Virtualized continuous rendering.** The default view keeps one correctly sized placeholder widget per page in a single persistent layout, so the scrollbar always spans the whole document and every page stays reachable. Page pixmaps are rendered lazily for the viewport plus a small overscan (`CONTINUOUS_OVERSCAN`) and released once they leave the cache window (`CONTINUOUS_CACHE`), keeping memory bounded at high zoom and for long documents. Scroll position drives the current page; Next/Previous, the page box, and search jumps scroll in place without rebuilding the layout. Explicit renders (zoom, annotations, search, theme) invalidate the cached pixmaps. Single-page mode remains available via **View → Continuous Scroll**.
7. **Theme-aware design system.** A single 44 px toolbar groups file, page, zoom, annotation, and search actions. Icons are drawn as vectors from one factory (`_make_toolbar_icon`) in the active theme's palette, and both light and dark stylesheets share the same neutral tokens with the OpenReader accent.
8. **Editing is persisted, never painted on top.** Text objects are native `FreeText` annotations; signatures and images are image XObjects in page content. Both carry an `OpenReaderData` JSON key so OpenReader can find and re-edit them after save/reopen. There is no sidecar or temporary canvas that is lost on save.
9. **Safe writes.** Saves use a temp file in the same directory plus `os.replace`; encryption is preserved with `PDF_ENCRYPT_KEEP`. Flattened export uses `Document.bake` on a copy, so the original file is untouched. Documents with digital-signature fields warn before editing/saving; encrypted documents and rotated pages are read-only for editing.

## Editing Pipeline (v1.3.0)

```
Fill  ── AcroForm widgets ────────────────┐
Add Text ── FreeText annot + metadata ────┤
Sign  ── PNG image content + metadata ────┤── EditController (per tab)
Image ── PNG image content + metadata ────┘        │
                                                   ├─ overlays on page labels (continuous or single page)
                                                   ├─ inline text editor + contextual formatting bar
                                                   ├─ undo/redo snapshots of editable objects
                                                   └─ atomic save / Save As / flattened export
```

Coordinates are always PDF points; the GUI converts to and from page-label pixels using the active layout zoom. Page labels are persistent in continuous mode, so editing works without leaving continuous scroll.

## Security Model

- PDF validation before parsing (header check, size limits)
- Render pixel caps to prevent OOM from malformed PDFs
- Bandit + pip-audit in CI
- No secrets or credentials stored (no accounts)

## Distribution

- **Primary:** Microsoft Store (automatic updates via Store)
- **Secondary:** GitHub Releases (MSIX for sideloading)
- **Legacy:** Setup.exe and portable ZIP

See [Deployment](Deployment.md) for CI/CD and release details.
