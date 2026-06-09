# PDFReader by Sparsh — Roadmap

> Private desktop PDF tooling for local reading, annotation, search, diff,
> and workspace restore.

## Current — v0.3 (June 2026)

- [x] PDF reading and navigation with tabs
- [x] Annotation support (highlight, underline, strikethrough, sticky notes)
- [x] Full-text keyword search within a document
- [x] Library indexed search (SQLite FTS5 across folders)
- [x] PDF diff (side-by-side text-level comparison)
- [x] TF-IDF semantic search (offline, no ML deps)
- [x] Workspace session restoration
- [x] Dark/light theme (Auto, Light, Dark)
- [x] Auto-updater (Windows + macOS)
- [x] Windows installer (Inno Setup)
- [x] Release CI (Windows + macOS Apple Silicon + Intel)
- [x] Service-level test suite (pytest)
- [x] Repo governance (issue templates, PR template, support docs)

## Next

- [ ] macOS packaged build polish (notarization, signing)
- [ ] Performance optimizations for very large PDFs (500+ pages)
- [ ] Batch operations across multiple PDFs
- [ ] Improved annotation tools (freehand draw, shapes)
- [ ] Linux CI and packaged release

## Future

- [ ] Plugin or scripting interface for custom workflows
- [ ] More export formats (text, images, markdown)
- [ ] Accessibility improvements (screen reader support)
