<p align="center">
  <img src="assets/screenshot-main.png" alt="PDFReader by Sparsh main window" width="880">
</p>

<h1 align="center">PDFReader by Sparsh</h1>

<p align="center">
  A local-first, non-commercial desktop PDF reader for Windows and macOS source builds.
  <br>
  Read, search, copy, merge, split, extract, and compress PDFs without uploading documents anywhere.
</p>

<p align="center">
  <a href="https://github.com/sparshsam/pdfreader-by-sparsh/releases/latest"><img alt="Latest release" src="https://img.shields.io/github/v/release/sparshsam/pdfreader-by-sparsh?sort=semver"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-PolyForm%20Noncommercial-blue"></a>
  <a href="https://github.com/sparshsam/pdfreader-by-sparsh/actions/workflows/build-windows.yml"><img alt="Windows build" src="https://img.shields.io/github/actions/workflow/status/sparshsam/pdfreader-by-sparsh/build-windows.yml?label=windows%20build"></a>
  <a href="https://github.com/sparshsam/pdfreader-by-sparsh/actions/workflows/build-macos.yml"><img alt="macOS build" src="https://img.shields.io/github/actions/workflow/status/sparshsam/pdfreader-by-sparsh/build-macos.yml?label=macOS%20build"></a>
  <a href="https://github.com/sparshsam/pdfreader-by-sparsh/actions/workflows/security.yml"><img alt="Security checks" src="https://img.shields.io/github/actions/workflow/status/sparshsam/pdfreader-by-sparsh/security.yml?label=security"></a>
</p>

<p align="center">
  <a href="#download">Download</a>
  ·
  <a href="#features">Features</a>
  ·
  <a href="#screenshots">Screenshots</a>
  ·
  <a href="#roadmap">Roadmap</a>
  ·
  <a href="#build-from-source">Build</a>
  ·
  <a href="#security-and-privacy">Security</a>
  ·
  <a href="#cryptographic-verification-base">Verification</a>
  ·
  <a href="#future-philosophy">Philosophy</a>
</p>

## Overview

PDFReader by Sparsh is a practical desktop PDF utility built with Python, PySide6, and PyMuPDF. It is designed for people who want common PDF tasks in a simple native app without sending private documents to a cloud service.

The app is intentionally local-first: PDFs are opened, rendered, searched, merged, split, and compressed on your computer.

## Download

Get the latest builds from the [Releases page](https://github.com/sparshsam/pdfreader-by-sparsh/releases/latest).

| Platform | Download | Notes |
|---|---|---|
| Windows | `PDFReader.by.Sparsh.exe` | One-file executable. Python is not required. |
| macOS Apple Silicon | `PDFReader-by-Sparsh-macOS-Apple-Silicon.zip` | Unsigned app bundle. Gatekeeper may require manual approval. |
| macOS Intel | `PDFReader-by-Sparsh-macOS-Intel.zip` | Unsigned app bundle. Gatekeeper may require manual approval. |

Windows may show a SmartScreen warning because community builds are not code-signed. macOS may show a Gatekeeper warning because the Mac builds are not Apple-notarized. Only run software from sources you trust.

## Features

| Category | Capabilities |
|---|---|
| Reading | Open PDFs, one-page view, previous/next navigation, page jump, fit-width, zoom in/out |
| Search | Full-document text search, match count, next/previous result navigation |
| Copying | Drag-select text from the visible page and copy with `Ctrl+C` or the Copy button |
| OCR fallback | Attempts OCR-assisted selection on scanned/image-based pages when Tesseract OCR data is available |
| PDF tools | Merge PDFs, split every page, extract page ranges like `1-3,5`, save compressed copies |
| Desktop integration | Windows "Open with" support, last-folder memory with `QSettings`, custom app icon |
| Release engineering | PyInstaller packaging, Windows/macOS GitHub Actions builds, dependency/security checks |

## Screenshots

### Main Window

![PDFReader by Sparsh main window](assets/screenshot-main.png)

### Search View

![PDFReader by Sparsh search view](assets/screenshot-search.png)

## Why I Built This

I built PDFReader by Sparsh as a local-first alternative for reading and handling PDFs without uploading private documents to cloud services. The project helped me practice desktop GUI development, PDF processing, OCR fallback handling, packaging, release automation, and security hardening while creating a tool people can actually use.

## Security and Privacy

PDFReader by Sparsh processes PDFs locally. It does not use network services and does not upload PDFs.

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

## License and Use

PDFReader by Sparsh is free to use, share, study, and modify for non-commercial purposes under the [PolyForm Noncommercial License 1.0.0](LICENSE).

Commercial use, resale, paid redistribution, or bundling in a commercial product is not permitted without separate written permission from the copyright holder.

Earlier published versions may have been released under MIT. The current license applies from the license change forward.

## Requirements

| Use case | Requirements |
|---|---|
| Run Windows release | Windows. Python is not required. |
| Run macOS release | macOS. Apple Silicon or Intel build must match your Mac. |
| Develop/build locally | Python 3.11 or newer |

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
dist\PDFReader by Sparsh.exe
```

### macOS

The Windows `.exe` cannot run on macOS. PyInstaller bundles native binaries for the operating system it runs on, so Mac users need a macOS build.

```bash
git clone https://github.com/sparshsam/pdfreader-by-sparsh.git
cd pdfreader-by-sparsh
chmod +x scripts/build_macos.sh
./scripts/build_macos.sh
```

Output:

```text
dist/PDFReader by Sparsh.app
```

See [docs/macos.md](docs/macos.md) for macOS setup, Finder "Open With" notes, icon generation, OCR notes, and signing/notarization caveats.

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

## Roadmap

### Near-Term
Items in active or planned development.

- **Dark mode** — system-aware theme toggle for comfortable reading in any lighting
- **Recent files list** — quick access to recently opened documents
- **Multi-tab PDF support** — open several documents in a single window with tabbed navigation
- **Highlight and annotation tools** — select, highlight, underline, and add sticky notes; saved as PDF annotations (not a separate overlay)
- **Better OCR setup instructions** — clearer per-platform guidance for installing Tesseract OCR data
- **Windows installer package** — a professional installer (Inno Setup or MSI) with file-association registration and Start Menu entry
- **Auto-update integration** — in-app update checks against GitHub releases with one-click download and install

### Mid-Term
Ambitious but achievable additions that meaningfully expand the app's capabilities.

- **Full-library indexed search** — build a local search index over a folder of PDFs for instant, cross-document text search
- **Workspace and session restoration** — remember which documents were open, which page you were on, and restore on next launch
- **PDF version comparison** — diff two PDFs side-by-side and visually highlight text changes, insertions, and deletions
- **Local AI summarization** — generate document summaries and extract key points using a local LLM (e.g. Ollama, llama.cpp); no data ever leaves your machine
- **Offline semantic search** — search by meaning rather than exact keyword using local embeddings, entirely offline
- **Code signing** — signed Windows and macOS releases for smoother downloads without SmartScreen or Gatekeeper warnings
- **Stronger sandboxing guidance** — documented approaches for running the app in an OS sandbox when opening documents from untrusted sources

### Long-Term Vision
The direction the project grows into over time — grounded in real engineering, not speculation.

- **Cross-platform desktop support** — native builds for Linux in addition to Windows and macOS, broadening the audience to all major desktop platforms
- **Secure research workspace** — a sandboxed reading environment with isolated rendering, no write access to the rest of the filesystem, and optional network blocking for working with sensitive or untrusted documents
- **PDF timeline and version history** — track changes across document revisions, with a browsable timeline of edits and diffs
- **Plugin system** — a lightweight extension API for community-contributed tools (custom export formats, batch processing pipelines, metadata editors)
- **Collaborative annotations (optional, wallet-based)** — share annotations and highlights between trusted peers using cryptographic identity, not a cloud account

## Cryptographic Verification (Base)

Optional infrastructure for anchoring document fingerprints to the [Base](https://base.org) blockchain. This feature is entirely opt-in — the app functions fully without it.

### Philosophy

PDFs remain local. No document content is ever uploaded or transmitted. Only a cryptographic hash — a fixed-length fingerprint derived from the file — is written to the blockchain. This creates a permanent, publicly verifiable proof that a specific document existed at a specific time, without revealing anything about its contents.

### Planned capabilities

- **Proof-of-existence anchoring** — generate a SHA-256 hash of any PDF and record it on Base in a single low-cost transaction
- **Verification receipts** — the app produces a small local receipt file containing the block number, transaction hash, and document fingerprint, so you can prove a document's existence without re-querying the chain
- **QR verification slips** — print or save a QR code that encodes the verification receipt, allowing anyone with the original PDF to independently confirm it matches the anchored fingerprint
- **Portable proof metadata** — embed verification metadata directly in the PDF as a hidden annotation layer, so proof travels with the document
- **Optional wallet-based identity** — use an Ethereum wallet for signing annotations, allowing trusted collaborators to verify who made a highlight or note without a central account system

### What stays local

- All PDF content
- All rendering, search, and processing
- All AI summarization and semantic search (when enabled)
- All annotation data until a user explicitly anchors a hash or signs with their wallet

Base is used only as a low-cost, permanent verification layer. It is not a data store, not a monetization mechanism, and not a requirement for any core functionality.

## Future Philosophy

PDFReader by Sparsh sits at the intersection of a few ideas that I think are worth building towards:

- **Local-first tools** that work offline, respect your filesystem, and don't require an account
- **Privacy-preserving software** that treats user data as something to protect, not extract
- **Cryptographic proof systems** that let you assert facts about documents without revealing their contents
- **User ownership** — you install it, you run it, you decide what happens to your data
- **Interoperable calm utilities** — small, focused tools that compose well with each other rather than monolithic platforms
- **Optional decentralized infrastructure** — blockchain used as a lightweight verification oracle, not a platform for speculation or lock-in

This project is one piece of that broader picture. The immediate goal is a genuinely good PDF reader. Everything else — the proof layer, the AI features, the cross-platform story — builds on that foundation, never replaces it.

## Project Structure

```text
.
├── .github/                 # CI, security checks, Dependabot
├── assets/                  # App icon and README screenshots
├── docs/                    # Platform notes
├── scripts/                 # Build scripts
├── tools/                   # Developer utilities, including icon generation
├── main.py                  # Main PySide6 application
├── requirements.txt         # Pinned runtime/build dependencies
├── PDFReader by Sparsh.spec # PyInstaller spec
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
└── SECURITY.md
```

## Contributing

Contributions are welcome for non-commercial use cases. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md) before opening issues or pull requests.
