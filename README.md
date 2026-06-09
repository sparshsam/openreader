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

| Platform | Recommended Download | Alternative | Notes |
|---|---|---|---|---|
| Windows | `PDFReader-by-Sparsh-Setup.exe` | `PDFReader-by-Sparsh-Windows.zip` | Use Setup.exe for normal installation. ZIP remains for updater/portable/manual use. |
| macOS Apple Silicon | `PDFReader-by-Sparsh-macOS-Apple-Silicon.zip` | — | Unsigned app bundle. Gatekeeper may require manual approval. |
| macOS Intel | `PDFReader-by-Sparsh-macOS-Intel.zip` | — | Unsigned app bundle. Gatekeeper may require manual approval. |

Windows may show a SmartScreen warning because community builds are not code-signed. macOS may show a Gatekeeper warning because the Mac builds are not Apple-notarized. Only run software from sources you trust.

Packaged builds check the latest GitHub Release for updates. Source builds are intended to be updated with `git pull` and rebuilt locally.

## Windows Installation Guide

### Installing (Normal Install)

1. Go to the [Releases page](https://github.com/sparshsam/pdfreader-by-sparsh/releases/latest).
2. Download **`PDFReader-by-Sparsh-Setup.exe`**.
3. Double-click the installer.
4. If **Windows SmartScreen** shows a warning (see below), click **More info** then **Run anyway**.
5. Follow the installer prompts. The default installation path is:
   ```
   C:\Program Files\PDFReader by Sparsh\
   ```
6. The installer creates:
   - **Start Menu** folder named `PDFReader by Sparsh`
   - Optional **desktop shortcut**
   - **Add or Remove Programs** entry
   - **`.pdf` file association** registration

### Installing (Portable / ZIP)

Download **`PDFReader-by-Sparsh-Windows.zip`**, extract it anywhere, and run
`PDFReader by Sparsh.exe`. No admin rights needed. No file association or
Start Menu entry is created.

### First Launch and File Association

After installing, `.pdf` files will show the PDFReader icon. To make
PDFReader your default PDF app:

1. Right-click any `.pdf` file.
2. Choose **Open with > Choose another app**.
3. Select **PDFReader by Sparsh** from the list.
4. Check **Always use this app to open .pdf files**.
5. Click **OK**.

You can also use Windows Settings:
**Settings → Apps → Default Apps → Choose defaults by file type → .pdf**.

### Update Behavior

- The **built-in auto-updater** checks GitHub Releases on launch.
- When an update is found, the app downloads the new ZIP and applies it
  automatically (user data is preserved).
- Updates **replace** the app files in `C:\Program Files\PDFReader by Sparsh\`.
- User settings are stored separately under `%APPDATA%\Sparsh\PDFReader by Sparsh\`
  (Qt QSettings) and are never touched during updates.
- Library index data lives under `%USERPROFILE%\.pdfreader\library\` and
  is preserved across updates.

### Uninstalling

**Via Settings:**
1. Open **Settings → Apps → Installed apps**.
2. Find **PDFReader by Sparsh** in the list.
3. Click the **•••** menu and select **Uninstall**.
4. Confirm the uninstall.

**Via Start Menu:**
1. Open **Start Menu → PDFReader by Sparsh** folder.
2. Click **Uninstall PDFReader by Sparsh**.

The uninstaller removes:
- All app files from `Program Files`
- Start Menu shortcut
- Desktop shortcut (if created)
- `.pdf` file association entries from the registry
- App Paths registry entry

User settings, library index, and updater temp files are **not** removed
during uninstall. To fully clean up after uninstalling:

```powershell
# Remove user settings
Remove-Item -Recurse -Force "$env:APPDATA\Sparsh\PDFReader by Sparsh" -ErrorAction SilentlyContinue
# Remove library index
Remove-Item -Recurse -Force "$env:USERPROFILE\.pdfreader" -ErrorAction SilentlyContinue
# Remove updater temp files
Remove-Item -Recurse -Force "$env:TEMP\PDFReader-Updates" -ErrorAction SilentlyContinue
```

### Upgrading Over an Existing Install

- Run the new installer **without uninstalling** the old version.
- Inno Setup detects the existing install and upgrades in place.
- User settings and library data are preserved.
- Program Files content is replaced.
- This is the recommended upgrade path for end users.

### SmartScreen Warning

Windows may show **"Windows protected your PC"** when running the installer.
This is expected because the build is **not code-signed** with an EV
certificate (code-signing certificates cost several hundred dollars per year).

What to do:

1. Click **More info** (the text link, not the close button).
2. Click the **Run anyway** button.
3. The installer will proceed normally.

Why this happens:
- Free/open-source builds are almost never code-signed due to cost.
- SmartScreen has no reputation data for unsigned installers from new publishers.
- The warning is not about the app's safety — it's about the lack of a
  signed publisher identity.
- Once enough Windows users run the installer, SmartScreen builds a
  reputation and the warning becomes less frequent.

### Portable ZIP and SmartScreen

The `PDFReader-by-Sparsh-Windows.zip` portable build may also trigger
SmartScreen when extracting and running the `.exe`. The same **More info →
Run anyway** flow applies.

### Known Windows Limitations

| Limitation | Details |
|------------|---------|
| **No code signing** | Installer and EXE trigger SmartScreen (see above). |
| **No silent install** | The installer always shows a GUI — `/VERYSILENT` is not exposed. Can be added on request. |
| **No per-user install** | The installer requires admin rights (`PrivilegesRequired=admin`). Per-user (non-admin) installs are not currently supported. |
| **`.pdf` association not system-default** | The installer registers the app as a PDF handler, but Windows does not change the system default app. Users must set this manually (see above). |
| **No per-machine mutex** | Multiple instances of the app can be launched. No single-instance enforcement. |
| **Updater replaces in-place** | The auto-updater replaces app files while the app is closed. If a file is locked, the update will fail (with a diagnostic message logged to `%TEMP%\PDFReader-Updates\updater-debug.log`). |
| **Tesseract OCR** | OCR requires a separate Tesseract install (see OCR Setup section). The installer does not bundle Tesseract. |

## Features

| Category | Capabilities |
|---|---|
| Reading | Open PDFs, one-page view, previous/next navigation, page jump, fit-width, zoom in/out |
| Multi-tab | Open several documents in a single window with movable, closeable tabs. Ctrl+T, Ctrl+W |
| Session restore | Remembers open PDFs and page positions across restarts. Auto or manual restore |
| Search (keyword) | Full-document text search, match count, next/previous result navigation |
| Search (semantic) | TF-IDF cosine similarity search across indexed library. Toggle "Semantic" in search bar |
| Library search | SQLite FTS5 full-text index over entire folders. Cross-document search ranked by BM25 |
| PDF comparison | Side-by-side diff with color-coded changes (red delete, green insert) |
| Copying | Drag-select text from the visible page and copy with `Ctrl+C` or the Copy button |
| OCR fallback | Attempts OCR-assisted selection on scanned/image-based pages when Tesseract OCR data is available |
| Annotations | Highlight, underline, and strikethrough selected text; sticky notes on any page. Saved as native PDF annotations |
| PDF tools | Merge PDFs, split every page, extract page ranges like `1-3,5`, save compressed copies |
| Desktop integration | Windows installer with `.pdf` file association, Start Menu, and desktop shortcut |
| Dark mode | System-aware dark theme (Catppuccin Mocha) with Auto/Light/Dark toggle |
| Recent files | Quick access to the last 10 opened PDFs via File → Open Recent |
| Auto-update | Packaged builds check GitHub Releases and update from canonical release ZIP assets |
| Release engineering | Tag-driven GitHub Release publishing, PyInstaller packaging, Windows/macOS GitHub Actions builds, Inno Setup installer, self-update mechanism |

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
dist\PDFReader by Sparsh\
├── PDFReader by Sparsh.exe
└── _internal\
    ├── python311.dll
    ├── PySide6\
    └── ...
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

## Releases and Auto-Update

Release assets are the canonical distribution path. GitHub Actions artifacts are CI outputs and are not visible to the in-app updater.

The updater checks:

```text
https://api.github.com/repos/sparshsam/pdfreader-by-sparsh/releases/latest
```

It expects these exact asset names on the latest GitHub Release:

```text
PDFReader-by-Sparsh-Windows.zip
PDFReader-by-Sparsh-macOS-Apple-Silicon.zip
PDFReader-by-Sparsh-macOS-Intel.zip
```

See [RELEASE.md](RELEASE.md) for release instructions, version injection, updater discovery, and validation.

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

### ✓ v0.3.0 — Completed
These features are shipped in the latest release.

- **Workspace and session restoration** — remembers which PDFs were open and what page you were on. Auto-restore on launch (toggle in File menu).
- **Full-library indexed search** — SQLite FTS5-based full-text index over entire folders of PDFs. Manage folders via Library dialog, search across all documents instantly.
- **PDF version comparison** — side-by-side diff view with color-coded changes (red deletions, green insertions). Compares page by page.
- **Offline semantic search** — TF-IDF cosine similarity search (no ML dependencies). Toggle "Semantic" checkbox in the search bar for meaning-based matching across your indexed library.
- **Compare button** in toolbar and **Tools → Compare PDFs** menu entry.
- **Library button** in toolbar and **View → Library Search** menu entry with Ctrl+Shift+F shortcut.
- **Semantic search toggle** (checkbox) integrated into the main search bar.

### ✓ v0.2.0 — Completed

- **Highlight and annotation tools** — select, highlight, underline, and add sticky notes directly on PDFs; saved as native PDF annotations, not overlays
- **Multi-tab PDF support** — open several documents in a single window with tabbed navigation. Ctrl+T new tab, Ctrl+W close tab
- **Dark mode** — system-aware Catppuccin Mocha theme with Auto/Light/Dark toggle (View → Theme)
- **Recent files list** — last 10 documents in File → Open Recent
- **Windows installer** — Inno Setup installer with `.pdf` file association and Start Menu entry
- **OCR setup docs** — per-platform Tesseract installation guide above
- **macOS auto-update** — PID-based process wait, retry logic, Gatekeeper quarantine clearance

### Near-Term
Items in active or planned development.

- **Local AI summarization** — generate document summaries and extract key points using a local LLM (e.g. Ollama, llama.cpp); no data ever leaves your machine
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
├── .github/                 # CI, issue templates, PR template, Dependabot
├── assets/                  # App icon and README screenshots
├── docs/                    # Platform notes
├── installer/               # Inno Setup installer script
├── scripts/                 # Build scripts (Windows, macOS, version injection)
├── tests/                   # Service-level tests (pytest)
├── tools/                   # Developer utilities, including icon generation
├── main.py                  # Main PySide6 application
├── pdfreader_lib/           # Service modules (updater, validation, pdf tools, theme, tabs)
├── requirements.txt         # Pinned runtime/build dependencies
├── PDFReader by Sparsh.spec # PyInstaller spec
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
└── SECURITY.md
```

## Contributing

Contributions are welcome for non-commercial use cases. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md) before opening issues or pull requests.

---

*Last updated: June 2026*

## Tech Stack

| Layer | Choice |
|-------|--------|
| Language | Python |
| Platform | Cross-platform (Windows, macOS) |
| UI | Desktop native |
