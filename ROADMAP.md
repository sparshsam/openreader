# PDFReader by Sparsh — Roadmap

> Stable, local-first desktop PDF utility with AI agent integration.

## ❄️ v1.1.0 — Current Stable (Frozen)

v1.1.0 ships the MCP server for AI agent integration (14 programmatic PDF tools), along with a full README features refresh. It will receive **only critical bug fixes**.

See the [v1.2.0 Plan](docs/v1.2.0-plan.md) for upcoming scope.

## ✓ v1.0.0 — Shipped

- [x] PDF reading and navigation (single-page, zoom, fit-width)
- [x] Multi-tab document management
- [x] Dark mode (Auto/Light/Dark, Catppuccin Mocha)
- [x] Full-document keyword search with match navigation
- [x] Text selection and copy (native text + OCR fallback)
- [x] Annotations (highlight, underline, strikethrough, sticky notes)
- [x] PDF tools (merge, split, compress)
- [x] Library full-text search (SQLite FTS5)
- [x] PDF version comparison (side-by-side diff)
- [x] Semantic search (TF-IDF)
- [x] Workspace session restore
- [x] Recent files
- [x] Auto-update (Windows ZIP, macOS ZIP)
- [x] Windows installer (Inno Setup, file association)
- [x] macOS builds (Apple Silicon + Intel)
- [x] GitHub Actions CI, release, and security workflows
- [x] Regression test suite
- [x] Security audit (bandit, pip-audit)
- [x] Backup-before-write crash safety
- [x] Known limitations documented

## ✓ v1.1.0 — Shipped

- [x] MCP server for AI agent PDF integration (14 tools: extract, search, compare, merge, split, compress, index)
- [x] README features table synced with code
- [x] README tech stack expanded
- [x] AGENTS.md maintenance rules for MCP server

## Future

Items under consideration — not committed or scheduled.

- [ ] Premium visual polish (tab styling, recent-files start screen, sidebar thumbnails)
- [ ] macOS DMG packaging
- [ ] Signed Windows binaries
- [ ] Local AI summarization (Ollama / llama.cpp)
- [ ] Cross-platform Linux support
- [ ] Plugin system for community tools
- [ ] PDF timeline / version history
- [ ] Cryptographic document anchoring (Base blockchain)
- [ ] Stronger sandboxing guidance
