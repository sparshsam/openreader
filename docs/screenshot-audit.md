# README Screenshot Audit

> Audit date: June 2026
> Target: `main` at `6c82278` (v1.0.6)

---

## Current State

| Screenshot | File | Size | Dimen | Age | Status |
|---|---|---|---|---|---|
| Main window | `assets/screenshot-main.png` | 1.4 MB | 1536×1024 | ~1 month | ✅ Exists, may be slightly outdated (v1.0.x era) |
| Search view | `assets/screenshot-search.png` | 1.6 MB | 1536×1024 | ~1 month | ✅ Exists, may be slightly outdated |

The README references both screenshots:
- Header image (line 2) uses `assets/screenshot-main.png`
- Screenshots section (lines 83–91) shows both images

## Missing Screenshots

The following views are **not captured** and would improve the README:

| Screenshot | Priority | Filename | README Placement | Notes |
|---|---|---|---|---|
| **Empty state** | High | `assets/screenshot-empty.png` | After the header image, before Features section | What the user sees on first launch — no PDFs open. Important for first impressions. |
| **Multi-tab view** | High | `assets/screenshot-tabs.png` | Near the multi-tab row in the Features table | Shows tab bar with multiple documents open, demonstrating tabbed PDF support. |
| **About dialog** | Medium | `assets/screenshot-about.png` | Near the end of the README, before License | Shows app version, credits, links. Helps with professional presentation. |
| **Windows installer / release page** | Low | `assets/screenshot-installer.png` | Not required for README; keep for release notes | Could show the installer setup or Releases page. Not essential for README. |

## TODO Checklist

- [ ] Capture **empty state** → save as `assets/screenshot-empty.png`
- [ ] Capture **multi-tab view** (2–3 PDFs open) → save as `assets/screenshot-tabs.png`
- [ ] Capture **About dialog** (File → About) → save as `assets/screenshot-about.png`
- [ ] (Optional) Capture **Windows installer** screenshot → save as `assets/screenshot-installer.png`
- [ ] Replace or retake `screenshot-main.png` if the current one looks dated after v1.1.0 UI polish
- [ ] Replace or retake `screenshot-search.png` if the search bar styling has changed
- [ ] Optimize each PNG to keep file sizes under ~300 KB (use `pngquant`, `oxipng`, or TinyPNG)
- [ ] Update README with new screenshot references using standard markdown image syntax

## How to Capture

1. Run the app in dev mode: `python main.py`
2. Resize the window to a clean 1280×800 or 1440×900 crop
3. Use any screen capture tool (Windows Snipping Tool, macOS Cmd+Shift+4)
4. Save as PNG to `assets/` with the filename from the checklist above
5. Optimize the PNG to keep the file size under ~300 KB
6. Reference in README with standard markdown image syntax:
   ```markdown
   ![Empty state](assets/screenshot-empty.png)
   ```

**Note:** Do not use automated screenshot tools from the CLI for this — the app needs to be running with real PDFs loaded for representative screenshots. Capture manually.

### PNG Optimization

The current screenshots (`screenshot-main.png` at 1.4 MB, `screenshot-search.png` at 1.6 MB) are significantly larger than ideal. Before adding new screenshots, optimize with one of:

- **`pngquant`**: lossy compression, reduces to ~200–300 KB with minimal visual loss
- **`oxipng`** (via `cargo install oxipng`): lossless recompression
- **TinyPNG.com**: web-based, good balance of compression and quality

Aim for ~200–300 KB per screenshot to keep the README load time reasonable.
