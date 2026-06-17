# PDF Reader by Sparsh — Agent Instructions

## Overview

Private, local-first desktop PDF tool for reading, annotation, search, diff, and workspace restore.
Windows primary target; macOS source-build only.

## Architecture Constraints

1. **Local-first.** No cloud dependency. No network calls beyond the explicit GitHub release update check.
2. **Privacy by design.** Treat PDFs as local/private user data. Never upload or transmit document content.
3. **Cross-platform** (Windows primary, macOS secondary).

## Commands

### Development
```powershell
# Windows — run from source
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py

# Build packaged executable
.\scripts\build_windows.ps1
```

### Build verification
```bash
# Syntax check
python -m py_compile main.py tools/create_icon.py scripts/inject_version.py
```

### Testing
```bash
python -m pytest tests/ -v
```

## Release Rules

- Canonical release asset names must be preserved:
  - `PDFReader-by-Sparsh-Setup.exe`
  - `PDFReader-by-Sparsh-Windows.zip`
  - `PDFReader-by-Sparsh-macOS-Apple-Silicon.zip`
  - `PDFReader-by-Sparsh-macOS-Intel.zip`
- Tag releases with `vMAJOR.MINOR.PATCH`.
- Version injected from tag via `scripts/inject_version.py`.
- Source builds remain `-dev`.
- Update `RELEASE.md` if release mechanics change.

## Workflow

1. Branch from `main`. Branch naming: `<type>/<description>`.
2. PR for every merge. No direct pushes to `main`.
3. Run lint/tests before creating a PR.
4. Do not change application behavior beyond what the task requests.
5. Do not add new features unless explicitly asked.

## Documentation Rules

- README should describe shipped behavior only.
- ARCHITECTURE.md is the canonical architecture reference.
- VERSIONING.md documents the versioning scheme.
- Keep CHANGELOG.md updated per Keep a Changelog format.
- Keep Mac signing/Gatekeeper caveats visible until releases are signed.

## Security Rules

- Validate `.gitignore` coverage for `.env` and secret files before every commit.
- Preserve PDF pre-validation and resource limits.
- Keep dependency pins deliberate.
- Do not expose raw exception internals in user-facing dialogs.
- If a secret is accidentally exposed, report immediately. Do not fix silently.

## MCP Server

The repository ships `pdfreader_lib/mcp_server.py` — an MCP server exposing PDF operations as tools for AI agents.

- `pdfreader_lib/mcp_server.py` must stay in sync with `main.py`'s feature set.
- When adding a new PDF operation to the GUI, add a matching MCP tool.
- Keep `requirements-mcp.txt` minimal (only `mcp` SDK required for stdio mode).
