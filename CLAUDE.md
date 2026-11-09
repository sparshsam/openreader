# OpenReader — Agent Instructions & Session Handoff

## What OpenReader Is

Privacy-first, **local-only** desktop PDF utility for Windows (macOS experimental; Linux unsupported). Read, annotate, search, compare, merge/split/compress — and, from v1.3.0, **fill forms, add text, sign visually, and insert images** — without accounts, subscriptions, cloud processing, uploads, or internet access. The only network call is the optional GitHub update check (detection only; no downloads).

**Stack:** Python 3.11–3.14 · PySide6 6.11.1 (Qt 6) · PyMuPDF 1.28.2 · Pillow · PyInstaller (Windows/macOS packaging) · Inno Setup (legacy installer) · MSIX (Windows/Store).

## Current Repository State (2026-11-08)

| Item | Value |
|---|---|
| **Latest published release** | **v1.2.8** — merge commit `57c29ea`, annotated tag `v1.2.8`, release `https://github.com/sparshsam/openreader/releases/tag/v1.2.8` |
| **Current development version** | **v1.3.0 — Fill, Edit & Sign** — implemented, **NOT approved for release** |
| **Active branch** | `feat/v1.3.0-fill-edit-sign` |
| **Open PR** | **#107** — https://github.com/sparshsam/openreader/pull/107 — implementation head **`7106ae5`**; the documentation-handoff commit follows on this branch and is the current PR head |
| **Backup branch** | `wip/v1.3.0-form-intelligence` at **`60038ca`** — unchanged; do not modify |
| **Tests** | **261 passed, 18 skipped** (local Python 3.14 and CI Python 3.11) |
| **CI** | All checks green on the implementation head: Validate, Security, python-security, Windows build (MSIX), macOS Apple Silicon + Intel, CodeQL/Analyze, Cloudflare Pages |
| **Branch protection** | PR required; **0 required approvals**; required checks `Validate`, `Security`, `build`; admins enforced; force pushes/deletions blocked |
| **Installed app** | Untouched; no Microsoft Store submission |

### Immediate Next Task — next session only

**v1.3.0 is implemented but NOT approved for release.** The next session must begin with **isolated Windows runtime testing** (do not start it in the documentation session):

1. Prepare an isolated v1.3.0 Windows development environment (separate source copy + private venv/profile; do not reuse the installed app's data).
2. Preserve the existing installed OpenReader application and all previous development environments.
3. Launch the actual desktop GUI for Sparsh's manual testing.
4. Prepare realistic PDF fixtures: interactive AcroForm forms (all field types), non-interactive printed forms, long documents, multi-page documents, signed/encrypted samples, images and signatures.
5. Test interactive and non-interactive form filling, freeform text and formatting, signature draw/type/import/place, image insertion, Save, Save As, reopen, and flattened export.
6. Verify editing in **continuous-scroll mode** (scroll, zoom, window resize, tab switches).
7. Perform cross-viewer compatibility checks where possible (Acrobat, Edge, Chrome) and confirm text selectability, links/bookmarks/metadata preservation.
8. Fix any defects found, re-run tests/CI, and only then request release approval.

Do **not** merge, tag, publish, or submit to the Store until Sparsh explicitly approves the runtime test results.

## Repository Structure

```
main.py                      PySide6 application (window, toolbar, page rendering,
                             form overlays, edit overlays, save/dirty/close flows)
pdfreader_lib/
  form_fields.py             Qt-free AcroForm engine (fields, type detection,
                             advisory validation, local form-state store)
  edit_objects.py            Qt-free text/signature/image model + persistence,
                             atomic save, flattened export, signature detection
  edit_gui.py                Per-tab EditController, overlays, inline text editor,
                             signature draw/type/import dialog, undo/redo
  signature_store.py         Local-only PNG signature library
  mcp_server.py              Bundled MCP server (19 tools, stdio + SSE)
  search_index.py            SQLite FTS5 + TF-IDF search
  comparison.py              Page-by-page PDF comparison
  install_source.py          source / MSIX / Setup / portable detection
  win_default_apps.py        Windows default-PDF-reader detection
packages/mcp-server/         Standalone openreader-mcp pip package
  src/openreader_mcp/server.py + _form_fields.py
assets/                      branding, icons, screenshots
docs/                        Architecture, RELEASE, VERSIONING, BRANDING,
                             playbooks, superpowers design specs
packaging/msix/              AppxManifest.xml, AppInstaller.xml
installer/                   Inno Setup script
scripts/                     inject_version.py, build scripts, icon generation
site/                        reader.kovina.org (Cloudflare Pages)
tests/                       pytest suites (forms, editing, scrolling, toolbar,
                             MCP, packaging, security, updater)
.github/workflows/           ci, security, build-windows, build-macos, release,
                             deploy-site
```

## v1.3.0 Functionality

### Fill
- Native AcroForm overlays: text/multiline, checkbox, radio groups, combo, listbox; existing values preserved; read-only/required/max-length/password/comb rules.
- Tab/Shift+Tab navigation; accessible names; field highlights.
- Field type detection (explicit vs. inferred), advisory validation, date picker, persisted overrides.
- Form Navigator (status, next/previous, clear, completion review), autosave/recovery, recent-file form markers.
- Non-interactive forms completed with **Add Text**.

### Add Text
- Click-to-place multiline text objects; inline editor (Ctrl+Enter/Done); auto-grow boxes.
- Drag, resize, rotate in 90° steps, duplicate, copy/paste, delete; snapshot undo/redo.
- Contextual bar: Helvetica/Times New Roman/Courier New, size, color, bold/italic/underline, left/center/right.
- Native `FreeText` annotations with `OpenReaderData` metadata — reopens editable and remains selectable in other viewers.

### Sign
- Draw (mouse/touch/pen/trackpad), Type (installed signature-style fonts with preview), Import (PNG/JPEG/BMP/WebP/GIF, transparency), and Saved signatures.
- Place anywhere, drag, proportional resize, rotate, duplicate, remove, multi-page.
- Local-only signature library with delete/clear; **visual electronic signature**, not certificate-based.

### Images
- Insert common formats; position, proportional resize, rotate, duplicate, delete.

### Persistence & Safety
- Atomic Save / Save As; **Export Flattened PDF** via `Document.bake` on a copy (original untouched).
- Dirty indicators in tab/window title; Save / Discard / Cancel on close.
- Existing annotations, links, bookmarks, metadata preserved.
- Digital-signature fields warn before editing/saving; encrypted docs and `/Rotate` pages are read-only for editing.
- Editing works directly in virtualized continuous scroll at any zoom.

### MCP
- Five form tools (`form_list_fields`, `form_get_field`, `form_set_value`, `form_fill`, `form_validate`) → **19 tools total**, mirrored in the standalone package.
- Optional SDK constrained to **`mcp>=1.0.0,<2`** (v1.3.0 server uses the 1.x API).

## Architecture Rules

1. **Local-first / privacy by design.** No cloud, accounts, telemetry, or uploads. PDFs and signatures stay local.
2. **Qt-free model.** `form_fields.py` and `edit_objects.py` must not import PySide6; GUI logic stays in `edit_gui.py`/`main.py`.
3. **Persisted, not painted on top.** Text = native `FreeText` annotations; signatures/images = image XObjects in page content; both carry `OpenReaderData` JSON metadata for re-editing. Never use temporary overlays that vanish on save.
4. **Coordinates in PDF points.** The GUI converts to/from page-label pixels with the active layout zoom; editing must survive scrolling, zoom, resize, and tab switches.
5. **Safe writes.** Temp file + `os.replace`; preserve encryption with `PDF_ENCRYPT_KEEP`; flatten a copy, never the open original.
6. **Do not silently invalidate signatures.** Warn on `/FT /Sig` documents; encrypted documents and rotated pages are read-only for editing.
7. **Preserve the v1.2.8 reader.** Continuous scrolling, unified toolbar, themes, annotations, search, tabs and existing shortcuts must keep working.

## Testing

```bash
# Full suite (offscreen Qt)
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q

# Syntax check
python -m py_compile main.py tools/create_icon.py scripts/inject_version.py
```

- Current: **261 passed, 18 skipped** (pre-existing skips).
- New v1.3.0 suites: `test_edit_objects.py` (16), `test_edit_gui.py` (16), `test_signature_store.py` (5), plus the ported form/MCP suites (`test_form_fields.py`, `test_form_gui.py`, `test_mcp_server.py`).
- Packaging: `tests/test_packaging.py` — 7/7 (version alignment, frozen identity, `.pdf` association, MinVersion).
- CI required checks: **`Validate`** (compile + pytest), **`Security`** (pip-audit + Bandit), **`build`** (Windows PyInstaller + MSIX). Also run: macOS builds, python-security, CodeQL/Analyze, Cloudflare Pages.

## Known Limitations & Outstanding Verification

**Limitations (v1.3.0):**
- Text rotation: 90° increments only (FreeText `/Rotate`).
- Text fonts: Base-14 Helvetica / Times New Roman / Courier New.
- User-added text is native/selectable; signatures and images are raster content.
- Editing arbitrary pre-existing embedded PDF text is out of scope.
- Certificate-based digital signing is out of scope (visual signatures only).
- Encrypted documents and `/Rotate` pages are read-only for editing.
- Form-field value changes use native widget undo; the global undo stack covers editable objects.

**Still to verify before release approval:**
1. **Isolated Windows runtime manual test** (the next session's first task).
2. Cross-viewer round-trip (Acrobat/Edge/Chrome): text selectability, images/signatures, flattened output, links/bookmarks/metadata.
3. Signature draw/import dialogs and real pen/touch input on Windows.
4. Signed-document warning UX and encrypted/read-only behavior on real files.
5. MSIX install/update compatibility with the existing installed copy (without modifying it).
6. CI currently builds the **test** MSIX: package version `1.3.0.0`, app version `1.3.0-test`. The production package must be built from the `v1.3.0` tag (app version `1.3.0`).

## Branching, CI, Versioning, Release & Store

### Branching / CI
- Branch from `main`; naming `<type>/<description>`; PR for every merge (no direct pushes).
- Branch protection: PR required, 0 required approvals, required checks `Validate`, `Security`, `build`; admins enforced; no force pushes/deletions. Do not rename those job contexts casually.
- Workflows: `ci.yml` (Validate/Security), `security.yml` (python-security/CodeQL), `build-windows.yml` (PR/main; builds PyInstaller ZIP + Inno Setup + unsigned MSIX), `build-macos.yml`, `release.yml` (tag build-only; publish via manual dispatch), `deploy-site.yml`.
- When using `gh`/`git` push in this environment, prefix with `env -u GITHUB_TOKEN` (an invalid `GITHUB_TOKEN` shadows the working login).

### Versioning
- Canonical source: `main.py` `__version__`; propagate with `python scripts/inject_version.py <version>` (also updates MCP pyproject/PKG-INFO and MSIX manifests when strict semver).
- `source` builds may be `-dev`/`-test`; MSIX manifests require `x.y.z.0`.
- Tags are **immutable**; never retag. If a release fails, ship a patch version.

### Release
1. Merge the approved PR; tag the merge commit with an **annotated** `vX.Y.Z`; push the tag.
2. The tag run builds `OpenReader.msix`, `OpenReader-Setup.exe`, `OpenReader-Windows.zip`, and the macOS ZIPs **without publishing** (Publish job gated).
3. Verify the MSIX identity/version and version metadata.
4. Publish explicitly: `gh workflow run release.yml --ref vX.Y.Z -f publish=true`.
- Canonical asset names: `OpenReader-Windows.zip`, `OpenReader-macOS-Apple-Silicon.zip`, `OpenReader-macOS-Intel.zip`, `OpenReader.msix`, `OpenReader-Setup.exe`.
- MSIX generation is mandatory; the release fails without it.

### Microsoft Store
- Upload the production `OpenReader.msix` to Partner Center (Store ID `9MXDVW2645LL`); Microsoft signs it.
- **Never submit without Sparsh's explicit approval.** Do not modify an installed copy during testing.
- Post-release acceptance: `docs/store-acceptance-checklist.md` (update to the current version when submitting).

### Frozen identity — never change
`SparshSam.OpenReader` · Publisher `CN=E6186421-BF8A-47E0-A89C-0F513DFF91C0` · PFN `SparshSam.OpenReader_yh0byntbzd2qw` · Store ID `9MXDVW2645LL`.

## Kovina Standards

- **Privacy-first, local-first, open-source.** No accounts, subscriptions, cloud processing, telemetry, or uploads; signatures remain local.
- **Open Product Family branding:** KOVINA → OPEN → Reader. OPEN is typography only (no icon); the app icon belongs to OpenReader. Brand accent `#ff255F`. See `docs/BRANDING.md`; never redesign the header lockup without instruction.
- **Design decisions start from `docs/playbooks/`** (Product Architecture, Design, MCP Server Build Guide).
- **Docs discipline:** README describes shipped behavior only; `docs/Architecture.md` is canonical; keep `CHANGELOG.md` current (Keep a Changelog); keep macOS experimental caveats visible; update `docs/RELEASE.md` if release mechanics change.
- **Security:** preserve PDF pre-validation/resource limits; keep dependency pins deliberate; never expose raw exception internals in user dialogs; report accidental secret exposure immediately.

## Useful Commands

```powershell
# Windows source run
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py

# Packaged build
.\scripts\build_windows.ps1
```

```bash
# Tests / compile
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q
python -m py_compile main.py tools/create_icon.py scripts/inject_version.py
```
