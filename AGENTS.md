# Agent Maintenance Guide

This repository is a local-first desktop PDF utility. Keep maintenance changes boring, explicit, and release-safe.

## Product Boundaries

- Do not add new user-facing PDF features unless the task explicitly asks for them.
- Do not change the local-first privacy philosophy.
- Do not introduce network behavior beyond the explicit GitHub release update check (update detection only — no downloading or applying updates).
- Treat PDFs as local/private user data.

## Release and Update Rules

- The app detects updates via GitHub API and opens the releases page in a browser. It does not download or install updates.
- Canonical release assets must keep these exact names:
  - `OpenReader-Windows.zip`
  - `OpenReader-macOS-Apple-Silicon.zip`
  - `OpenReader-macOS-Intel.zip`
  - `OpenReader.msix` (MSIX package for Store submission/advanced use)
  - `OpenReader-Setup.exe` (legacy Inno Setup installer)
- The Microsoft Store identity (`SparshSam.OpenReader`) is frozen — never change.
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
- OpenReader does not install updates itself. Store installations update automatically; GitHub MSIX installations are manual.
- Keep Mac signing/Gatekeeper caveats visible until releases are signed and notarized.

## MCP Server (AI Agent Integration)

The repository ships two MCP server entry points:

1. **`pdfreader_lib/mcp_server.py`** — bundled with the main app. 14 tools, stdio + SSE transport.
2. **`packages/mcp-server/`** — standalone pip package `openreader-mcp`. Install via `pip install openreader-mcp`, run with `python -m openreader_mcp`.

**Improvements made (June 2026):**
- All 14 tool descriptions rewritten as AI-optimized sentences (what it does, what it returns, when to use vs alternatives).
- Error messages tiered by type: validation errors, file-not-found, missing params, unexpected errors — each tells the agent what to fix.
- 43 tests added at `tests/test_mcp_server.py` covering registration, input validation, output shape, and error handling.
- Standalone package created at `packages/mcp-server/` — users install with one `pip install` command, no repo clone needed.

**Maintenance rules:**
- `pdfreader_lib/mcp_server.py` must stay in sync with the feature set in `main.py`.
- When adding a new PDF operation to the GUI, add a matching MCP tool.
- Do not introduce network behavior beyond the existing GitHub release check (update detection only — no download) and MCP transport.
- The MCP server is optional — it does not affect the desktop GUI or packaged builds.
- Keep `requirements-mcp.txt` minimal (only `mcp` SDK required for stdio mode).
- When adding a tool to the bundled server, add it to `packages/mcp-server/` too.
- Agent config uses `"args": ["-m", "openreader_mcp"]` for standalone, `"args": ["-m", "pdfreader_lib.mcp_server"]` for bundled.

## Landing Page & Docs

OpenReader has a showcase landing page at **https://reader.kovina.org** (Cloudflare Pages).

- **Source:** `site/` — static HTML + CSS. Huninn font, `#ff255F` accent, dark/light toggle.
- **Features:** Hero → Story → SVG feature icons → MCP/AI section with copy-paste prompt → CTA.
- **MCP prompt box:** Users click Copy, paste to any AI assistant to set up `python -m openreader_mcp`.
- **Docs page:** `site/docs/index.html` — full MCP setup guide for Claude Code, Desktop, Cursor.
- **Deploy:** Auto via `.github/workflows/deploy-site.yml` on push to `main` touching `site/`. Manual via `npx wrangler pages deploy site/ --project-name reader`.
