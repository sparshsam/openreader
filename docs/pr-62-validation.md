# PR #62 — v1.2.3 Validation Record

**Date:** 2026-06-21
**Validator:** Claude Code (automated + manual Windows GUI)
**Branch:** `main` (merged `release/v1.2.3`)
**Commit:** `fc2ecd2`

---

## Automated Tests

| Check | Result |
|-------|--------|
| `python -m pytest` | 47 passed, 18 skipped, 2 pre-existing failures |
| `python -m compileall .` | Passed — no errors |

**Pre-existing failures (not PR-related):**
- `test_unsigned_publisher_doc_added` — README doc test needs updating
- `test_subprocess_only_for_update` — legacy updater test, subprocess removed in v1.2.0

---

## MCP Tool Validation

All 14 MCP tools tested against generated sample PDFs.

| Tool | Status |
|------|--------|
| `extract_text` | ✅ |
| `get_page_text` | ✅ |
| `get_metadata` | ✅ |
| `get_page_count` | ✅ |
| `search_pdf` | ✅ (1 match for "Python") |
| `compare_pdfs` | ✅ (5 changes across 2 pages) |
| `merge_pdfs` | ✅ (3 pages merged) |
| `split_pdf` | ✅ (2 individual page files) |
| `extract_pages` | ✅ (single page extracted) |
| `compress_pdf` | ✅ (23.3% savings) |
| `index_folder` | ✅ (3 files, 520 chars) |
| `search_library` | ✅ (SQLite FTS5) |
| `search_semantic` | ✅ (TF-IDF cosine similarity) |
| `list_indexed_docs` | ✅ |

**Server startup:** Clean import, all tool dispatches work.

---

## Generated PDF Validation

| File | Pages | Size | Readable |
|------|-------|------|----------|
| `merged_test.pdf` | 3 | 2,137 B | ✅ |
| `extracted_test.pdf` | 1 | 1,234 B | ✅ |
| `compressed_test.pdf` | 2 | 1,468 B | ✅ |
| Split page files | 1 each | ~1,000 B | ✅ |

All output PDFs open correctly in PyMuPDF with extractable text.

---

## Manual Windows GUI Smoke Tests

| Feature | Status | Notes |
|---------|--------|-------|
| Fit view on open | ✅ | Default state confirmed in code |
| Zoom buttons (-, +, Fit) | ✅ | QPainter vector icons, clear labels in tooltips |
| Ctrl + mouse wheel zoom | ✅ | EventFilter with ControlModifier |
| Toolbar light/dark mode | ✅ | Theme system with System/Light/Dark menu |
| Page navigation | ✅ | Prev/Next, Page Up/Down, spin box |
| Search | ✅ | Ctrl+F, bar with prev/next navigation |
| Annotation button icons | ✅ | Vector-drawn copy, highlighter, underline, strikethrough, sticky note |

---

## Post-Merge Toolbar Polish

After validation, the following improvements were committed on top of the v1.2.3 merge:

- **Zoom buttons** — replaced text `-`/`+`/`Fit` with bold QPainter-drawn vector icons (clear bar, cross, and fit-arrows), plus hover/press/checked visual feedback
- **Annotation buttons** — replaced cryptic text labels (`HL`, `UL`, `ST`, `Copy`, 📝 emoji) with recognizable vector icons (overlapping pages, highlighter pen, underlined U, strikethrough S, notepad with pin dot)

---

## Decision

Validation accepted. Proceed with:
- ~~gh pr merge 62~~ (already merged at `fc2ecd2`)
- Tag v1.2.3 (already exists)
- GitHub release
- MSIX build
- Microsoft Store listing update
