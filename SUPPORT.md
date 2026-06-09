# Support

PDFReader by Sparsh is a local-first desktop PDF utility. Support is
best-effort and focused on reproducible bugs, packaging issues,
documentation, and release verification.

## Before Opening an Issue

- Check the [README](README.md), [RELEASE.md](RELEASE.md),
  [ROADMAP.md](ROADMAP.md), and existing [issues](https://github.com/sparshsam/pdfreader-by-sparsh/issues).
- Include your operating system, installation method, and app version
  (visible in **Help → About**).
- **Do not upload private PDFs or sensitive document screenshots.**

## Good Issue Reports

- Describe the PDF operation involved: reading, search, annotation, merge,
  split, extract, compression, or update.
- Include a minimal public sample PDF only when it is safe to share.
- Mention whether the issue occurs in a **packaged build** or **source build**.

For security concerns, follow [SECURITY.md](SECURITY.md).

## Supported Platforms

| Platform | Support Status |
|----------|---------------|
| **Windows 10 / 11** (x64) | ✅ Full — packaged installer + auto-update via ZIP |
| **macOS 14+** (Apple Silicon) | ✅ Builds available; auto-update via ZIP |
| **macOS 14+** (Intel) | ✅ Builds available; auto-update via ZIP |
| **Linux** | ⚠️ Source builds only — no packaged release |

## Known Limitations

| Area | Limitation |
|------|------------|
| **Search** | Keyword search only within the currently open PDF. Cross-document search requires the Library feature with indexed folders. |
| **Semantic search** | TF-IDF based; no LLM or embedding model integration. Results may miss meaning-based matches. |
| **OCR** | Requires Tesseract OCR system installation. OCR text is cached per page (max 3 pages). |
| **Compression** | Re-saves with maximum PyMuPDF compression settings. Some PDFs may not shrink significantly. |
| **Split** | Limited to 1,000 pages per operation. |
| **Render** | Max render size 80 MP — very large PDFs may show a warning instead of rendering. |

## Updater Limitations

- The auto-updater only supports **packaged builds** (PyInstaller onedir).
- **Source builds** (running `python main.py`) see the update prompt but
  must update via `git pull` and rebuild manually.
- The updater only checks the **latest GitHub release** — it cannot skip
  multiple versions or apply partial updates.
- Windows updates replace `_internal/` and the main `.exe`. User data
  (settings, library index) is stored separately under `~/.pdfreader/` and
  is preserved.
- macOS Apple Silicon and Intel have separate update assets. The updater
  selects the correct one based on `platform.machine()`.

## Unsupported Workflows

- **Encrypted / password-protected PDFs** — not supported by the reader.
- **Fillable form fields** — rendered as static content; no form filling.
- **Digital signatures** — not parsed or verified.
- **Edit-in-place** — annotations are saved incrementally, but text/content
  editing is not supported.
- **Network / cloud integration** — the app intentionally has no upload,
  sync, or cloud storage features.
- **Mobile / tablet / web** — desktop-only (Qt/PySide6).
