"""Offscreen GUI tests for v1.3.0 Fill / Edit / Sign."""

from __future__ import annotations

import io

import fitz
import pytest
from PIL import Image
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from pdfreader_lib import edit_gui, edit_objects as eo


@pytest.fixture(autouse=True)
def _no_blocking_dialogs(monkeypatch):
    # Closing a dirty test document must not wait for a human.
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QMessageBox.Discard),
    )


def _png(color=(180, 30, 80, 255), size=(80, 40)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", size, color).save(buffer, "PNG")
    return buffer.getvalue()


def _flush(window) -> None:
    window._render_timer.stop()
    window._do_render()
    QApplication.processEvents()
    QApplication.processEvents()


def _open(window, path) -> None:
    window.open_pdf(str(path))
    _flush(window)
    _flush(window)


def _controller(window):
    controller = window._edit_for_current()
    assert controller is not None
    return controller


def _page_label(window, index=0):
    return window._continuous_pages[index]


def _zoom(window):
    return window._continuous_layout_zoom or 1.0


def _add_text(window, page_index=0, x=100, y=120):
    window._activate_edit_tool("text", True)
    QApplication.processEvents()
    controller = _controller(window)
    before = {obj.oid for obj in controller.objects}
    label = _page_label(window, page_index)
    controller.handle_page_click(
        page_index, label, QPoint(x, y), _zoom(window)
    )
    QApplication.processEvents()
    created = [obj for obj in controller.objects if obj.oid not in before]
    assert len(created) == 1
    return controller, created[0]


def test_window_has_edit_tools_and_hidden_context_bar(make_window):
    window = make_window()
    for name in ("fill_button", "text_button", "sign_button", "image_button"):
        assert hasattr(window, name)
    assert window.context_toolbar is not None
    assert window.context_toolbar.isHidden()


def test_add_text_commit_save_and_reopen(tmp_path, make_window, make_pdf):
    pdf = make_pdf(1, body="Page content")
    window = make_window()
    _open(window, pdf)

    controller, obj = _add_text(window)
    assert obj.kind == eo.TEXT_KIND
    assert controller._editor is not None
    assert window.context_toolbar.isVisible()
    assert window._ctx_done.isVisible()

    controller._commit_text_edit(obj.oid, "Hello edit")
    QApplication.processEvents()
    assert not window._ctx_done.isVisible()
    _flush(window)
    saved = controller.object_by_oid(obj.oid)
    assert saved is not None and saved.text == "Hello edit"
    assert window._document_dirty(window.current_tab_id)
    assert window.windowTitle().startswith("●")

    assert window._save_document() is True
    assert not window._document_dirty(window.current_tab_id)
    assert not window.windowTitle().startswith("●")

    second = make_window()
    _open(second, pdf)
    objects = eo.list_objects(second.document)
    assert len(objects) == 1
    assert objects[0].kind == eo.TEXT_KIND
    assert objects[0].text == "Hello edit"


def test_text_style_and_context_toolbar(make_window, make_pdf):
    pdf = make_pdf(1)
    window = make_window()
    _open(window, pdf)
    controller, obj = _add_text(window)
    controller._commit_text_edit(obj.oid, "Styled")
    _flush(window)

    assert window.context_toolbar.isVisible()
    window._ctx_font.setCurrentIndex(
        window._ctx_font.findData("Times-Roman")
    )
    window._ctx_size.setValue(24)
    window._ctx_bold.setChecked(True)
    window._ctx_underline.setChecked(True)
    window._on_context_style_changed()
    _flush(window)

    updated = controller.object_by_oid(obj.oid)
    assert updated is not None
    assert updated.style.font_family == "Times-Roman"
    assert updated.style.font_size >= 20
    assert updated.style.bold and updated.style.underline


def test_image_placement_undo_redo(make_window, make_pdf):
    pdf = make_pdf(1)
    window = make_window()
    _open(window, pdf)
    controller = _controller(window)
    label = _page_label(window)
    controller.set_pending_image("signature", _png(), "Test")
    controller.handle_page_click(0, label, QPoint(150, 350), _zoom(window))
    _flush(window)
    assert len(controller.objects) == 1
    obj = controller.objects[0]
    assert obj.kind == eo.SIGNATURE_KIND
    assert obj.name == "Test"

    assert controller.undo() is True
    _flush(window)
    assert eo.list_objects(window.document) == []
    assert controller.redo() is True
    _flush(window)
    objects = eo.list_objects(window.document)
    assert len(objects) == 1 and objects[0].kind == eo.SIGNATURE_KIND


def test_continuous_mode_editing_and_overlay_scaling(make_window, make_pdf):
    pdf = make_pdf(4)
    window = make_window()
    _open(window, pdf)
    controller, obj = _add_text(window, page_index=1, x=100, y=100)
    controller._commit_text_edit(obj.oid, "Page two")
    _flush(window)
    assert obj.page_index == 1

    overlay = controller._overlays.get(obj.oid)
    if overlay is not None:
        before = overlay.geometry()
        window.zoom_in()
        _flush(window)
        overlay = controller._overlays.get(obj.oid)
        if overlay is not None:
            assert overlay.geometry().width() > before.width()

    # The object survives navigation and page changes.
    window.jump_to_page(4)
    _flush(window)
    window.jump_to_page(2)
    _flush(window)
    assert eo.list_objects(window.document)[0].text == "Page two"


def test_duplicate_and_delete(make_window, make_pdf):
    pdf = make_pdf(1)
    window = make_window()
    _open(window, pdf)
    controller, obj = _add_text(window)
    controller._commit_text_edit(obj.oid, "Duplicate me")
    _flush(window)
    controller.select(obj.oid)
    controller.duplicate_selected()
    _flush(window)
    assert len(eo.list_objects(window.document)) == 2
    controller.select(obj.oid)
    controller.delete_selected()
    _flush(window)
    assert len(eo.list_objects(window.document)) == 1


def test_save_as_and_flattened_export(
    tmp_path, monkeypatch, make_window, make_pdf
):
    pdf = make_pdf(1)
    window = make_window()
    _open(window, pdf)
    controller, obj = _add_text(window)
    controller._commit_text_edit(obj.oid, "Export me")
    _flush(window)

    target = tmp_path / "saved-as.pdf"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(target), "PDF files (*.pdf)"),
    )
    assert window._save_document_as() is True
    assert target.exists()
    reopened = fitz.open(target)
    try:
        assert any(o.text == "Export me" for o in eo.list_objects(reopened))
    finally:
        reopened.close()

    flat = tmp_path / "flat.pdf"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(flat), "PDF files (*.pdf)"),
    )
    window._export_flattened()
    assert flat.exists()
    flattened = fitz.open(flat)
    try:
        assert list(flattened[0].annots()) == []
        assert "Export me" in flattened[0].get_text()
    finally:
        flattened.close()


def test_tool_activation_and_escape(make_window, make_pdf):
    pdf = make_pdf(1)
    window = make_window()
    _open(window, pdf)
    window._activate_edit_tool("text", True)
    controller = _controller(window)
    assert controller.tool == "text"
    assert window.text_button.isChecked()
    assert window._edit_escape() is True
    assert controller.tool is None
    assert not window.text_button.isChecked()


def test_rotated_pages_are_safely_rejected(make_window, tmp_path):
    pdf = tmp_path / "rotated.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), "Rotated", fontsize=18)
    page.set_rotation(90)
    doc.save(pdf)
    doc.close()

    window = make_window()
    _open(window, pdf)
    controller = _controller(window)
    controller.set_tool("text")
    label = _page_label(window)
    consumed = controller.handle_page_click(
        0, label, QPoint(80, 80), _zoom(window)
    )
    assert consumed is True
    assert controller.objects == []


def test_inline_editor_ctrl_enter_commits(make_window, make_pdf):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    pdf = make_pdf(1)
    window = make_window()
    _open(window, pdf)
    controller, obj = _add_text(window)
    editor = controller._editor
    assert editor is not None
    editor.setPlainText("Typed in the editor")
    QTest.keyClick(editor, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    QApplication.processEvents()
    _flush(window)
    assert controller.object_by_oid(obj.oid).text == "Typed in the editor"


def test_text_rotation_swaps_rect_and_persists(make_window, make_pdf):
    pdf = make_pdf(1)
    window = make_window()
    _open(window, pdf)
    controller, obj = _add_text(window)
    controller._commit_text_edit(obj.oid, "Rotate me")
    _flush(window)
    before = controller.object_by_oid(obj.oid)
    width = before.rect[2] - before.rect[0]
    height = before.rect[3] - before.rect[1]

    controller.select(obj.oid)
    controller.rotate_selected(90)
    _flush(window)

    rotated = controller.object_by_oid(obj.oid)
    assert rotated.rotation == 90
    assert (rotated.rect[2] - rotated.rect[0]) == pytest.approx(height, abs=2)
    assert (rotated.rect[3] - rotated.rect[1]) == pytest.approx(width, abs=2)
    assert eo.list_objects(window.document)[0].rotation == 90


def test_context_toolbar_hides_text_controls_for_images(make_window, make_pdf):
    pdf = make_pdf(1)
    window = make_window()
    _open(window, pdf)
    controller = _controller(window)
    controller.set_pending_image("signature", _png(), "Test")
    label = _page_label(window)
    controller.handle_page_click(0, label, QPoint(200, 400), _zoom(window))
    _flush(window)
    signature = [o for o in controller.objects if o.kind == eo.SIGNATURE_KIND][0]
    controller.select(signature.oid)
    QApplication.processEvents()
    assert window.context_toolbar.isVisible()
    assert not window._ctx_text_actions[0].isVisible()
    assert window._ctx_rotate.isVisible()
    assert not window._ctx_done.isVisible()


def test_coordinate_mapping_at_two_zoom_levels(make_window, make_pdf):
    pdf = make_pdf(1)
    window = make_window()
    _open(window, pdf)

    def expected(point, zoom):
        page_rect = window.document[0].rect
        return (
            page_rect.x0 + (point.x() - 1) / zoom,
            page_rect.y0 + (point.y() - 1) / zoom,
        )

    controller, obj = _add_text(window, x=100, y=140)
    zoom = _zoom(window)
    ex, ey = expected(QPoint(100, 140), zoom)
    assert obj.rect[0] == pytest.approx(ex, abs=1)
    assert obj.rect[1] == pytest.approx(ey, abs=1)
    controller._commit_text_edit(obj.oid, "One")
    _flush(window)

    window.zoom_in()
    _flush(window)
    controller, obj2 = _add_text(window, x=180, y=220)
    zoom2 = _zoom(window)
    ex2, ey2 = expected(QPoint(180, 220), zoom2)
    assert obj2.rect[0] == pytest.approx(ex2, abs=1)
    assert obj2.rect[1] == pytest.approx(ey2, abs=1)


def test_typed_signature_dialog_produces_png(tmp_path):
    from pdfreader_lib import signature_store as ss

    store = ss.SignatureStore(tmp_path / "sigs")
    dialog = edit_gui.SignatureDialog(store)
    dialog.tabs.setCurrentIndex(1)
    dialog.type_name.setText("Sparsh Sam")
    assert dialog.type_font.count() > 0
    dialog._accept()
    assert dialog.result_png
    assert dialog.result_png[:8] == b"\x89PNG\r\n\x1a\n"
    assert dialog.result_kind == "typed"


def test_drawn_canvas_produces_transparent_png():
    from PySide6.QtCore import QPointF

    canvas = edit_gui.SignatureCanvas()
    canvas.resize(400, 200)
    canvas._strokes = [[QPointF(20, 120), QPointF(120, 40), QPointF(260, 140)]]
    assert canvas.has_content()
    png = canvas.to_png()
    image = Image.open(io.BytesIO(png))
    assert image.mode == "RGBA"
    assert image.size[0] > 0 and image.size[1] > 0
    canvas.clear()
    assert not canvas.has_content()


def test_dark_theme_keeps_edit_toolbar_styled(make_window):
    window = make_window()
    window.set_theme(window.THEME_DARK)
    assert "ContextToolbar" in window.styleSheet()
    window.set_theme(window.THEME_LIGHT)
    assert "ContextToolbar" in window.styleSheet()
