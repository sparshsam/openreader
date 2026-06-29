# Development

> Developer documentation for OpenReader. For product information, see the [README](../README.md).

---

## Quick Start

### Prerequisites

- Python 3.11+
- Git
- Windows 10/11 (primary target)

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

### macOS

macOS is experimental. To run from source:

```bash
git clone https://github.com/sparshsam/openreader.git
cd openreader
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

See [Platform Notes](macos.md) for macOS-specific setup and OCR guidance.

### OCR Setup

Text selection works natively on PDFs with embedded text. For scanned/image-only PDFs, the app falls back to OCR via PyMuPDF's Tesseract integration.

| Platform | Command |
|----------|---------|
| Windows | Download Tesseract from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesserage/releases), run the installer, check "Add to PATH", restart the app |
| macOS | `brew install tesseract` |
| Linux | `sudo apt install tesseract-ocr tesseract-ocr-eng` |

---

## Project Structure

```
.
├── .github/                 # CI, security checks, Dependabot
├── assets/                  # App icon and README screenshots
├── docs/                    # Platform notes, playbooks, architecture
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

---

## Building

### Windows — Packaged Executable

```powershell
.\scripts\build_windows.ps1
```

Output:

```
dist\OpenReader\
├── OpenReader.exe
└── _internal\
    ├── python311.dll
    ├── PySide6\
    └── ...
```

### Build Verification

```bash
python -m py_compile main.py tools/create_icon.py scripts/inject_version.py
```

### Testing

```bash
python -m pytest tests/ -v
```

---

## Release Assets

Canonical release asset names:

| Asset | Description |
|-------|-------------|
| `OpenReader-Windows.zip` | Portable Windows build |
| `OpenReader-macOS-Apple-Silicon.zip` | macOS Apple Silicon build |
| `OpenReader-macOS-Intel.zip` | macOS Intel build |
| `OpenReader.msix` | MSIX package for sideloading |
| `OpenReader-Setup.exe` | Legacy installer |

### Versioning

- Tags follow `vMAJOR.MINOR.PATCH`.
- Version is injected from the tag via `scripts/inject_version.py` during CI.
- Source builds always show `-dev`.
- MSIX version uses 4-part `major.minor.patch.build` where build number maps to patch.

### Frozen Identity

These values must never change after the first release:

| Property | Value |
|----------|-------|
| Identity Name | `SparshSam.OpenReader` |
| Publisher | `CN=E6186421-BF8A-47E0-A89C-0F513DFF91C0` |
| PFN | `SparshSam.OpenReader_yh0byntbzd2qw` |
| Store ID | `9MXDVW2645LL` |

---

## Tech Stack

| Layer | Choice |
|-------|--------|
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

## MCP Server

OpenReader ships a built-in [Model Context Protocol](https://modelcontextprotocol.io) server for AI agent integration. All operations run locally — no cloud, no API keys, no document uploads.

### Quick Setup

```bash
pip install -r requirements-mcp.txt
```

### Agent Configuration

Add to your MCP-compatible agent's configuration:

```json
{
  "mcpServers": {
    "openreader": {
      "command": "python",
      "args": ["-m", "pdfreader_lib.mcp_server"]
    }
  }
}
```

### Standalone Package

A standalone pip package is also available:

```bash
pip install openreader-mcp
python -m openreader_mcp
```

### Transports

| Transport | Command |
|-----------|---------|
| stdio (default) | `python -m pdfreader_lib.mcp_server` |
| HTTP/SSE | `python -m pdfreader_lib.mcp_server --transport sse --port 8312` |

### Available Tools (14)

| Tool | Purpose |
|------|---------|
| `extract_text` | Extract text from any page range |
| `get_page_text` | Get text from a single page |
| `get_metadata` | Read document metadata |
| `get_page_count` | Get total page count |
| `search_pdf` | Keyword search within a document |
| `search_library` | FTS5 BM25 cross-document search |
| `search_semantic` | TF-IDF cosine similarity search |
| `compare_pdfs` | Page-by-page structured diff |
| `merge_pdfs` | Combine multiple PDFs into one |
| `split_pdf` | Split PDFs by page or range |
| `extract_pages` | Extract specific page ranges |
| `compress_pdf` | Save a compressed copy |
| `index_folder` | Index a folder for library search |
| `list_indexed_docs` | List indexed documents |

---

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](../CONTRIBUTING.md) and [SECURITY.md](../SECURITY.md) before opening issues or pull requests.

### Design Principles

- **Local-first.** No cloud dependency. No network calls beyond the optional GitHub release update check.
- **Privacy by design.** Treat PDFs as private user data. Never upload or transmit document content.
- **Windows primary.** macOS experimental. Linux unsupported.

### Security

- Accepts `.pdf` files only
- Checks for PDF header before parsing
- Rejects empty files and files over 500 MB
- Caps render pixel allocation to reduce OOM risk
- Runs `pip-audit` and Bandit in CI

These checks reduce risk from malformed or oversized PDFs, but PDF parsing still depends on PyMuPDF/MuPDF. Avoid opening PDFs from untrusted sources unless using OS-level sandboxing.

### Update Policy

OpenReader does not install updates itself:

- **Microsoft Store** installations update automatically through the Store.
- **GitHub MSIX** installations: Help → Check for Updates opens the releases page. Download and install manually.
- **Source builds**: `git pull` and rebuild.

---

## Architecture Reference

See [Product Architecture Playbook](playbooks/PRODUCT_ARCHITECTURE_PLAYBOOK.md) and [Design Playbook](playbooks/DESIGN_PLAYBOOK.md) for the full design and architecture documentation.
