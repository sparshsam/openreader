"""Shared AcroForm fixture builders for the form-intelligence tests."""

from __future__ import annotations

import fitz

# Widget flag bits (mirror pdfreader_lib.form_fields).
FLAG_READONLY = 0x1
FLAG_REQUIRED = 0x2
FLAG_MULTILINE = 0x1000
FLAG_PASSWORD = 0x2000
FLAG_COMB = 0x100000


def _make_stream(doc, data: bytes = b"") -> int:
    xref = doc.get_new_xref()
    doc.update_object(
        xref, "<< /Type /XObject /Subtype /Form /BBox [0 0 20 20] /Length 0 >>"
    )
    doc.update_stream(xref, data)
    return xref


def add_radio_group(doc, page, field_name, options, rects, selected=None) -> int:
    """Build a real radio group (/Parent + /Kids) via raw xref objects."""
    kids = []
    for caption, rect in zip(options, rects):
        on = "".join(ch for ch in str(caption) if ch.isalnum()) or "Yes"
        kid = doc.get_new_xref()
        doc.update_object(kid, "<< >>")
        for key, value in {
            "Type": "/Annot",
            "Subtype": "/Widget",
            "FT": "/Btn",
            "Ff": "32768",
            "F": "4",
            "Rect": f"[{rect.x0} {rect.y0} {rect.x1} {rect.y1}]",
            "AS": "/" + (on if caption == selected else "Off"),
            "MK": f"<< /CA ({caption}) >>",
        }.items():
            doc.xref_set_key(kid, key, value)
        off_x, on_x = _make_stream(doc), _make_stream(doc)
        doc.xref_set_key(kid, "AP", f"<</N<</Off {off_x} 0 R/{on} {on_x} 0 R>>>>")
        kids.append(kid)
    parent = doc.get_new_xref()
    doc.update_object(parent, "<< >>")
    doc.xref_set_key(parent, "FT", "/Btn")
    doc.xref_set_key(parent, "Ff", "32768")
    doc.xref_set_key(parent, "T", f"({field_name})")
    doc.xref_set_key(parent, "Kids", "[" + " ".join(f"{k} 0 R" for k in kids) + "]")
    sel_on = "".join(ch for ch in str(selected) if ch.isalnum()) if selected else None
    doc.xref_set_key(parent, "V", "/" + (sel_on or "Off"))
    for kid in kids:
        doc.xref_set_key(kid, "Parent", f"{parent} 0 R")
    annots = doc.xref_get_key(page.xref, "Annots")[1]
    kids_str = " ".join(f"{k} 0 R" for k in kids)
    if annots == "null":
        doc.xref_set_key(page.xref, "Annots", f"[{kids_str}]")
    else:
        inner = annots.strip()[1:-1].strip()
        doc.xref_set_key(page.xref, "Annots", f"[{inner} {kids_str}]")
    return parent


def _add_text(page, name, rect, *, flags=0, max_len=0, label=None):
    widget = fitz.Widget()
    widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    widget.field_name = name
    widget.rect = fitz.Rect(rect)
    widget.field_flags = flags
    if max_len:
        widget.text_maxlen = max_len
    if label:
        widget.field_label = label
    page.add_widget(widget)


def make_form_fixture(path) -> str:
    """Build a PDF exercising every field type and rule. Returns the path."""
    doc = fitz.open()
    page = doc.new_page()

    _add_text(page, "fullname", (100, 100, 300, 125), max_len=40)
    _add_text(page, "comments", (100, 140, 300, 200), flags=FLAG_MULTILINE)
    _add_text(page, "ref", (100, 300, 300, 325), flags=FLAG_READONLY)
    _add_text(page, "phone", (100, 340, 300, 365), flags=FLAG_REQUIRED, label="Phone number")
    _add_text(page, "pin", (100, 380, 300, 405), flags=FLAG_PASSWORD)
    _add_text(page, "code", (100, 420, 300, 445), flags=FLAG_COMB, max_len=6)
    # "dob" with a nearby label to the left -> label-based inference.
    _add_text(page, "dob", (220, 460, 420, 485))
    page.insert_text((40, 478), "Date of Birth:", fontsize=11)

    checkbox = fitz.Widget()
    checkbox.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
    checkbox.field_name = "agree"
    checkbox.rect = fitz.Rect(100, 220, 120, 240)
    page.add_widget(checkbox)

    combo = fitz.Widget()
    combo.field_type = fitz.PDF_WIDGET_TYPE_COMBOBOX
    combo.field_name = "country"
    combo.rect = fitz.Rect(100, 260, 300, 285)
    combo.choice_values = ["US", "CA", "UK"]
    page.add_widget(combo)

    listbox = fitz.Widget()
    listbox.field_type = fitz.PDF_WIDGET_TYPE_LISTBOX
    listbox.field_name = "tags"
    listbox.rect = fitz.Rect(100, 620, 300, 680)
    listbox.choice_values = ["a", "b", "c"]
    page.add_widget(listbox)

    add_radio_group(
        doc,
        page,
        "gender",
        ["M", "F"],
        [fitz.Rect(100, 500, 120, 520), fitz.Rect(100, 530, 120, 550)],
        selected="F",
    )

    doc.save(path, garbage=4, deflate=True)
    doc.close()
    return path
