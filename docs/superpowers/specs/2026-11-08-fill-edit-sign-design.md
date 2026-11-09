# Fill, Edit & Sign (v1.3.0) — Design

> **Status:** Implemented for v1.3.0 on top of the released v1.2.8 reader.
> **Scope:** Interactive form filling, freeform text, visual electronic signatures,
> image placement, persistence, and editing UI. Certificate-based signing and
> editing arbitrary embedded PDF text are explicitly out of scope.

## Goals

Make OpenReader a practical local alternative to Acrobat for everyday completion:

**Open a PDF → Fill its fields → Add text or images → Sign → Save or export.**

Everything runs locally. No accounts, no subscriptions, no uploads.

## Architecture

```
pdfreader_lib/form_fields.py      Qt-free AcroForm engine (Forms)
pdfreader_lib/edit_objects.py     Qt-free editable-object model + persistence
pdfreader_lib/edit_gui.py         Qt controller, overlays, inline editor,
                                  signature dialog/canvas, undo/redo
pdfreader_lib/signature_store.py  Local-only PNG signature library
main.py                           Toolbar actions, contextual bar, save/dirty UI,
                                  page-label overlay attachment
```

The model never imports PySide6, so it is usable from tests and the MCP server.
The GUI controller owns all Qt widgets and coordinate conversion.

## Persistence

| Object | PDF representation | Re-edit metadata |
|---|---|---|
| Text | Native `FreeText` annotation (rich text, base-14 fonts, selectable) | `OpenReaderData` JSON string key on the annotation xref: oid, rect, text, style, rotation |
| Signature | Image XObject inserted into page content | `OpenReaderData` JSON on the image xref: oid, kind, rect, rotation, name |
| Image | Image XObject inserted into page content | Same as signatures |

Notes:

- Image payloads are made unique per placement with a private PNG `tEXt` chunk so
  PyMuPDF cannot merge two objects onto one XObject and lose metadata.
- `list_objects()` only returns objects carrying `OpenReaderData`; foreign
  annotations and images are never modified.
- Text style is a Qt-free `TextStyle` (family, size, color, bold, italic,
  underline, alignment) mapped to FreeText CSS + `/Q`.
- Moving/resizing/reformatting removes and re-inserts the object while preserving
  its `oid`, so the same object remains selected and editable.

## Save / export

- **Save / Save As:** temp file in the target directory + `os.replace`; encryption
  preserved with `PDF_ENCRYPT_KEEP`. Dirty state clears after success.
- **Export Flattened PDF:** save a copy to a temp file, open it, call
  `Document.bake(annots=True, widgets=True)`, save the target. The open document
  and source file are untouched.
- **Form values:** written with `set_field_value` (which calls `widget.update()`
  to regenerate appearances) before the atomic document save.

## Undo / redo

Snapshot-based per tab: each edit pushes a deep copy of the editable-object list.
Undo/redo applies a snapshot by removing all OpenReader objects and re-adding the
snapshot. Image bytes are immutable and shared between snapshots. Form fields use
native widget undo; global undo covers text/signature/image objects.

## Coordinates

- Stored in PDF points.
- GUI conversion: `label_px = (pdf_point − page.rect.origin) × zoom + 1`
  (1 px = page-label border/content offset).
- Works in continuous and single-page modes; overlays live on the persistent
  page QLabels, so scrolling and the virtualized renderer do not break editing.
- Pages with a non-zero `/Rotate` refuse editing with a clear status message.

## UI

- Main toolbar adds **Fill | Add Text | Sign | Image** as compact vector buttons.
- Fill shows the Form Navigator and focuses the first field; fields are always
  directly editable (no separate form mode).
- A contextual `ContextToolbar` row appears for the selection: font family, size,
  color, B/I/U, alignment, rotate, duplicate, delete and Done (inline editor).
  Image/signature selections show rotate/duplicate/delete only.
- Inline text editor commits on Ctrl+Enter or Done; Escape cancels; selecting
  another object commits.
- Dirty indicators: `●` in the tab and window title; close prompts Save / Discard /
  Cancel.

## Safety

- Signature fields (`/FT /Sig`) trigger an explicit warning before editing and
  before saving a dirty document; Save As Copy is offered.
- Encrypted documents are treated as read-only for editing. Encryption is captured
  at open time because PyMuPDF 1.28 corrupts its decryption state if
  `needs_pass`/`permissions` are read after `authenticate()`.
- Pages with `/Rotate` are read-only.
- Existing annotations, links, bookmarks and metadata are preserved by full saves.
- No cryptographic signing is performed; signatures are visual electronic
  signatures and are labelled as such.

## Limitations (v1.3.0)

- Text rotation: 0/90/180/270 only (FreeText `/Rotate`).
- Text fonts: Base-14 Helvetica / Times New Roman / Courier New.
- User-added text is selectable; signatures/images are raster images.
- Arbitrary pre-existing embedded text editing is out of scope.
- Certificate-based digital signatures and signing workflows are out of scope.
- Rotated pages and encrypted documents are read-only for editing.

## Testing

- `tests/test_form_fields.py` — AcroForm engine, type detection, validation, state.
- `tests/test_edit_objects.py` — text/image metadata, reopen, undo state, atomic
  save, flattened export, signature detection, encrypted save.
- `tests/test_signature_store.py` — local signature library lifecycle.
- `tests/test_edit_gui.py` — offscreen end-to-end text/image/signature editing,
  inline commit, formatting, undo/redo, Save As, flatten, coordinate mapping,
  continuous mode, rotated-page rejection, themes.
- Existing reader, scrolling, toolbar, security and packaging suites remain green.
