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
| GUI | `main.py` | PySide6 application window, menus, controls bar, PDF viewer |
| PDF Engine | — | PyMuPDF (MuPDF bindings) for rendering, text extraction, annotation |
| Search | `pdfreader_lib/search_index.py` | SQLite FTS5 keyword index + TF-IDF semantic search |
| Comparison | `pdfreader_lib/comparison.py` | Page-by-page text diff with color-coded output |
| MCP Server | `pdfreader_lib/mcp_server.py` | Model Context Protocol server for AI agent integration (14 tools) |

## Key Architecture Decisions

1. **Local-first.** No network calls beyond the optional GitHub release update check. PDFs are never uploaded or transmitted.
2. **Single-process.** The GUI and all operations run in a single process. Heavy operations (search, compare, compress) show progress feedback.
3. **SQLite for indexing.** Library search uses SQLite FTS5 (keyword) and scikit-learn TF-IDF (semantic). Both are local, zero-configuration, and fast.
4. **MCP server as library.** The MCP server is built into `pdfreader_lib/` and can be used standalone or alongside the GUI. It shares the same underlying search and comparison modules.
5. **No self-update.** The app detects updates via GitHub API but never downloads or runs installers. MSIX updates are handled by Windows App Installer.

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
