"""Tests for the Qt-free editable-object model (v1.3.0)."""

from __future__ import annotations

import hashlib
import io
import json

import fitz
import pytest
from PIL import Image

from pdfreader_lib import edit_objects as eo


def _png(color=(200, 30, 60, 255), size=(60, 30)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", size, color).save(buffer, "PNG")
    return buffer.getvalue()


def _blank_doc():
    doc = fitz.open()
    doc.new_page(width=612, height=792)
    return doc


def _text_object(**overrides) -> eo.EditObject:
    values = dict(
        oid="text-1",
        kind=eo.TEXT_KIND,
        page_index=0,
        rect=(72, 72, 300, 120),
        text="Hello OpenReader\nsecond line",
        style=eo.TextStyle(
            font_family="Times New Roman",
            font_size=18,
            color="#cc0000",
            bold=True,
            italic=True,
            underline=True,
            align="center",
        ),
        rotation=0,
    )
    values.update(overrides)
    return eo.EditObject(**values)


def _image_object(**overrides) -> eo.EditObject:
    values = dict(
        oid="image-1",
        kind=eo.SIGNATURE_KIND,
        page_index=0,
        rect=(72, 200, 252, 280),
        image_png=_png(),
        name="Sparsh",
    )
    values.update(overrides)
    return eo.EditObject(**values)


def test_text_style_normalization():
    style = eo.TextStyle(
        font_family="Arial",
        font_size=1000,
        color="not-a-color",
        align="diagonal",
    ).normalized()
    assert style.font_family == "Helvetica"
    assert style.font_size == 200
    assert style.color == "#000000"
    assert style.align == "left"


def test_add_text_persists_metadata_and_style(tmp_path):
    doc = _blank_doc()
    eo.add_object(doc, _text_object())
    found = eo.list_objects(doc)
    assert len(found) == 1
    obj = found[0]
    assert obj.kind == eo.TEXT_KIND
    assert obj.text.startswith("Hello OpenReader")
    assert obj.style.font_family == "Times-Roman"
    assert obj.style.bold and obj.style.italic and obj.style.underline
    assert obj.style.align == "center"

    path = tmp_path / "text.pdf"
    eo.save_document(doc, path)
    doc.close()

    reopened = fitz.open(path)
    try:
        objects = eo.list_objects(reopened)
        assert len(objects) == 1
        assert objects[0].oid == "text-1"
        assert objects[0].rect == pytest.approx((72, 72, 300, 120))
        assert "second line" in objects[0].text
        assert objects[0].style.color == "#cc0000"
    finally:
        reopened.close()


def test_update_text_replace_and_delete(tmp_path):
    doc = _blank_doc()
    obj = eo.add_object(doc, _text_object())
    updated = obj.copy()
    updated.text = "Replaced"
    updated.rect = (100, 100, 340, 150)
    updated.style = eo.TextStyle(font_family="Courier New", font_size=12)
    eo.remove_object(doc, obj)
    eo.add_object(doc, updated)
    found = eo.list_objects(doc)
    assert len(found) == 1
    assert found[0].text == "Replaced"
    assert found[0].rect == pytest.approx((100, 100, 340, 150))
    assert found[0].style.font_family == "Courier"

    eo.remove_object(doc, found[0])
    assert eo.list_objects(doc) == []
    doc.close()


def test_text_rotation_roundtrip(tmp_path):
    doc = _blank_doc()
    eo.add_object(doc, _text_object(rotation=90))
    path = tmp_path / "rotated.pdf"
    eo.save_document(doc, path)
    doc.close()
    reopened = fitz.open(path)
    try:
        annots = list(reopened[0].annots())
        assert len(annots) == 1
        assert annots[0].rotation == 90
        assert eo.list_objects(reopened)[0].rotation == 90
    finally:
        reopened.close()


def test_add_image_persists_and_removes_visually(tmp_path):
    doc = _blank_doc()
    obj = eo.add_object(doc, _image_object())
    page = doc[0]
    found = eo.list_objects(doc)
    assert len(found) == 1
    assert found[0].kind == eo.SIGNATURE_KIND
    assert found[0].image_png  # extracted from the XObject
    assert found[0].name == "Sparsh"

    pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
    assert pix.pixel(100, 240) != (255, 255, 255)

    path = tmp_path / "image.pdf"
    eo.save_document(doc, path)
    doc.close()

    reopened = fitz.open(path)
    try:
        objects = eo.list_objects(reopened)
        assert len(objects) == 1
        assert objects[0].kind == eo.SIGNATURE_KIND
        assert objects[0].rect == pytest.approx((72, 200, 252, 280))
        eo.remove_object(reopened, objects[0])
        pix = reopened[0].get_pixmap(matrix=fitz.Matrix(1, 1))
        assert pix.pixel(100, 240) == (255, 255, 255)
        assert eo.list_objects(reopened) == []
    finally:
        reopened.close()


def test_duplicate_image_gets_independent_metadata(tmp_path):
    doc = _blank_doc()
    first = eo.add_object(doc, _image_object())
    duplicate = first.copy()
    duplicate.oid = "image-2"
    duplicate.rect = (300, 200, 480, 280)
    eo.add_object(doc, duplicate)
    objects = eo.list_objects(doc)
    assert len(objects) == 2
    assert {o.oid for o in objects} == {"image-1", "image-2"}
    assert objects[0].xref != objects[1].xref
    assert objects[0].rect != objects[1].rect
    page = doc[0]
    before = page.get_pixmap(matrix=fitz.Matrix(1, 1))
    assert before.pixel(100, 240) != (255, 255, 255)
    assert before.pixel(350, 240) != (255, 255, 255)

    # Deleting one placement must leave the other intact.
    eo.remove_object(doc, objects[0])
    remaining = eo.list_objects(doc)
    assert len(remaining) == 1 and remaining[0].oid == "image-2"
    after = page.get_pixmap(matrix=fitz.Matrix(1, 1))
    assert after.pixel(100, 240) == (255, 255, 255)
    assert after.pixel(350, 240) != (255, 255, 255)
    doc.close()


def test_apply_objects_restores_a_snapshot():
    doc = _blank_doc()
    eo.add_object(doc, _text_object())
    eo.add_object(doc, _image_object())
    saved = eo.snapshot(doc)
    assert len(saved) == 2

    eo.clear_objects(doc)
    assert eo.list_objects(doc) == []

    restored = eo.apply_objects(doc, saved)
    assert len(restored) == 2
    current = eo.list_objects(doc)
    assert {o.oid for o in current} == {"text-1", "image-1"}
    assert any(o.kind == eo.TEXT_KIND for o in current)
    assert any(o.kind == eo.SIGNATURE_KIND for o in current)
    doc.close()


def test_save_document_is_atomic_and_preserves_content(tmp_path):
    doc = _blank_doc()
    doc[0].insert_text((72, 40), "Existing page content", fontsize=12)
    eo.add_object(doc, _text_object())
    path = tmp_path / "atomic.pdf"
    eo.save_document(doc, path)
    doc.close()

    reopened = fitz.open(path)
    try:
        assert "Existing page content" in reopened[0].get_text()
        assert len(eo.list_objects(reopened)) == 1
    finally:
        reopened.close()
    # No temporary files are left behind.
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []


def test_export_flattened_leaves_original_untouched(tmp_path):
    doc = _blank_doc()
    eo.add_object(doc, _text_object())
    eo.add_object(doc, _image_object())
    source = tmp_path / "source.pdf"
    eo.save_document(doc, source)
    hash_before = hashlib.sha256(source.read_bytes()).hexdigest()

    flat = tmp_path / "flattened.pdf"
    eo.export_flattened(doc, flat)

    assert hashlib.sha256(source.read_bytes()).hexdigest() == hash_before
    assert len(eo.list_objects(doc)) == 2

    flattened = fitz.open(flat)
    try:
        page = flattened[0]
        assert list(page.annots()) == []
        assert list(page.widgets() or []) == []
        assert "Hello OpenReader" in page.get_text()
        assert len(page.get_images(full=True)) >= 1
    finally:
        flattened.close()
    doc.close()


def test_document_safety_helpers():
    doc = _blank_doc()
    assert eo.document_allows_editing(doc) is True
    assert eo.document_has_signatures(doc) is False
    assert eo.page_allows_editing(doc[0]) is True
    doc.close()
    assert eo.document_allows_editing(doc) is False


def test_document_has_signatures_detects_signature_fields():
    doc = fitz.open()
    page = doc.new_page()
    widget = fitz.Widget()
    widget.field_type = fitz.PDF_WIDGET_TYPE_SIGNATURE
    widget.field_name = "signature1"
    widget.rect = fitz.Rect(50, 50, 200, 100)
    page.add_widget(widget)
    try:
        assert eo.document_has_signatures(doc) is True
    finally:
        doc.close()


def test_encrypted_read_only_document_is_not_editable(tmp_path):
    source = tmp_path / "encrypted.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Locked content", fontsize=14)
    doc.save(
        source,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner-secret",
        user_pw="user-secret",
        permissions=fitz.PDF_PERM_PRINT,
    )
    doc.close()

    reopened = fitz.open(source)
    try:
        assert reopened.needs_pass
        assert reopened.authenticate("user-secret")
        # The encryption flag is captured at open time; do not inspect the
        # authenticated document's encryption properties (PyMuPDF 1.28 bug).
        assert eo.document_allows_editing(reopened, encrypted=True) is False
        assert "Locked content" in reopened[0].get_text()
    finally:
        reopened.close()


def test_atomic_save_preserves_encryption(tmp_path):
    source = tmp_path / "encrypted.pdf"
    target = tmp_path / "encrypted-copy.pdf"
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Encrypted content", fontsize=14)
    doc.save(
        source,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner-secret",
        user_pw="user-secret",
        permissions=fitz.PDF_PERM_PRINT,
    )
    doc.close()

    reopened = fitz.open(source)
    try:
        assert reopened.authenticate("user-secret")
        reopened[0].insert_text((72, 100), "Second line", fontsize=12)
        eo.save_document(reopened, target)
    finally:
        reopened.close()

    copied = fitz.open(target)
    try:
        assert copied.needs_pass
        assert copied.authenticate("user-secret")
        text = copied[0].get_text()
        assert "Encrypted content" in text and "Second line" in text
    finally:
        copied.close()


def test_rotated_png_and_aspect_size():
    png = _png(size=(100, 50))
    rotated = eo.rotated_png(png, 90)
    with Image.open(io.BytesIO(rotated)) as image:
        assert image.size == (50, 100)
    assert eo.aspect_size(200, png) == pytest.approx(100)


def test_metadata_rejects_foreign_annotations(tmp_path):
    doc = _blank_doc()
    page = doc[0]
    page.add_freetext_annot(fitz.Rect(10, 10, 100, 50), "foreign")
    assert eo.list_objects(doc) == []
    path = tmp_path / "foreign.pdf"
    eo.save_document(doc, path)
    doc.close()


def test_invalid_object_kind_is_rejected():
    doc = _blank_doc()
    with pytest.raises(ValueError):
        eo.add_object(
            doc,
            eo.EditObject(oid="x", kind="video", page_index=0, rect=(0, 0, 10, 10)),
        )
    doc.close()
