# Contributing

Thanks for your interest in improving PDFReader by Sparsh.

This project is source-available for non-commercial use. Contributions are
accepted under the same [PolyForm Noncommercial License 1.0.0](LICENSE)
used by the project.

## Local Setup

### Prerequisites

- Python 3.10+
- pip

### Install

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\Activate.ps1    # Windows PowerShell

python -m pip install -r requirements.txt
```

### Run

```bash
python main.py
python main.py path/to/document.pdf   # open a PDF directly
```

### Run Tests

Service-level tests live in the `tests/` directory and use `pytest`:

```bash
python -m pip install pytest
python -m pytest tests/ -v
```

> **Note:** If `tests/` is empty, the service test suite has not yet been
> merged to this branch. The commands above will still work once it lands.

Run the updater regression tests (standalone script, no pytest needed):

```bash
python tools/test_updater_asset_flow.py
```

### Code Quality

Python compile-check (covers all `.py` files):

```bash
python -m compileall . -q
```

Security scan (Bandit):

```bash
python -m pip install bandit
bandit -q -r main.py tools/
```

## Build on Windows

```powershell
.\scripts\build_windows.ps1
```

The executable is created at:

```text
dist\PDFReader by Sparsh.exe
```

## Build on macOS

```bash
chmod +x scripts/build_macos.sh
./scripts/build_macos.sh
```

The app bundle is created at:

```text
dist/PDFReader by Sparsh.app
```

## Pull Request Guidelines

- Keep the UI simple and native-looking (no web-style chrome).
- **Avoid network services** — PDFs should stay local and private.
- Test opening PDFs directly through command-line arguments.
- Test search, text selection, merge, split, and compress when changing
  document logic.
- Add or update service-level tests in `tests/` for any extracted logic
  in `pdfreader_lib/`.
- Run `python -m pytest tests/ -v` before opening a PR.
- Update `CHANGELOG.md` for any user-facing change.

## Issue Templates

Use the appropriate GitHub issue template:

- [Bug Report](.github/ISSUE_TEMPLATE/bug_report.yml)
- [Feature Request](.github/ISSUE_TEMPLATE/feature_request.yml)
- [Documentation Issue](.github/ISSUE_TEMPLATE/documentation_issue.yml)

## License

By contributing, you agree that your contributions will be licensed under
the same [PolyForm Noncommercial License 1.0.0](LICENSE) as the project.
