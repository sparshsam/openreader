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

**Is it fixed?** Yes — v1.0.2+ fixes the updater to write to your temporary files folder (`%TEMP%`) instead, which does not require administrator permission. Once v1.0.3 is installed, all future updates will work automatically.

**One-time manual recovery** — you need to install v1.0.3 manually, then the updater will work from then on:

1. **Download the installer** from the [v1.0.3 release page](https://github.com/sparshsam/pdfreader-by-sparsh/releases/tag/v1.0.3) — use `PDFReader-by-Sparsh-Setup.exe`.
2. **Close PDFReader** if it is running (File → Quit, or close the window).
3. **Right-click the installer** and choose **Run as Administrator**.
4. **Install over the existing version** — use the same install location (`C:\Program Files\PDFReader by Sparsh` by default).
5. **Launch PDFReader** — it will show v1.0.3 in the About dialog.
6. **Future updates will work normally** — the updater no longer needs admin access.

If you are unsure about any step, you can also download the portable ZIP (`PDFReader-by-Sparsh-Windows.zip`), extract it anywhere, and run the app from there without affecting your installed version.

## Windows installer

PDFReader ships a Windows Inno Setup installer (`PDFReader-by-Sparsh-Setup.exe`). This section explains its behavior.

### Admin / UAC

The installer requires administrator privileges. When you run it, Windows will show a **User Account Control (UAC)** prompt asking for permission. This is expected — the installer needs admin rights to:

- Install or update files under `C:\Program Files\PDFReader by Sparsh`
- Register the app as a PDF file handler in the Windows Registry
- Create Start Menu and desktop shortcuts

If you do not see a UAC prompt, the installer was not launched with admin rights. Right-click the `.exe` and choose **Run as Administrator**.

> **Note for portable users:** The ZIP archive (`PDFReader-by-Sparsh-Windows.zip`) does not require any installer or admin rights. Extract it anywhere and run `PDFReader by Sparsh.exe` directly.

### Install path

Default: `C:\Program Files\PDFReader by Sparsh`

You can change the install folder during setup. All app files are placed inside this single folder — nothing else is written to the system outside of shortcuts and registry entries.

### What is installed

| Item | Location |
|------|----------|
| Main executable | `{install}\PDFReader by Sparsh.exe` |
| Internal libraries | `{install}\_internal\` |
| Start Menu shortcut | `Start Menu → PDFReader by Sparsh` |
| Desktop shortcut | Optional (checked by default) |
| PDF file association | Registry — `.pdf` opens with PDFReader |
| Add/Remove Programs entry | Windows Apps & Features |

### Uninstaller

To uninstall, use **Windows Settings → Apps → Installed apps → PDFReader by Sparsh → Uninstall**.

The uninstaller removes:

- All installed app files (`PDFReader by Sparsh.exe`, `_internal\` folder)
- Start Menu shortcut and desktop shortcut (if created)
- PDF file association registry keys owned by the app
- The app folder (if empty after removal)

The uninstaller **preserves**:

- Your PDF documents and files (never touched)
- User settings (stored in your Windows user account, not in the app folder)
- Library search index (SQLite database — preserved across install/uninstall)

If you want a completely clean removal of all settings, delete these folders after uninstalling:

```
%APPDATA%\Sparsh\PDFReader by Sparsh\     (settings)
%TEMP%\PDFReader-Updates\                 (update cache)
```

### Installing over an existing version

The installer supports installing over an existing version:

1. The installer will detect that PDFReader is already installed.
2. If PDFReader is running, it will be closed automatically before the install begins.
3. Your user settings and library index are preserved (stored separately from the app folder).
4. Choose **Yes** when asked to confirm the overwrite.

### Troubleshooting

**"Access denied" or "Permission denied" during install:**
Right-click the installer and choose **Run as Administrator**.

**"File in use" error:**
Close PDFReader first (File → Quit, or right-click taskbar → Close window). The installer has an `AppMutex` set, but some file-lock scenarios may still require a manual close.

**"Failed to launch after install":**
Try running PDFReader from the Start Menu. If it still fails, reboot once — this resolves any file-lock edge cases from the update process.
