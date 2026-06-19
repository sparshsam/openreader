<p align="center">
  <img src="assets/screenshot-main.png" alt="OpenReader main window" width="880">
</p>

<h1 align="center">OpenReader</h1>

<p align="center">
  A privacy-first desktop PDF utility for Windows.
  <br>
  Read, search, copy, merge, split, extract, and compress PDFs — all locally, no uploads required.
</p>

<p align="center">
  <a href="https://github.com/sparshsam/pdfreader-by-sparsh/releases/latest"><img alt="Latest release" src="https://img.shields.io/github/v/release/sparshsam/pdfreader-by-sparsh?sort=semver&label=stable%20release"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-AGPLv3-blue"></a>
  <a href="https://github.com/sparshsam/pdfreader-by-sparsh/actions/workflows/release.yml"><img alt="Release build" src="https://img.shields.io/github/actions/workflow/status/sparshsam/pdfreader-by-sparsh/release.yml?label=release%20build"></a>
  <a href="https://github.com/sparshsam/pdfreader-by-sparsh/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/sparshsam/pdfreader-by-sparsh/ci.yml?label=CI"></a>
  <a href="https://github.com/sparshsam/pdfreader-by-sparsh/actions/workflows/security.yml"><img alt="Security" src="https://img.shields.io/github/actions/workflow/status/sparshsam/pdfreader-by-sparsh/security.yml?label=security"></a>
  <a href="https://github.com/sparshsam/pdfreader-by-sparsh/releases"><img alt="Downloads" src="https://img.shields.io/github/downloads/sparshsam/pdfreader-by-sparsh/total"></a>
</p>

<p align="center">
  <a href="#download">Download</a>
  ·
  <a href="#features">Features</a>
  ·
  <a href="#screenshots">Screenshots</a>
  ·
  <a href="#build-from-source">Build</a>
  ·
  <a href="#privacy-and-security">Privacy</a>
  ·
  <a href="#ai-agent-integration-mcp-server">AI Agent</a>
  ·
  <a href="ARCHITECTURE.md">Architecture</a>
  ·
  <a href="VERSIONING.md">Versioning</a>
</p>

## Overview

OpenReader is a **local-first desktop PDF utility** built with Python, PySide6, and PyMuPDF. It is designed for people who want common PDF tasks in a simple native app without sending private documents to a cloud service.

The app is intentionally local-first: PDFs are opened, rendered, searched, merged, split, annotated, and compressed on your computer — no uploads, no accounts, no telemetry.

**Current version:** v1.2.2 (June 2026)

## Download

### Recommended: Microsoft Store

The Microsoft Store submission is in certification. Once approved, install OpenReader with one click — automatic updates included.

*Store link will appear here after certification.*

### GitHub Releases (Advanced Users)

MSIX packages are available from the [Releases page](https://github.com/sparshsam/pdfreader-by-sparsh/releases).

| Platform | Package | Notes |
|---|---|---|
| Windows 10/11 | `OpenReader.msix` | MSIX package. May be unsigned — requires [Windows Developer Mode](https://learn.microsoft.com/en-us/windows/apps/get-started/enable-your-device-for-development) for sideloading. |
| Windows 10/11 | `OpenReader-Setup.exe` | Legacy Inno Setup installer for manual recovery. Requires administrator rights. |
| Windows 10/11 | `OpenReader-Windows.zip` | Portable ZIP for manual recovery. |
| macOS | `OpenReader-macOS-*.zip` | **Experimental.** Community-tested. See [macOS notes](docs/macos.md). |
| Linux | — | Unsupported. |

### Platform Support

| Platform | Status |
|---|---|
| Windows 10/11 | Supported |
| Microsoft Store | In certification — recommended after approval |
| GitHub MSIX | Advanced users |
| macOS Apple Silicon | Experimental |
| macOS Intel | Experimental |
| Linux | Unsupported |

### Update Policy

OpenReader does not install updates itself.

- **Microsoft Store** installations update automatically through the Store.
- **GitHub MSIX** installations can check for new versions (Help → Check for Updates) but updates must be downloaded and installed manually.
- **Source builds** should be updated with `git pull` and rebuilt locally.

## Features

| Category | Capabilities |
|---|---|
| Reading | Open PDFs, one-page view, previous/next navigation, page jump, fit-width, zoom in/out |
| Multi-tab | Open several documents in a single window with movable, closeable tabs. Ctrl+T new tab, Ctrl+W close tab, Ctrl+Shift+W close all |
| Session restore | Remembers open PDFs and page positions across restarts. Auto or manual restore (File menu toggle) |
| Search (keyword) | Full-document text search, match count, next/previous result navigation (PageUp/PageDown). Ctrl+F to focus |
| Search (semantic) | TF-IDF cosine similarity search across indexed library. Toggle "Semantic" in search bar |
| Library search | SQLite FTS5 full-text index over entire folders. Cross-document search ranked by BM25. Ctrl+Shift+F shortcut |
| PDF comparison | Side-by-side diff with color-coded changes (red delete, green insert) and diff summary |
| Copying | Drag-select text from the visible page and copy with `Ctrl+C` or the Copy button |
| OCR fallback | Attempts OCR-assisted selection on scanned/image-based pages when Tesseract OCR data is available |
| Annotations | Highlight, underline, and strikethrough selected text; sticky notes on any page. Saved as native PDF annotations |
| Annotation management | Show/hide annotations toggle (View menu). Delete all annotations on current page or entire document (Tools menu) |
| Save PDF | Explicit File → Save (Ctrl+S) to persist annotation edits immediately |
| PDF tools | Merge PDFs, split every page, extract page ranges like `1-3,5`, save compressed copies |
| Dark mode | System-aware dark theme (Catppuccin Mocha) with Auto/Light/Dark toggle via View → Theme |
| Recent files | Quick access to the last 10 opened PDFs via File → Open Recent |
| Update detection | Help → Check for Updates queries GitHub API and opens the releases page. |

## Screenshots

| Reader | Sample PDF |
|---|---|
| ![Reader](assets/screenshots/reader-main.png) | ![Sample PDF](assets/screenshots/sample-pdf.png) |

| Sample PDF 2 | PDF Tools |
|---|---|
| ![Sample PDF 2](assets/screenshots/sample-pdf-2.png) | ![PDF Tools](assets/screenshots/merge-split.png) |

| Dark Mode | About |
|---|---|
| ![Dark Mode](assets/screenshots/dark-mode.png) | ![About](assets/screenshots/about.png) |

## Privacy and Security

OpenReader processes PDFs locally. It does not use network services and does not upload PDFs.

The app includes lightweight safety checks before opening and rendering documents:

- Accepts `.pdf` files only.
- Checks for a PDF header before parsing.
- Rejects empty files and files over 500 MB.
- Rejects pages outside the supported page-size limit.
- Caps render pixel allocation to reduce PDF-bomb/OOM risk.
- Limits all-pages search result storage.
- Keeps only a small OCR page cache in memory.
- Runs `pip-audit` and Bandit in CI.

These checks reduce risk from malformed or oversized PDFs, but PDF parsing still depends on PyMuPDF/MuPDF. Avoid opening PDFs from untrusted sources unless you use OS-level sandboxing, a VM, or another isolation layer.

## License

OpenReader is free software under the [GNU AGPLv3](LICENSE).

Copyright &copy; 2026 Sparsh Sam.

## Requirements

| Use case | Requirements |
|---|---|
| Run Windows package | Windows 10 or newer. Python is not required. |
| Develop or build from source | Python 3.11 or newer. Windows recommended. macOS source builds may work but are not tested. |

## Build From Source

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

Build the Windows executable:

```powershell
.\scripts\build_windows.ps1
```

Output:

```text
dist\OpenReader\
├── OpenReader.exe
└── _internal\
    ├── python311.dll
    ├── PySide6\
    └── ...
```

### macOS

The Windows `.exe` cannot run on macOS. PyInstaller bundles native binaries for the operating system it runs on.

**macOS packaged builds are experimental.** The app is developed and tested primarily on Windows. To run on macOS, build from source:

```bash
git clone https://github.com/sparshsam/pdfreader-by-sparsh.git
cd pdfreader-by-sparsh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

See [docs/macos.md](docs/macos.md) for macOS setup, Finder "Open With" notes, icon generation, and OCR notes.

## OCR Setup

Text selection works natively on PDFs with embedded text. For scanned/image-only PDFs, the app falls back to OCR via PyMuPDF's Tesseract integration.

No OCR setup is needed to read regular PDFs — the app only requires Tesseract when you drag-select text on a scanned page.

### Installing Tesseract

**Windows**
1. Download the installer from [GitHub UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/releases)
2. Run the installer — check "Add to PATH" during setup
3. Restart the app; OCR will work automatically

**macOS**
```bash
brew install tesseract
```
No restart needed — PyMuPDF finds it automatically.

**Linux (source builds)**
```bash
# Debian / Ubuntu
sudo apt install tesseract-ocr tesseract-ocr-eng

# Fedora
sudo dnf install tesseract tesseract-langpack-eng

# Arch
sudo pacman -S tesseract tesseract-data-eng
```

## Roadmap

### Near-Term
- **Microsoft Store submission** — currently in certification
- **Local AI summarization** — generate document summaries and extract key points using a local LLM (e.g. Ollama, llama.cpp); no data ever leaves your machine
- **Stronger sandboxing guidance** — documented approaches for running the app in an OS sandbox when opening documents from untrusted sources
- **Winget support** — `winget install SparshSam.OpenReader`

### Long-Term Vision
- **Cross-platform desktop support** — native builds for Linux in addition to Windows and macOS
- **Secure research workspace** — a sandboxed reading environment with isolated rendering and optional network blocking
- **PDF timeline and version history** — track changes across document revisions
- **Plugin system** — a lightweight extension API for community-contributed tools
- **Collaborative annotations (optional, wallet-based)** — share annotations between trusted peers using cryptographic identity

## Project Structure

```text
.
├── .github/                 # CI, security checks, Dependabot
├── assets/                  # App icon and README screenshots
├── docs/                    # Platform notes and known limitations
├── installer/               # Inno Setup installer script (legacy)
├── packaging/               # MSIX packaging
├── scripts/                 # Build scripts
├── tests/                   # Regression test suite
├── tools/                   # Developer utilities and CI test helpers
├── main.py                  # Main PySide6 application
├── pdfreader_lib/           # Core library (search, comparison, MCP server)
├── requirements.txt         # Pinned runtime/build dependencies
├── requirements-mcp.txt     # MCP server dependencies (optional)
└── CHANGELOG.md
```

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md) before opening issues or pull requests.

## AI Agent Integration (MCP Server)

OpenReader ships with a built-in [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that lets AI agents interact with PDFs programmatically. Agents can read, search, compare, merge, split, compress, and index PDFs — all locally, no cloud involved.

### Available Tools (14)

| Tool | Purpose |
|---|---|
| `extract_text` | Extract all text from a PDF, per-page |
| `get_page_text` | Extract text from a single page |
| `get_metadata` | Get PDF metadata (title, author, pages, size) |
| `get_page_count` | Get the number of pages |
| `search_pdf` | Search for text within a single PDF |
| `compare_pdfs` | Compare two PDFs page-by-page with diff |
| `merge_pdfs` | Merge multiple PDFs into one |
| `split_pdf` | Split into individual page files |
| `extract_pages` | Extract specific pages by range (e.g. `1-3,5,7-9`) |
| `compress_pdf` | Create a compressed copy |
| `index_folder` | Build SQLite FTS5 full-text index for a folder |
| `search_library` | Search across all indexed PDFs (BM25 ranked) |
| `search_semantic` | TF-IDF meaning-based search across indexed PDFs |
| `list_indexed_docs` | List all documents in the search index |

### Setup

```bash
# Install the MCP SDK
pip install -r requirements-mcp.txt

# For SSE/HTTP transport (optional):
# pip install starlette uvicorn
```

### Agent Configuration

**Claude Code, Hermes Agent, or any MCP-compatible agent:**

Add to your agent's MCP server configuration:

```json
{
  "mcpServers": {
    "pdfreader-by-sparsh": {
      "command": "python",
      "args": ["-m", "pdfreader_lib.mcp_server"]
    }
  }
}
```

### Usage

The server runs over stdio by default (standard for AI agents):

```bash
python -m pdfreader_lib.mcp_server
```

For HTTP/SSE transport (gateway mode):

```bash
python -m pdfreader_lib.mcp_server --transport sse --port 8312
```

### What Agents Can Do

- **Extract text** from PDFs for analysis or summarization
- **Search** across a folder of PDFs using full-text or semantic search
- **Compare** document versions and get structured diffs
- **Merge** multiple PDFs into one document
- **Split** PDFs by page or extract specific page ranges
- **Compress** PDFs to reduce file size
- **Index** entire folders for cross-document search

All operations are local. No data is uploaded anywhere.

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| UI Framework | PySide6 (Qt 6) |
| PDF Rendering | PyMuPDF (MuPDF) |
| Search | SQLite FTS5 (keyword), TF-IDF / scikit-learn (semantic) |
| OCR | PyMuPDF / Tesseract integration |
| Packaging | PyInstaller (onedir), MSIX |
| CI/CD | GitHub Actions (Windows + macOS) |
| Security scanning | Bandit, pip-audit |
| Platform | Windows (primary), macOS (experimental) |

---

*Last updated: June 2026*
