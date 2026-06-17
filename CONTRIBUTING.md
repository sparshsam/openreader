# Contributing

Thanks for your interest in improving OpenReader.

This project is source-available for non-commercial use. Contributions are accepted under the same PolyForm Noncommercial License 1.0.0 used by the project.

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

## Build on Windows

```powershell
.\scripts\build_windows.ps1
```

The executable is created at:

```text
dist\OpenReader.exe
```

## Build on macOS

```bash
chmod +x scripts/build_macos.sh
./scripts/build_macos.sh
```

The app bundle is created at:

```text
dist/OpenReader.app
```

## Pull Requests

- Keep the UI simple and native-looking.
- Avoid network services; PDFs should stay local.
- Test opening PDFs directly through command-line arguments.
- Test search, text selection, merge, split, and compress behavior when changing document logic.
