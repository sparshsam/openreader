# Contributing

Thanks for your interest in improving PDFReader by Sparsh.

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
dist\PDFReader by Sparsh.exe
```

## Pull Requests

- Keep the UI simple and native-looking.
- Avoid network services; PDFs should stay local.
- Test opening PDFs directly through command-line arguments.
- Test search, text selection, merge, split, and compress behavior when changing document logic.
