# Known Limitations

These are accepted limitations of the current release. They are documented here so users and contributors know what to expect rather than discovering them through frustration.

## Rendering

- **No thumbnail/prefetch.** Adjacent pages are not pre-rendered. Page navigation always waits for `fitz.get_pixmap()` to complete before displaying the result.
- **No worker thread rendering.** All rendering happens on the main (UI) thread. Very large pages (>80 megapixels) or very high zoom levels may cause brief UI stutters.
- **No LRU render cache.** Pages are re-rendered on every visit. If you navigate back and forth between two pages, both are rendered from scratch each time.
- **No progressive loading.** The entire PDF is opened in memory before the first page appears. Very large files (>2000 pages) may have a noticeable open delay.

## Search

- **Keyword search is single-threaded.** The current search scans pages one-by-one on the main thread. Large documents (1000+ pages) may show a brief pause during search. The progress bar updates every 50 pages to keep the user informed.
- **Search is capped at 20,000 matches.** Very dense search terms will stop after reaching this limit to avoid memory issues.

## Memory

- **Log file grows unboundedly.** The app debug log at `%TEMP%\PDFReader-Logs\app-debug.log` grows indefinitely. Manual cleanup is required.
- **No backup rotation.** The safety backup system (`_save_with_backup`) only keeps one `.bak` file per document. Multiple saves overwrite the same backup. This is intentional — the backup is meant for crash recovery, not version history.

## macOS

- **Unsigned builds.** Both GitHub Actions builds and local builds are unsigned. macOS Gatekeeper will warn before running. The app needs Apple Developer ID code signing and notarization for smooth public distribution.
- **macOS is experimental.** The app is developed and tested on Windows. macOS builds are published for community testing but are not stable.

## Windows

- **SmartScreen warning.** Community builds are not code-signed. Windows may show a SmartScreen warning on first run.
- **Cross-filesystem rename.** The atomic save pattern (`shutil.move` to temp file) is only truly atomic when the temp file is on the same filesystem as the target file. In normal use this is always the case.

## Filesystem Safety

- **Backup file is left on success.** The `.pdf.bak` file is removed on successful save, but if the app crashes after the copy and before the cleanup, a stale `.pdf.bak` may remain. The app will attempt to auto-restore it on the next open.
- **No unencrypted fallback.** Password-protected PDFs are rejected with a clear error message. The app does not attempt decryption.

## Library / Comparison

- **Library modules are optional.** The `pdfreader_lib` package (library full-text search, PDF comparison, semantic search) is only loaded if installed. Without it, the Compare and Library buttons are grayed out. This is by design — the core PDF reader works without these modules.
- **Semantic search requires an indexed library.** The TF-IDF index must be built by adding folders via the Library dialog before semantic search returns results.

