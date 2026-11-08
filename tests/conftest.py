"""Shared fixtures for OpenReader tests.

Qt tests run offscreen so they work in CI without a display. QSettings is
redirected to a temporary directory so tests never touch a developer's real
configuration.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import fitz  # noqa: E402
import pytest  # noqa: E402
from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import main as app_main  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path):
    """Keep QSettings out of the developer's real configuration."""
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path)
    )
    QSettings.setPath(
        QSettings.Format.IniFormat, QSettings.Scope.SystemScope, str(tmp_path)
    )
    settings = QSettings("Sparsh Sam", "OpenReader")
    settings.setValue("autoCheckUpdates", False)
    settings.setValue("autoRestore", False)
    settings.sync()
    yield


@pytest.fixture
def make_window(qapp):
    """Factory that creates a shown, offscreen PdfReaderWindow."""
    created = []

    def _make():
        window = app_main.PdfReaderWindow()
        window.resize(1000, 800)
        window.show()
        qapp.processEvents()
        created.append(window)
        return window

    yield _make

    for window in created:
        window.close()
        window.deleteLater()
    qapp.processEvents()


@pytest.fixture
def make_pdf(tmp_path):
    """Factory that writes a simple multi-page PDF and returns its path."""
    counter = {"n": 0}

    def _make(pages: int, label: str | None = None, body: str | None = None):
        counter["n"] += 1
        path = tmp_path / f"{label or 'document'}-{counter['n']}.pdf"
        doc = fitz.open()
        for index in range(pages):
            page = doc.new_page(width=612, height=792)
            page.insert_text((72, 72), f"Page {index + 1}", fontsize=20)
            if body:
                page.insert_text((72, 120), body, fontsize=14)
        doc.save(str(path))
        doc.close()
        return path

    return _make
