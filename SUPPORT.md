# Support

PDFReader by Sparsh is a local-first desktop PDF utility. Support is best-effort and focused on reproducible bugs, packaging issues, documentation, and release verification.

## Before Opening An Issue

- Check the [README](README.md), [RELEASE.md](RELEASE.md), and existing issues.
- Include your operating system, installation method, and app version.
- Do not upload private PDFs or sensitive document screenshots.

## Good Issue Reports

- Describe the PDF operation involved: reading, search, annotation, merge, split, extract, compression, or update.
- Include a minimal public sample PDF only when it is safe to share.
- Mention whether the issue occurs in a packaged build or source build.

For security concerns, follow [SECURITY.md](SECURITY.md).

## Windows v1.0.0/v1.0.1 updater recovery

If you are using PDFReader v1.0.0 or v1.0.1 on Windows and see this error when checking for updates:

```
[Errno 13] Permission denied: C:\Program Files\PDFReader by Sparsh\_update_*.bat
```

**What happened:** The old updater tried to write a temporary update script inside the `Program Files` folder, but normal users don't have permission to write there.

**Why it happens:** This is a bug in the updater code of v1.0.0 and v1.0.1. The same files were used successfully in those releases, so the installer placed PDFReader in `Program Files` as expected — but the updater could not write additional files there.

**Is it fixed?** Yes — v1.0.2 fixes the updater to write to your temporary files folder (`%TEMP%`) instead, which does not require administrator permission. Once v1.0.2 is installed, all future updates will work automatically.

**One-time manual recovery** — you need to install v1.0.2 manually, then the updater will work from then on:

1. **Download the installer** from the [v1.0.2 release page](https://github.com/sparshsam/pdfreader-by-sparsh/releases/tag/v1.0.2) — use `PDFReader-by-Sparsh-Setup.exe`.
2. **Close PDFReader** if it is running (File → Quit, or close the window).
3. **Right-click the installer** and choose **Run as Administrator**.
4. **Install over the existing version** — use the same install location (`C:\Program Files\PDFReader by Sparsh` by default).
5. **Launch PDFReader** — it will show v1.0.2 in the About dialog.
6. **Future updates will work normally** — the updater no longer needs admin access.

If you are unsure about any step, you can also download the portable ZIP (`PDFReader-by-Sparsh-Windows.zip`), extract it anywhere, and run the app from there without affecting your installed version.
