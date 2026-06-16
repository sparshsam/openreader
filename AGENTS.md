# Agent Maintenance Guide

This repository is a local-first desktop PDF utility. Keep maintenance changes boring, explicit, and release-safe.

## Product Boundaries

- Do not add new user-facing PDF features unless the task explicitly asks for them.
- Do not change the local-first privacy philosophy.
- Do not introduce network behavior beyond the explicit GitHub release update check.
- Treat PDFs as local/private user data.

## Release and Update Rules

- The updater depends on GitHub Release assets, not GitHub Actions artifacts.
- Canonical release assets must keep these exact names:
  - `PDFReader-by-Sparsh-Windows.zip`
  - `PDFReader-by-Sparsh-macOS-Apple-Silicon.zip`
  - `PDFReader-by-Sparsh-macOS-Intel.zip`
- Tag releases with `vMAJOR.MINOR.PATCH`.
- Packaged builds must inject the tag version into `main.py` via `scripts/inject_version.py`.
- Source builds may remain `-dev`.
- Update `RELEASE.md` if release mechanics change.

## Build and Test

- Keep `build-windows.yml`, `build-macos.yml`, and `security.yml` passing.
- Use `.github/workflows/release.yml` as the canonical distribution workflow.
- Do not rename status check jobs casually because `main` branch protection depends on their contexts.
- Run Python syntax checks after editing Python:

  ```powershell
  .\.venv\Scripts\python.exe -m py_compile main.py tools\create_icon.py scripts\inject_version.py
  ```

## Security Rules

- Preserve PDF pre-validation and resource limits.
- Keep dependency pins deliberate.
- Do not remove `pip-audit`, Bandit, or Dependabot without replacing them.
- Avoid exposing raw exception internals in user-facing dialogs.

## Documentation Rules

- README should describe shipped behavior only.
- Do not overclaim auto-update. It works for packaged builds only when canonical release assets are attached to the latest GitHub Release.
- Keep Mac signing/Gatekeeper caveats visible until releases are signed and notarized.

## MCP Server (AI Agent Integration)

The repository ships `pdfreader_lib/mcp_server.py` — an MCP server exposing all PDF operations as tools for AI agents.

**Maintenance rules:**
- `pdfreader_lib/mcp_server.py` must stay in sync with the feature set in `main.py`.
- When adding a new PDF operation to the GUI, add a matching MCP tool in `mcp_server.py`.
- Do not introduce network behavior beyond the existing GitHub release check and MCP transport.
- The MCP server is optional — it does not affect the desktop GUI or packaged builds.
- Keep the `requirements-mcp.txt` dependency list minimal (only `mcp` SDK is required for stdio mode).
