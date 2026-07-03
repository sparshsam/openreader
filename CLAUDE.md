# OpenReader — Agent Instructions

## Overview

**Latest update:** v1.2.5 — Open Product Family branding alignment (2026-07-02)

Privacy-first, local-only desktop PDF utility for Windows.
macOS experimental; Linux unsupported.

## Version History

| Version | Date | Summary |
|---------|------|---------|
| v1.2.5 | 2026-07-02 | Open Product Family branding alignment — header lockup, docs/BRANDING.md, icon generation pipeline, dark/light theme icon |
| v1.2.4 | 2026-06-28 | (previous release) |

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
- Update `docs/RELEASE.md` if release mechanics change.

## Workflow

1. Branch from `main`. Branch naming: `<type>/<description>`.
2. PR for every merge. No direct pushes to `main`.
3. Run lint/tests before creating a PR.
4. Do not change application behavior beyond what the task requests.
5. Do not add new features unless explicitly asked.

## Documentation Rules

- README should describe shipped behavior only.
- docs/Architecture.md is the canonical architecture reference.
- docs/VERSIONING.md documents the versioning scheme.
- Keep CHANGELOG.md updated per Keep a Changelog format.
- Keep Mac caveats visible for experimental platform status.

## Security Rules

- Validate `.gitignore` coverage for `.env` and secret files before every commit.
- Preserve PDF pre-validation and resource limits.
- Keep dependency pins deliberate.
- Do not expose raw exception internals in user-facing dialogs.
- If a secret is accidentally exposed, report immediately. Do not fix silently.

## MCP Server

The repository ships two MCP server entry points:

1. **`pdfreader_lib/mcp_server.py`** — bundled with the main app source. 14 tools, stdio + SSE transport.
   - All tool descriptions rewritten as AI-optimized sentences (what, returns, when-to-use).
   - Error messages are tiered: validation, file-not-found, missing params, unexpected errors.
   - Tests at `tests/test_mcp_server.py` — 43 tests covering registration, validation, output shape, error handling.

2. **`packages/mcp-server/`** — standalone pip package `openreader-mcp`. Install via `pip install openreader-mcp`, run with `python -m openreader_mcp`.
   - Mirrors the bundled server but imports bundled `_search_index` and `_comparison` modules.
   - `pyproject.toml` defines metadata. Update whenever `pdfreader_lib/mcp_server.py` gains new tools.

### Rules

- `pdfreader_lib/mcp_server.py` must stay in sync with `main.py`'s feature set.
- When adding a new PDF operation to the GUI, add a matching MCP tool.
- Keep `requirements-mcp.txt` minimal (only `mcp` SDK required for stdio mode).
- When adding a tool to the bundled server, add it to `packages/mcp-server/` too.
- Agent config uses `"args": ["-m", "openreader_mcp"]` (standalone) or `"args": ["-m", "pdfreader_lib.mcp_server"]` (bundled).

## Design Playbooks

Three canonical playbooks govern all design and architecture decisions. Loaded at `docs/playbooks/`:

| File | What it covers |
|------|---------------|
| `docs/playbooks/PRODUCT_ARCHITECTURE_PLAYBOOK.md` | Structural canvas — spatial system, grids, containers, responsive, layout archetypes, reading tempo, motion |
| `docs/playbooks/DESIGN_PLAYBOOK.md` | Visual design — machine metaphor, color, typography, component rules, buttons, navigation, states |
| `docs/playbooks/MCP-SERVER-BUILD-GUIDE.md` | MCP server blueprint — SHA-256 token auth, Streamable HTTP, user isolation, tool patterns, testing |

**Every design or architectural decision starts from these playbooks first.**

## Branding Architecture

### Hierarchy

```
KOVINA          Parent ecosystem     → kovina.org/standards/KOVINA_MANIFESTO.md
  ↓
OPEN            Product family       → kovina.org/standards/BRAND_GUIDELINES.md
  ↓
Reader          Individual product   → docs/BRANDING.md
```

- **OPEN has no icon.** No symbol, no badge, no monogram. Typography only.
- The application icon belongs only to OpenReader, never to OPEN.
- Do not merge the icon into the typography lockup.
- Do not create a combined logo mark.
- The header lockup is: `[icon] OPEN / Reader` (stacked, icon on left).
- Never redesign the header lockup without explicit instruction.
- Kovina standards are authoritative. OpenReader inherits them.
- OpenPalette is the canonical reference implementation for the Open Product Family branding.
- Brand accent: `#ff255F` pink-red.
- See [docs/BRANDING.md](docs/BRANDING.md) for complete product-specific branding documentation.

### Icon Generation Pipeline (v1.2.5)

- **Source art:** `openreader_light_mode.png` (1024x1024 PNG)
- **Resampling:** Lanczos (high-quality) via `scripts/generate-icons.js`
- **Total assets:** 155 across all target formats
- **Formats:** Windows ICO (multi-resolution), MSIX assets, Android adaptive icons, iOS/macOS app icons, Web/PWA favicons (incl. SVG), social OG image (1200x630), GitHub avatar/profile icons, header icon for app chrome
- **Automation:** GitHub Actions workflow `.github/workflows/generate-icons.yml` runs on icon source change detection

### Header Lockup

```html
<a href="/" class="logo" aria-label="OpenReader home">
  <img src="/openreader-icon.svg" alt="" class="logo-icon" />
  <div class="logo-text">
    <span class="logo-open">OPEN</span>
    <span class="logo-product">Reader</span>
  </div>
</a>
```

- OPEN: uppercase, bold, 0.06em tracking, muted 50% opacity
- Reader: title case, medium weight, primary text color
- Icon: 28px mobile / 32px desktop, 6px border-radius
- OpenPalette alignment (v1.2.5): product Reader `font-medium -mt-0.5 leading-tight`; icon wrapper `margin-top: -1px` for optical centering against text ascender
- Themed icon (v1.2.5): CSS `transition: all 0.3s ease` on app chrome icon for dark/light mode switching; same source image for both modes until dark-specific art is created

## Landing Page

OpenReader's showcase landing page at **https://reader.kovina.org**, hosted on Cloudflare Pages.

- **Source:** `site/` — static HTML + CSS, no build step.
- **Font:** Huninn (rounded sans-serif), hosted TTF.
- **Accent:** `#ff255F` (pink/red).
- **Dark mode toggle:** sun/moon icon at right screen edge, persists to localStorage.
- **Features:** SVG icons replace numbered list. Hero icon at 512×512px.
- **Nav:** logo left, links centered, theme toggle far right. Seamless (no border).
- **Sections:** Hero → Story → Features (SVG icons) → MCP/AI (with copy-paste prompt) → Ribbon (#ff255F filled) → CTA → Footer.
- **MCP prompt box:** Click-to-copy JSON config users paste to any AI assistant.
- **Docs page:** `site/docs/index.html` — full MCP setup guide for Claude Code, Desktop, Cursor.

### Deploy

- **Manual:** `npx wrangler pages deploy site/ --project-name reader` (requires `CLOUDFLARE_API_TOKEN`).
- **Auto:** `.github/workflows/deploy-site.yml` deploys on push to `main` touching `site/`.

## GitHub Repo

- **Website URL:** `https://reader.kovina.org`
- **Description:** Includes Microsoft Store ID (`9MXDVW2645LL`) for discoverability.
- **Release page:** v1.2.5 release body has Store link at top + direct download assets below.

## App Identity Card

| Property | Definition |
|----------|-----------|
| Core metaphor | Reading desk / Document workbench |
| Primary brand color | #ff255F (accent) |
| Emotional tone | Focused, calm |
| Main user action | Read & annotate PDFs |
| Navigation | Features · AI Access · Docs · Store · GitHub |
