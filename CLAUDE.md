# OpenReader — Agent Instructions

## Overview

Privacy-first, local-only desktop PDF utility for Windows.
macOS experimental; Linux unsupported.

## Architecture Constraints

1. **Local-first.** No cloud dependency. No network calls beyond the optional GitHub release update check (no downloads).
2. **Privacy by design.** Treat PDFs as local/private user data. Never upload or transmit document content.
3. **Cross-platform** (Windows primary, macOS experimental).

## Distribution and Updates

- **Microsoft Store** (live) — automatic updates through the Store.
- **GitHub MSIX** — advanced users, unsigned, requires Developer Mode for sideloading.
- **Legacy Setup.exe** — manual recovery only.
- The app detects updates via GitHub API (opens browser). It never downloads or runs installers.

## Frozen Identity — Never Change

- Identity Name: `SparshSam.OpenReader`
- Publisher: `CN=E6186421-BF8A-47E0-A89C-0F513DFF91C0`
- PFN: `SparshSam.OpenReader_yh0byntbzd2qw`
- Store ID: `9MXDVW2645LL`

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

- Canonical release asset names:
  - `OpenReader-Windows.zip`
  - `OpenReader-macOS-Apple-Silicon.zip`
  - `OpenReader-macOS-Intel.zip`
  - `OpenReader.msix` (MSIX package)
  - `OpenReader-Setup.exe` (legacy installer)
- MSIX identity (`SparshSam.OpenReader`) is frozen — never change.
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
- Keep Mac caveats visible for experimental platform status.

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
