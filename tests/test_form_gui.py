"""Offscreen GUI smoke tests for the AcroForm overlay feature (Phase 2).

These exercise the FormController without a display: field-index building,
overlay widget creation, dirty tracking, and save→reopen persistence. They
skip cleanly when a Qt platform (e.g. offscreen) is unavailable.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from pdfreader_lib import form_fields as ff
from tests._form_fixtures import make_form_fixture

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication, QMessageBox
except Exception:  # pragma: no cover - Qt not importable
    QApplication = None  # type: ignore

pytestmark = pytest.mark.skipif(QApplication is None, reason="PySide6 not available")

if QApplication is not None:
    from main import PdfReaderWindow

    # Blocking dialogs never render during tests. Discard = let close proceed.
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Discard)
    # Session restore shows a modal prompt 100 ms after window creation; the
    # offscreen test driver cannot answer it, so neutralize it.
    PdfReaderWindow._restore_session = lambda self, force=False: None
    PdfReaderWindow._do_restore_session = lambda self: None


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("OpenReader-Test")
    yield app


@pytest.fixture
def form_window(qapp, tmp_path):
    from main import PdfReaderWindow

    path = tmp_path / "form.pdf"
    make_form_fixture(str(path))
    win = PdfReaderWindow()
    win.show()
    win.open_pdf(str(path))
    win._do_render()  # synchronous render (bypasses the debounce timer)
    qapp.processEvents()
    yield win, path
    win.close()
    qapp.processEvents()


def test_form_controller_built(form_window):
    win, _path = form_window
    controller = win._form_for_current()
    assert controller is not None
    assert len(controller.fields) >= 9
    assert len(controller.editable_fields) >= 9


def test_overlay_widgets_attached(form_window):
    win, _path = form_window
    controller = win._form_for_current()
    assert controller._widgets, "expected overlay widgets on the rendered page"


def test_editing_marks_dirty_and_persists(form_window, qapp):
    win, path = form_window
    controller = win._form_for_current()

    for name, value in {"fullname": "Alice Smith", "country": "UK", "gender": "M"}.items():
        field = next(f for f in controller.fields if f.name == name)
        widget = controller._field_widgets.get(field.name)[0]
        if field.field_type == ff.FieldType.RADIO:
            controller._set_widget_value(field, value)
            controller.on_radio(field, value)
        elif field.field_type in (ff.FieldType.COMBO, ff.FieldType.LISTBOX):
            controller._set_widget_value(field, value)
            controller.on_edited(field)
        else:
            widget.setText(value)
            widget.textEdited.emit(value)
    assert controller.dirty is True

    win._save_document()
    assert controller.dirty is False

    # The values must be written into the PDF on disk (appearance + value).
    # Read the file back with the shared module (no second window needed).
    import fitz

    doc = fitz.open(str(path))
    try:
        fields = ff.build_field_index(doc)
        for name, expected in {"fullname": "Alice Smith", "country": "UK", "gender": "M"}.items():
            field = next(f for f in fields if f.name == name)
            assert ff.get_field_value(doc, field) == expected, name
    finally:
        doc.close()


def test_required_validation_message(form_window):
    win, _path = form_window
    controller = win._form_for_current()
    dob = next(f for f in controller.fields if f.name == "dob")
    widget = controller._field_widgets.get(dob.name)[0]
    widget.setText("not-a-date")
    controller.on_commit(dob, widget.text())
    assert dob.validation_message
    assert "date" in dob.validation_message.lower()
