# Agent Maintenance Guide — OpenReader

OpenReader is Kovina's **privacy-first, local-only** desktop PDF utility (Windows primary; macOS experimental; Linux unsupported). Read, annotate, search, compare, and from v1.3.0 **fill forms, add text, sign visually, and insert images** — all locally, with no accounts, subscriptions, cloud processing, telemetry, uploads, or internet access beyond the optional GitHub update check.

Keep changes boring, explicit, and release-safe. Full architecture and command reference: [CLAUDE.md](CLAUDE.md); canonical architecture: [docs/Architecture.md](docs/Architecture.md).

## Current State (2026-11-08)

| Item | Value |
|---|---|
| **Latest published release** | **v1.2.8** — merge `57c29ea`, tag `v1.2.8`, release `https://github.com/sparshsam/openreader/releases/tag/v1.2.8` |
| **Current development version** | **v1.3.0 — Fill, Edit & Sign** — implemented, **NOT approved for release** |
| **Active branch** | `feat/v1.3.0-fill-edit-sign` |
| **Open PR** | **#107** — implementation head **`7106ae5`**; the documentation-handoff commit follows on the same branch/PR |
| **Backup branch** | `wip/v1.3.0-form-intelligence` at **`60038ca`** — unchanged; do not modify |
| **Tests** | **261 passed, 18 skipped**; CI green on the implementation head |
| **Installed app** | Untouched; no Store submission |
| **Branch protection** | PR required; 0 required approvals; required checks `Validate`, `Security`, `build`; admins enforced; force pushes/deletions blocked |

## Immediate Next Task — next session only

**v1.3.0 is implemented but NOT approved for release.** Begin the next session with **isolated Windows runtime testing**:

1. Prepare an isolated v1.3.0 Windows dev environment (separate source copy, private venv/profile).
2. Preserve the installed OpenReader application and all previous dev environments.
3. Launch the real desktop GUI for Sparsh's manual testing.
4. Prepare realistic fixtures: interactive forms (all field types), non-interactive forms, long/multi-page PDFs, signed/encrypted samples, images/signatures.
5. Test form filling, freeform text/formatting, signature draw/type/import, images, Save, Save As, reopen, flattened export.
6. Verify continuous-scroll editing (scroll, zoom, resize, tabs).
7. Cross-viewer checks where possible (Acrobat/Edge/Chrome), including text selectability and preservation of links/bookmarks/metadata.
8. Fix defects, re-run tests/CI, then request release approval.

Do not merge, tag, publish, or submit to the Store until Sparsh approves the runtime results.

## Product Boundaries & Kovina Standards

- **Privacy-first / local-first:** never upload or transmit PDFs, signatures, or user data; no accounts, subscriptions, or cloud processing.
- No network behavior beyond the optional GitHub update check (detection only) and the optional local MCP transport.
- Treat PDFs as private user data. Signature data is local-only.
- Kovina/OPEN branding: OPEN is typography only; the app icon belongs to OpenReader; brand accent `#ff255F`; never redesign the header lockup without instruction. See `docs/BRANDING.md`.
- Design/architectural decisions start from `docs/playbooks/`.
- Do not add user-facing features or refactor working code unless the task explicitly asks.

## Editing & Form Rules (v1.3.0+)

- `pdfreader_lib/form_fields.py` and `pdfreader_lib/edit_objects.py` are **Qt-free**. GUI logic (overlays, inline editor, signature dialog, coordinate conversion) belongs in `pdfreader_lib/edit_gui.py` / `main.py`.
- **Persist, don't paint over:** text is native `FreeText` annotations; signatures/images are image XObjects in page content; both carry the `OpenReaderData` metadata key. Never use temporary overlays that disappear on save.
- Save atomically (temp file + `os.replace`); preserve encryption with `PDF_ENCRYPT_KEEP`. Flattened export uses `Document.bake` on a copy, never the open original.
- Warn before editing/saving documents with `/FT /Sig` signature fields. Encrypted documents and `/Rotate` pages are read-only for editing. Never silently invalidate a signature.
- Object-model changes require save → reopen round-trip tests; overlay changes require continuous-scroll/zoom coordinate tests.
- Visual signatures are **not** certificate-based digital signatures; keep that distinction explicit.
- Known limits: 90° text rotation only; Base-14 text fonts; arbitrary existing embedded text editing and cryptographic signing out of scope.

## Build, Test & CI Rules

- Keep `Validate`, `Security`, and `build` passing; `main` branch protection depends on those exact check names — do not rename the jobs casually.
- Run the suite before pushing:
  ```bash
  QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q
  python -m py_compile main.py tools/create_icon.py scripts/inject_version.py
  ```
- Current suite: **261 passed, 18 skipped**; packaging tests 7/7; Bandit clean.
- Preserve PDF pre-validation, resource limits, dependency pins, pip-audit, Bandit, and Dependabot.
- Do not expose raw exception internals in user-facing dialogs.
- When pushing with `gh`/`git` in this environment, prefix with `env -u GITHUB_TOKEN` (an invalid env token shadows the working login).

## Versioning, Release & Store Rules

- Canonical version: `main.py __version__`; propagate with `python scripts/inject_version.py <version>` (MCP pyproject/PKG-INFO + MSIX manifests for strict semver).
- Tags are **immutable** (`vMAJOR.MINOR.PATCH`); never retag. If a release fails, ship a patch version.
- **Release workflow is two-phase:** tag push builds artifacts only (Publish job gated); after verification, publish with `gh workflow run release.yml --ref vX.Y.Z -f publish=true`. MSIX generation is mandatory.
- Canonical assets: `OpenReader-Windows.zip`, `OpenReader-macOS-Apple-Silicon.zip`, `OpenReader-macOS-Intel.zip`, `OpenReader.msix`, `OpenReader-Setup.exe`.
- Microsoft Store: upload the production `OpenReader.msix` to Partner Center (Store ID `9MXDVW2645LL`); Store signs it. **Never submit without explicit approval.** Do not modify an installed copy during testing.
- Frozen identity: `SparshSam.OpenReader` · `CN=E6186421-BF8A-47E0-A89C-0F513DFF91C0` · PFN `SparshSam.OpenReader_yh0byntbzd2qw` · Store ID `9MXDVW2645LL`.
- Update `docs/store-acceptance-checklist.md` for the version being submitted; run it after Store acceptance.

## MCP Server (19 tools)

- Bundled: `pdfreader_lib/mcp_server.py` (stdio + SSE). Standalone: `packages/mcp-server/` (`pip install openreader-mcp`, `python -m openreader_mcp`).
- Five form tools added in v1.3.0: `form_list_fields`, `form_get_field`, `form_set_value`, `form_fill`, `form_validate`; they share `form_fields.py`.
- Keep the bundled server and standalone package in sync (including `_form_fields.py`). Keep `requirements-mcp.txt` minimal; the SDK is constrained to **`mcp>=1.0.0,<2`** (MCP 2.x changed the server API).
- The MCP server is optional and must not affect the desktop GUI or packaged builds.

## Documentation & Site

- README describes **shipped** behavior only.
- `docs/Architecture.md` is canonical; keep `CHANGELOG.md` current (Keep a Changelog); keep macOS experimental caveats visible.
- Design specs live in `docs/superpowers/specs/` (forms 2026-08-02; Fill/Edit/Sign 2026-11-08).
- Landing site `site/` → `https://reader.kovina.org` (Cloudflare Pages; auto-deploys on `main` changes under `site/`).
- Keep the Privacy Policy and Terms pages in sync; update their "Last updated" date on material changes.
