# Phase 2 — PDF Form Intelligence (v1.3.0 / v1.3.1 / v1.3.2) — Design

> **Status:** Approved (approach + architecture) by Sparsh, 2026-08-02.
> **Build constraint:** local only — no commit, no push. Version bumps applied in code now, tags/PRs at release time.
> **Milestones:** v1.3.0 Interactive PDF Forms → v1.3.1 Field Type Intelligence → v1.3.2 Form Completion Workflow.

## Goal

Let users complete PDFs that already contain structured AcroForm fields: detect fields, render
them as native editable controls, preserve existing values, respect field rules, save values back
into the PDF, warn before closing a modified form, provide keyboard + accessible navigation, add
type intelligence, and make long-form completion manageable. Also expose form filling to the MCP
server so AI agents can drive the same engine.

## Architecture

All form logic lives in a **pure, Qt-free module**; the GUI and MCP server are thin consumers.

```
pdfreader_lib/form_fields.py       NEW — pure logic, no PySide6 imports
  FormField          dataclass: normalized view of a fitz.Widget
  FieldType          normalized enum (text, multiline, checkbox, radio,
                     combo, listbox, signature, button)
  iter_page_fields(page, page_index) -> list[FormField]
  build_field_index(doc) -> list[FormField]
  set_field_value(doc, page_index, field, value)   (radio/checkbox/choices aware)
  get_field_value(widget)
  FormValidator      (v1.3.1) per-type, international-tolerant, advisory
  FormTypeDetector   (v1.3.1) explicit vs inferred, never presented as certainty
  FormStateStore     (v1.3.2) autosave + user overrides, JSON on local disk

main.py                              GUI layer — Approach A native Qt overlays
  FormController       per-tab lifecycle: overlay widgets on page labels,
                       highlight painting, dirty flag, save/save-as wiring
  _TextFormWidget / _CheckFormWidget / _RadioFormWidget / _ComboFormWidget
                       QLineEdit / QTextEdit / QCheckBox / QRadioButton / QComboBox
  FormNavigatorDock    (v1.3.2) sidebar field list + status
  Completion summary, close warning, restore, recent indicators (v1.3.2)

pdfreader_lib/mcp_server.py         +5 tools, same module
  form_list_fields, form_get_field, form_set_value, form_fill, form_validate
```

### Why Qt-free

The MCP server runs standalone (STDIO/SSE) without Qt in scope, so `form_fields.py` must never
import PySide6. The GUI layer stays in `main.py` (a large monolith, consistent with how annotation
and selection code already live there). Overlays anchor to the existing per-page QLabels used by
continuous and single-page rendering.

## v1.3.0 — Interactive PDF Forms

### Detection (shared module)

PyMuPDF exposes AcroForm widgets natively; `FormField` is a defensive normalization of `fitz.Widget`:

| Widget | `field_type` | Normalized | Notes |
|--------|-------------|------------|-------|
| Text | `fitz.PDF_WIDGET_TYPE_TEXT` (7) | `text` / `multiline` | multiline via `PDF_WIDGET_IS_MULTILINE` flag; `max_len` for `/MaxLen` |
| Checkbox | 2 | `checkbox` | `button_state` on/off |
| Radio | 5 | `radio` | grouped by shared `field_name`; `on_state()` enumerates choices |
| Combo | 3 | `combo` | editable or not per flags; `choice_values` from `/Opt` |
| Listbox | 4 | `listbox` | multi-select supported by flags |
| Signature | 8 | `signature` | render-only marker, never editable |
| Pushbutton | 6 | `button` | render-only marker |

Flags honored: `PDF_WIDGET_IS_READONLY` (1), `PDF_WIDGET_IS_REQUIRED` (2), `PDF_WIDGET_IS_MULTILINE`,
`PDF_WIDGET_IS_PASSWORD`, `PDF_WIDGET_IS_COMB`, `PDF_WIDGET_IS_NO_TOGGLE_TO_OFF` (radio).

Defensive normalization: nameless fields get `field_<page>_<n>`; malformed choices degrade to text;
iteration never raises on a bad widget.

### Rendering & editing (GUI, Approach A)

- On every render (`_do_render`), after the pixmap is set on a page QLabel, the `FormController`:
  1. paints a subtle field-rect highlight onto the pixmap (`rect × zoom`) so fillable areas are
     visible even when the PDF ships no appearance stream;
  2. creates/repositions native overlay widgets at `(rect − page_rect) × zoom`.
- Text → `QLineEdit` (or `QTextEdit` for multiline), `setMaxLength` from `/MaxLen`,
  `setReadOnly` from flags, `echoMode=Password` for password fields.
- Checkbox → `QCheckBox`; radio → a `QRadioButton` group sharing the widget's state; combo/listbox
  → `QComboBox` (editable per flags) populated from `/Opt`.
- Signature/pushbutton → painted marker, no editor (respect read-only).
- Existing values are seeded into overlays on open (**preserve existing field values**).
- Each overlay carries `setAccessibleName(field.name)` so screen readers see labeled fields.
- Focus highlight: focused field gets a stronger accent border.

### Keyboard & accessibility

- `Tab` / `Shift+Tab` move between editable fields (native Qt focus chain over overlay widgets).
- Arrow keys move within a radio group (native).
- Overlays are real Qt widgets → focus-visible, accessible via the Qt a11y bridge.

### Persistence

- Dirty flag per tab set on any field change.
- Save (`Ctrl+S`, File > Save): for each dirty field `set_field_value(...)` then
  `widget.update()` (regenerates the appearance stream so values render in any viewer), then
  `doc.save(incremental=True)` with a full-save fallback — reusing `_save_document_annotations`
  semantics.
- Save As: full save to a new path (`doc.save(new_path, garbage=1, deflate=True)`), updates tab
  path + recent list.
- **Close warning** (v1.3.0): if a tab is dirty (form or annotation edits), prompt
  Save / Discard / Cancel before closing the tab or the window.

## v1.3.1 — Field Type Intelligence

### Detection pipeline (`FormTypeDetector`)

Given a `FormField` (formatting rule + name + nearby label text + page text near rect):

- **Explicit type** — from PDF metadata/formatting rule (e.g. `text_format == 2` → date). Authoritative.
- **Inferred type** — heuristic from field name/labels (e.g. "dob", "date of birth" → date;
  "phone", "telephone" → phone; "zip"/"postal" → zip; "email" → email; "$"/"amount"/"price" →
  currency; "qty"/"number"/"count" → numeric). Always tentative.
- `FormField` carries `field_type` (editing type), `explicit_type`, `inferred_type`,
  `type_confidence`, and `is_inferred: bool` so the UI can mark inference subtly.

**Never present inference as certainty**: inferred-type fields remain fully editable as plain text;
the inference only offers affordances (e.g. a date picker) and an advisory validation hint.
A clear message in the navigator/tooltip ("Inferred type: date — you can still type any text").

### Editing affordances

- Date → `QDateEdit`-style picker shown on focus, but free text still accepted.
- Phone / ZIP / email / currency / numeric → validation on focus-out (non-blocking).

### Override

- Context menu on a field: "Set field type → {Date, Phone, ZIP, Email, Currency, Number, Text}".
- Overrides persist **outside the PDF** (in `FormStateStore`), keyed by `(path, page, field_name)`
  so the PDF is never mutated by preference alone.

### Validation (`FormValidator`)

- Per-type rules, tolerant of legitimate international formats:
  phone accepts `+`, digits, spaces, dashes, parens; ZIP allows international alphanumeric
  (4–6+ chars); email pragmatic; currency optional symbol + comma + decimals; numeric optional
  sign + decimal.
- Advisory only — never blocks input; writes `validation_message` shown inline in the navigator
  and as a tooltip on focus-out ("Expected a phone number like +1 555 123 4567").

## v1.3.2 — Form Completion Workflow

- **FormNavigatorDock**: dockable sidebar listing all fields with status — ✓ filled, ○ empty,
  ● required, ⚠ invalid — grouped by page; click scrolls to + focuses the field.
- **Next Field / Previous Field** controls (toolbar + `Ctrl+Down` / `Ctrl+Up`), document order.
- **Completion summary** before export: counts of filled / empty / required-empty / invalid with
  jump-to links; launched from "Review & Complete" before Save As.
- **Highlight missing required fields**: required-empty fields get a warning tint + navigator dot.
- **Clear**: per-field ("Clear Field") and whole-form ("Clear Form", skipping read-only).
- **Autosave & crash recovery**: dirty field values are debounced (≈1 s) into `FormStateStore`
  (JSON in the app data dir, keyed by path hash). On reopen, offer "Restore unsaved form data?"
  (with "Don't ask again").
- **Restore on session reopen**: session entries (already written in `closeEvent`) gain form
  values + overrides.
- **Form-specific recent indicators**: recent-files menu marks documents that have AcroForm fields.

## MCP tools (same module)

All operate on an absolute local path with the existing safety validation, opening in memory and
saving incrementally to the original or to a supplied `output` path:

- `form_list_fields(path)` → JSON array: name, page, type, flags (readonly/required), value,
  choices, rect, inferred type + confidence.
- `form_get_field(path, field)` → single field detail incl. format rule.
- `form_set_value(path, field, value, output?)` → set one value, save.
- `form_fill(path, values: {field: value}, output?)` → set many, per-field success/failure.
- `form_validate(path, field, value)` → run `FormValidator`, return ok + message.

MCP uses on-demand inference; GUI overrides live only in `FormStateStore`.

## Error handling

- Encrypted docs: existing open flow applies; saving falls back to full save; surface existing
  save-failure path and offer Save As.
- Signed forms: signature fields are read-only markers; digital signing is out of scope.
- Malformed forms: normalized defensively, never crash on iteration.
- Read-only file on disk: reuse existing save error surface, offer Save As.
- Huge forms: navigator renders lazily; overlay count bounded by page.

## Testing

- Fixture PDFs built with PyMuPDF in `tests/` covering: text, multiline, checkbox, radio group,
  combo, listbox, readonly, required, `max_len`, `text_format` date, password, signed marker.
- Module unit tests: normalization, flag mapping, radio grouping, value set/get round-trip,
  incremental save → reopen → values present and visible.
- `FormValidator`: international formats accepted; wrong formats advisory; explicit vs inferred.
- `FormTypeDetector`: name/label heuristics, confidence, no false certainty.
- MCP: `form_list_fields` / `form_fill` / `form_set_value` round-trip; non-PDF path rejected.
- GUI smoke (offscreen): overlay creation for a fixture page — widget types + positions.

## Version alignment

`main.py __version__ = "1.3.0"`, `packages/mcp-server/pyproject.toml = "1.3.0"`,
`packaging/msix/AppxManifest.xml` + `AppInstaller.xml` = `1.3.0.0`.
