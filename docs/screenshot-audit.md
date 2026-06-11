# README Screenshot Audit

> Audit date: July 2026
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

| Screenshot | Priority | Notes |
|---|---|---|
| **Empty state** | High | What the user sees on first launch — no PDFs open. Important for first impressions. |
| **Multi-tab view** | High | Shows tab bar with multiple documents open, demonstrating tabbed PDF support. |
| **About dialog** | Medium | Shows app version, credits, links. Helps with professional presentation. |
| **Windows installer / release page** | Low | Could show the installer setup or Releases page. Not essential for README. |

## TODO Checklist

- [ ] Capture **empty state**: launch app with no PDFs loaded, screenshot the full window
- [ ] Capture **multi-tab view**: open 2–3 PDFs in tabs, screenshot with visible tab bar
- [ ] Capture **About dialog**: File → About, screenshot the dialog
- [ ] (Optional) Capture **Windows installer** screenshot
- [ ] Replace or add updated `screenshot-main.png` if the current one looks dated
- [ ] Replace or add updated `screenshot-search.png` if the search bar styling has changed
- [ ] Update README with new screenshot references

## How to Capture

1. Run the app in dev mode: `python main.py`
2. Resize the window to a clean 1280×800 or 1440×900 crop
3. Use any screen capture tool (Windows Snipping Tool, macOS Cmd+Shift+4)
4. Save as PNG to `assets/` with a descriptive name: `screenshot-empty.png`, `screenshot-tabs.png`, etc.
5. Reference in README with standard markdown image syntax:
   ```markdown
   ![Empty state](assets/screenshot-empty.png)
   ```

**Note:** Do not use automated screenshot tools from the CLI for this — the app needs to be running with real PDFs loaded for representative screenshots. Capture manually.
