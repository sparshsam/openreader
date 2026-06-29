<p align="center">
  <img src="assets/AppIcon.iconset/icon_256x256.png" alt="OpenReader" width="72">
</p>

<h1 align="center" style="font-size: 2.75rem; font-weight: 700; letter-spacing: -0.02em; margin: 0.5rem 0 0.25rem;">
  OpenReader
</h1>

<p align="center" style="font-size: 1.2rem; color: #666; margin: 0 0 0.5rem;">
  Private PDF tools for your computer. No uploads. No accounts. No cloud.
</p>

<p align="center">
  <img src="assets/screenshots/reader-main.png" alt="OpenReader reading a PDF" width="880" style="border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.15);">
</p>

<p align="center" style="font-size: 0.95rem; color: #888; margin: 0.75rem 0 1.5rem;">
  Built for Windows 10 &amp; 11 · 100% Offline · Open Source · AI-ready
</p>

<p align="center">
  <strong style="font-size: 1.15rem;">⭐ Get OpenReader</strong>
</p>

<p align="center">
  <a href="https://apps.microsoft.com/detail/9MXDVW2645LL"><img alt="Microsoft Store" src="https://img.shields.io/badge/Microsoft%20Store%20(Recommended)-ff255f?style=for-the-badge&logo=microsoft&logoColor=white"></a>
  &nbsp;
  <a href="https://github.com/sparshsam/openreader/releases/latest"><img alt="Portable Release" src="https://img.shields.io/badge/Portable%20Release-1a1b26?style=for-the-badge&logo=github&logoColor=white"></a>
  &nbsp;
  <a href="https://reader.kovina.org"><img alt="Project Website" src="https://img.shields.io/badge/Project%20Website-000000?style=for-the-badge&logo=googlechrome&logoColor=white"></a>
  &nbsp;
  <a href="https://github.com/sparshsam/openreader"><img alt="Source Code" src="https://img.shields.io/badge/Source%20Code-ffffff?style=for-the-badge&logo=github&logoColor=black"></a>
</p>

---

## Why OpenReader

| | |
|---|---|
| **Truly private** | Every operation runs on your machine. No accounts, no telemetry, no cloud uploads. |
| **Works offline** | No internet required. Open, read, and annotate PDFs anywhere. |
| **Built for Windows** | A native reading experience with proper Windows 10/11 integration. |
| **AI-ready** | Built-in MCP server lets AI agents interact with your PDFs — entirely local. |

---

## Features

| | |
|---|---|
| **📖 Read** — Open PDFs, one-page or continuous scroll, fit-width zoom, page jump. | **📝 Annotate** — Highlight, underline, strikethrough, and sticky notes. Saved as native PDF annotations. |
| **🔍 Search** — Full-document keyword search with match count and navigation. | **📚 Library search** — Index entire folders with SQLite FTS5 for cross-document BM25-ranked search. |
| **🧠 Semantic search** — TF-IDF cosine similarity — meaning-based matching, no external ML. | **📊 Compare** — Side-by-side diff with color-coded changes and structured summary. |
| **📑 Multi-tab** — Open several documents in one window with movable tabs. | **🌙 Dark mode** — System-aware theme with Auto/Light/Dark toggle. |
| **🔧 PDF tools** — Merge, split, extract page ranges, compress. | **👁️ OCR fallback** — Automatic OCR on scanned/image-based pages when Tesseract is available. |
| **💾 Session restore** — Remembers open documents and page positions across restarts. | **🤖 AI agent integration** — Built-in MCP server with 14 tools for automated PDF workflows. |

---

## Screenshots

| Dark Mode | PDF Tools |
|---|---|
| ![Dark Mode](assets/screenshots/dark-mode.png) | ![PDF Tools: merge, split, compress](assets/screenshots/merge-split.png) |

| About & Keyboard Shortcuts | Sample Document |
|---|---|
| ![About dialog with keyboard shortcuts](assets/screenshots/about.png) | ![Sample PDF loaded in OpenReader](assets/screenshots/sample-pdf.png) |

---

## Designed for

| Audience | Why OpenReader |
|----------|---------------|
| **Students** | Read textbooks, annotate lecture notes, search across research papers — all offline. |
| **Professionals** | Review contracts, compare document versions, merge reports without uploading to any service. |
| **Researchers** | Index and search across PDF libraries, extract text, build automated PDF pipelines. |
| **Privacy-conscious users** | Full-featured PDF tool that never sends your documents anywhere. |
| **AI adopters** | Connect AI agents to your local documents for automated reading, searching, and processing. |

---

## Design Philosophy

> *"Software should respect your documents. They stay on your computer, under your control."*

OpenReader is built around a single idea: **a PDF reader should feel like a well‑made tool, not a web page.** The interface follows native Windows conventions — real menus, keyboard shortcuts, proper window management — with a refined dark theme (Tokyo Night‑inspired) and a clean light option. Every interaction is immediate, every feature discoverable without tutorials.

The focus is on reading and working with documents, not fighting the interface. Toolbar buttons have clear vector‑drawn icons, tabs are movable, zoom is instant, and the reading view puts your document first.

---

## Built With

🐍 Python &nbsp;&nbsp;·&nbsp;&nbsp; 🪟 Qt 6 &nbsp;&nbsp;·&nbsp;&nbsp; 📄 MuPDF &nbsp;&nbsp;·&nbsp;&nbsp; 🔍 SQLite &nbsp;&nbsp;·&nbsp;&nbsp; 👁️ Tesseract &nbsp;&nbsp;·&nbsp;&nbsp; 🤖 MCP &nbsp;&nbsp;·&nbsp;&nbsp; 📦 PyInstaller &nbsp;&nbsp;·&nbsp;&nbsp; 🏪 MSIX

---

## Version Journey

| Release | Date | Milestone |
|---------|------|-----------|
| **v1.2.4** | Jun 2026 | Toolbar icon redesign — all buttons use QPainter vector icons |
| **v1.2.3** | Jun 2026 | Reader UX polish — Fit Page on open, Ctrl+Mouse Wheel zoom |
| **v1.2.2** | Jun 2026 | Store submission fix — XML DOM patching, CI validation |
| **v1.2.1** | Jun 2026 | First Microsoft Store release candidate |
| **v1.2.0** | Jun 2026 | MSIX packaging, self‑update removed, App Installer integration |
| **v1.1.0** | Jun 2026 | MCP server — 14 AI agent tools, local document automation |
| **v1.0.6** | Jun 2026 | Single‑instance IPC, icon bundling, Qt file dialog fallback chain |
| **v1.0.0** | Jun 2026 | Stable release — reliability, security audit, regression suite |
| **v0.3.0** | May 2026 | Library search, PDF comparison, semantic search, modular refactor |
| **v0.2.0** | May 2026 | Annotations (highlight, underline, strikethrough, sticky notes) |
| **v0.1.0** | May 2026 | First release — PySide6 PDF reader, text search, merge/split/compress |

[Full changelog →](CHANGELOG.md)

---

## License

OpenReader is free software under the [GNU AGPLv3](LICENSE).

Copyright &copy; 2026 Sparsh Sam.

<p align="center">
  <a href="https://apps.microsoft.com/detail/9MXDVW2645LL"><img alt="Get it from Microsoft Store" src="https://img.shields.io/badge/Get%20it%20from%20Microsoft%20Store-ff255f?style=for-the-badge&logo=microsoft&logoColor=white"></a>
  &nbsp;
  <a href="https://github.com/sparshsam/openreader/releases/latest"><img alt="Download from GitHub" src="https://img.shields.io/badge/Download%20from%20GitHub-1a1b26?style=for-the-badge&logo=github&logoColor=white"></a>
</p>

---

*Last updated: June 2026*
