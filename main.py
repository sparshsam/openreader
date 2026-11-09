import json
import math
import os
import platform
import re
import sys
import tempfile
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import fitz
from PySide6.QtCore import QBuffer, QByteArray, QEvent, QObject, QPoint, QPointF, QRect, QRectF, QSettings, QSize, QStandardPaths, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QDesktopServices, QIcon, QImage, QKeySequence, QPainter, QPainterPath, QPalette, QPen, QPixmap, QPolygonF, QShortcut
from PySide6.QtNetwork import QLocalServer, QLocalSocket, QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QButtonGroup,
    QCalendarWidget,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QScrollBar,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QStyle,
    QTabBar,
    QTextBrowser,
    QTextEdit,
    QToolBar,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


__version__ = "1.3.0"
GITHUB_REPO = "sparshsam/openreader"
IPC_SERVER_NAME = "OpenReader-IPC"
RECENT_FILES_MAX = 10
SETTINGS_RECENT_KEY = "recentFiles"
SETTINGS_AUTO_UPDATE_KEY = "autoCheckUpdates"
SETTINGS_DEFAULT_PROMPT_KEY = "defaultAppPromptShown"
SETTINGS_DEFAULT_DONT_ASK_KEY = "defaultAppDontAsk"
SETTINGS_UPDATE_SKIP_KEY = "updateSkipVersion"
SETTINGS_UPDATE_LAST_CHECKED_KEY = "updateLastChecked"


def should_suppress_silent_notify(result: dict, skip_version: str | None) -> bool:
    """True when a silent update check should not re-notify about a release.

    Suppression is exact-tag equality against the version the user skipped —
    a newer release still notifies.
    """
    if result.get("outcome") != "update_available":
        return False
    latest = result.get("latest_tag")
    return bool(latest) and bool(skip_version) and latest == skip_version

# ── Performance timer ─────────────────────────────────────────────────

import time as _time


def _perf_start() -> float:
    """Return a timestamp for performance measurement."""
    return _time.perf_counter()


def _perf_end(start: float, label: str) -> None:
    """Log elapsed time for *label* to stdout (dev builds only).

    In packaged builds this is silent — the function is a no-op in
    frozen mode.
    """
    elapsed = (_time.perf_counter() - start) * 1000
    if not getattr(sys, "frozen", False):
        print(f"[PERF] {label}: {elapsed:.1f} ms")

# Optional modules (graceful if missing)
try:
    from pdfreader_lib import search_index as lib_idx
    from pdfreader_lib import comparison as pdf_compare
    HAS_LIB_MODULES = True
except ImportError:
    HAS_LIB_MODULES = False

# Windows default-app detection (stdlib only; no-op on non-Windows).
from pdfreader_lib import win_default_apps

# Install-source detection for channel-aware updates (stdlib only).
from pdfreader_lib import install_source

# AcroForm field intelligence (Phase 2) — shared with the MCP server.
from pdfreader_lib import form_fields as _ff
from pdfreader_lib import edit_gui as edit_ui
from pdfreader_lib import edit_objects as eo
from pdfreader_lib import signature_store as sig_store


# ---------------------------------------------------------------------------
# Per-tab state container
# ---------------------------------------------------------------------------

@dataclass
class TabData:
    name: str
    path: str | None = None
    document: fitz.Document | None = None
    current_page: int = 0
    zoom: float = 1.25
    fit_to_window: bool = True
    search_text: str = ""
    search_results: list = field(default_factory=list)
    current_result_index: int = -1
    current_render_zoom: float = 1.0
    selected_text: str = ""
    selected_rects: list = field(default_factory=list)
    ocr_text_pages: OrderedDict = field(default_factory=OrderedDict)
    ocr_warning_shown: bool = False
    encrypted: bool = False


# ---------------------------------------------------------------------------
# Stylesheets
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Stylesheets
# ---------------------------------------------------------------------------

LIGHT_STYLESHEET = """
/* OpenReader — Fluent light theme */
QMainWindow, QDialog {
    background-color: #f3f3f5;
    color: #1b1b1f;
}
QWidget {
    color: #1b1b1f;
}
QMainWindow::separator {
    background-color: #e4e4e8;
    width: 1px;
    height: 1px;
}
QMenuBar {
    background-color: #fbfbfc;
    color: #1b1b1f;
    border: none;
    border-bottom: 1px solid #e8e8ec;
    padding: 2px 6px;
    spacing: 2px;
}
QMenuBar::item {
    padding: 5px 10px;
    border-radius: 6px;
    background: transparent;
}
QMenuBar::item:selected {
    background-color: rgba(0, 0, 0, 0.06);
}
QMenu {
    background-color: #ffffff;
    color: #1b1b1f;
    border: 1px solid #e2e2e6;
    border-radius: 8px;
    padding: 5px;
}
QMenu::item {
    padding: 7px 28px 7px 14px;
    border-radius: 5px;
}
QMenu::item:selected {
    background-color: rgba(0, 0, 0, 0.06);
}
QMenu::item:disabled {
    color: #a1a2a9;
}
QMenu::separator {
    height: 1px;
    background-color: #ececef;
    margin: 5px 8px;
}
QToolBar#MainToolbar {
    background-color: #fbfbfc;
    border: none;
    border-bottom: 1px solid #e8e8ec;
    padding: 6px;
    spacing: 3px;
}
QToolBar#MainToolbar::separator {
    width: 1px;
    background-color: #e6e6ea;
    margin: 7px 7px;
}
QToolBar#MainToolbar::extension {
    background: transparent;
    border: none;
}
QToolBar#MainToolbar QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 0px;
}
QToolBar#MainToolbar QToolButton:hover {
    background-color: rgba(0, 0, 0, 0.05);
}
QToolBar#MainToolbar QToolButton:pressed {
    background-color: rgba(0, 0, 0, 0.09);
}
QToolBar#MainToolbar QToolButton:checked {
    background-color: rgba(255, 37, 95, 0.10);
    border-color: rgba(255, 37, 95, 0.30);
}
QToolBar#MainToolbar QToolButton:disabled,
QToolBar#MainToolbar QToolButton:checked:disabled {
    background: transparent;
    border-color: transparent;
}
QSpinBox#PageSpin {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 3px 2px;
    color: #1b1b1f;
    font-weight: 600;
    selection-background-color: #ff255f;
    selection-color: #ffffff;
}
QSpinBox#PageSpin:hover {
    background-color: #ffffff;
    border-color: #e2e2e6;
}
QSpinBox#PageSpin:focus {
    background-color: #ffffff;
    border-color: #ff255f;
}
QLabel#PageCount, QLabel#ZoomLabel, QLabel#SearchCount {
    color: #6e6f76;
    font-size: 12px;
    font-weight: 500;
}
QLineEdit#SearchInput {
    background-color: #ffffff;
    color: #1b1b1f;
    border: 1px solid #e2e2e6;
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 22px;
    selection-background-color: #ff255f;
    selection-color: #ffffff;
}
QLineEdit#SearchInput:focus {
    border-color: #ff255f;
}
QToolBar#MainToolbar QToolButton#SemanticToggle {
    color: #6e6f76;
    font-size: 12px;
    font-weight: 500;
    padding: 0px 10px;
    min-height: 24px;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
}
QToolBar#MainToolbar QToolButton#SemanticToggle:hover {
    background-color: rgba(0, 0, 0, 0.05);
}
QToolBar#MainToolbar QToolButton#SemanticToggle:checked {
    background-color: rgba(255, 37, 95, 0.10);
    border-color: rgba(255, 37, 95, 0.30);
    color: #1b1b1f;
}
QToolBar#MainToolbar QToolButton#SemanticToggle:disabled {
    color: #aaabb2;
}
QToolBar#ContextToolbar {
    background-color: #fbfbfc;
    border: none;
    border-bottom: 1px solid #e8e8ec;
    padding: 4px 10px;
    spacing: 4px;
}
QToolBar#ContextToolbar QToolButton#CtxButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 3px 8px;
    color: #1b1b1f;
    font-size: 12px;
}
QToolBar#ContextToolbar QToolButton#CtxButton:hover {
    background-color: rgba(0, 0, 0, 0.05);
}
QToolBar#ContextToolbar QToolButton#CtxButton:checked {
    background-color: rgba(255, 37, 95, 0.10);
    border-color: rgba(255, 37, 95, 0.30);
}
QToolBar#ContextToolbar QLabel#CtxLabel {
    color: #6e6f76;
    font-size: 12px;
}
QToolBar#ContextToolbar QComboBox#CtxCombo,
QToolBar#ContextToolbar QSpinBox#CtxSpin {
    background-color: #ffffff;
    color: #1b1b1f;
    border: 1px solid #dfe0e4;
    border-radius: 5px;
    padding: 3px 6px;
    min-height: 22px;
}
QTabBar {
    background: transparent;
}
QTabBar::tab {
    background: transparent;
    color: #6e6f76;
    padding: 5px 14px;
    margin: 5px 3px;
    border: 1px solid transparent;
    border-radius: 7px;
    min-height: 18px;
}
QTabBar::tab:selected {
    background-color: #ffffff;
    color: #1b1b1f;
    border-color: #e2e2e6;
}
QTabBar::tab:hover:!selected {
    background-color: rgba(0, 0, 0, 0.05);
    color: #1b1b1f;
}
#TabStrip {
    background-color: #f3f3f5;
    border-bottom: 1px solid #e8e8ec;
}
QToolButton#NewTabButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 0px;
}
QToolButton#NewTabButton:hover {
    background-color: rgba(0, 0, 0, 0.05);
}
QToolButton#TabCloseButton {
    background-color: transparent;
    border: none;
    border-radius: 5px;
    color: #7b7c83;
    font-size: 15px;
    font-weight: 500;
    padding: 0px;
}
QToolButton#TabCloseButton:hover {
    background-color: rgba(0, 0, 0, 0.08);
    color: #1b1b1f;
}
QToolButton#TabCloseButton:pressed {
    background-color: rgba(0, 0, 0, 0.12);
}
QPushButton {
    background-color: #ffffff;
    color: #1b1b1f;
    border: 1px solid #dfe0e4;
    padding: 5px 14px;
    border-radius: 6px;
    min-height: 22px;
}
QPushButton:hover {
    background-color: #f6f6f8;
    border-color: #cfd0d5;
}
QPushButton:pressed {
    background-color: #ececef;
}
QPushButton:default {
    background-color: #ff255f;
    color: #ffffff;
    border-color: #ff255f;
}
QPushButton:default:hover {
    background-color: #f01650;
    border-color: #f01650;
}
QPushButton:checked {
    background-color: rgba(255, 37, 95, 0.10);
    color: #1b1b1f;
    border-color: rgba(255, 37, 95, 0.30);
}
QPushButton:disabled {
    background-color: #f2f2f4;
    color: #aaabb2;
    border-color: #e8e8ec;
}
QPushButton#OpenEmptyButton {
    background-color: #ff255f;
    color: #ffffff;
    border: none;
    border-radius: 7px;
    padding: 9px 22px;
    font-weight: 600;
}
QPushButton#OpenEmptyButton:hover {
    background-color: #f01650;
}
QPushButton#OpenEmptyButton:pressed {
    background-color: #d90f47;
}
QLineEdit {
    background-color: #ffffff;
    color: #1b1b1f;
    border: 1px solid #dfe0e4;
    padding: 5px 8px;
    border-radius: 6px;
    selection-background-color: #ff255f;
    selection-color: #ffffff;
}
QLineEdit:focus {
    border-color: #ff255f;
}
QSpinBox {
    background-color: #ffffff;
    color: #1b1b1f;
    border: 1px solid #dfe0e4;
    padding: 4px;
    border-radius: 6px;
}
QSpinBox:focus {
    border-color: #ff255f;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #f1f1f3;
    border: none;
    width: 18px;
}
QLabel {
    color: #1b1b1f;
    background-color: transparent;
}
QLabel#EmptyTitle {
    color: #1b1b1f;
    font-size: 19px;
    font-weight: 600;
}
QLabel#EmptySubtitle {
    color: #6e6f76;
    font-size: 13px;
}
QLabel#PdfPage, QLabel#ContinuousPage {
    background-color: #ffffff;
    border: 1px solid #d8d8dc;
}
QStatusBar {
    background-color: #fbfbfc;
    color: #6e6f76;
    border-top: 1px solid #e8e8ec;
    padding: 2px 8px;
}
QScrollArea {
    background-color: #ececee;
    border: none;
}
QWidget#ContinuousDocument, QWidget#DocumentViewport {
    background-color: #ececee;
}
QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background-color: #c4c5ca;
    border-radius: 4px;
    min-height: 36px;
    margin: 0px 2px;
}
QScrollBar::handle:vertical:hover {
    background-color: #a8a9af;
}
QScrollBar:horizontal {
    background: transparent;
    height: 12px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background-color: #c4c5ca;
    border-radius: 4px;
    min-width: 36px;
    margin: 2px 0px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #a8a9af;
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0px;
    height: 0px;
}
QScrollBar::add-page, QScrollBar::sub-page {
    background: transparent;
}
QProgressDialog {
    background-color: #f3f3f5;
    color: #1b1b1f;
}
QMessageBox {
    background-color: #f3f3f5;
    color: #1b1b1f;
}
QMessageBox QLabel {
    color: #1b1b1f;
}
QMessageBox QPushButton {
    min-width: 84px;
}
QInputDialog {
    background-color: #f3f3f5;
    color: #1b1b1f;
}
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e2e2e6;
    border-radius: 8px;
    margin-top: 12px;
    padding: 14px 12px 12px 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0px 4px;
    color: #6e6f76;
    font-size: 12px;
    font-weight: 600;
}
QToolTip {
    background-color: #2b2b31;
    color: #ffffff;
    border: 1px solid #3a3a42;
    border-radius: 6px;
    padding: 5px 8px;
}
"""

DARK_STYLESHEET = """
/* OpenReader — Fluent dark theme */
QMainWindow, QDialog {
    background-color: #1a1b1e;
    color: #ececed;
}
QWidget {
    color: #ececed;
}
QMainWindow::separator {
    background-color: #2b2c31;
    width: 1px;
    height: 1px;
}
QMenuBar {
    background-color: #222327;
    color: #ececed;
    border: none;
    border-bottom: 1px solid #2b2c31;
    padding: 2px 6px;
    spacing: 2px;
}
QMenuBar::item {
    padding: 5px 10px;
    border-radius: 6px;
    background: transparent;
}
QMenuBar::item:selected {
    background-color: rgba(255, 255, 255, 0.07);
}
QMenu {
    background-color: #26272c;
    color: #ececed;
    border: 1px solid #35363c;
    border-radius: 8px;
    padding: 5px;
}
QMenu::item {
    padding: 7px 28px 7px 14px;
    border-radius: 5px;
}
QMenu::item:selected {
    background-color: rgba(255, 255, 255, 0.07);
}
QMenu::item:disabled {
    color: #6a6b73;
}
QMenu::separator {
    height: 1px;
    background-color: #35363c;
    margin: 5px 8px;
}
QToolBar#MainToolbar {
    background-color: #222327;
    border: none;
    border-bottom: 1px solid #2b2c31;
    padding: 6px;
    spacing: 3px;
}
QToolBar#MainToolbar::separator {
    width: 1px;
    background-color: #34353b;
    margin: 7px 7px;
}
QToolBar#MainToolbar::extension {
    background: transparent;
    border: none;
}
QToolBar#MainToolbar QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 0px;
}
QToolBar#MainToolbar QToolButton:hover {
    background-color: rgba(255, 255, 255, 0.06);
}
QToolBar#MainToolbar QToolButton:pressed {
    background-color: rgba(255, 255, 255, 0.10);
}
QToolBar#MainToolbar QToolButton:checked {
    background-color: rgba(255, 77, 122, 0.14);
    border-color: rgba(255, 77, 122, 0.40);
}
QToolBar#MainToolbar QToolButton:disabled,
QToolBar#MainToolbar QToolButton:checked:disabled {
    background: transparent;
    border-color: transparent;
}
QSpinBox#PageSpin {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 3px 2px;
    color: #ececed;
    font-weight: 600;
    selection-background-color: #ff4d7a;
    selection-color: #1a1b1e;
}
QSpinBox#PageSpin:hover {
    background-color: #2a2b30;
    border-color: #34353b;
}
QSpinBox#PageSpin:focus {
    background-color: #2a2b30;
    border-color: #ff4d7a;
}
QLabel#PageCount, QLabel#ZoomLabel, QLabel#SearchCount {
    color: #9b9ca4;
    font-size: 12px;
    font-weight: 500;
}
QLineEdit#SearchInput {
    background-color: #2a2b30;
    color: #ececed;
    border: 1px solid #34353b;
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 22px;
    selection-background-color: #ff4d7a;
    selection-color: #1a1b1e;
}
QLineEdit#SearchInput:focus {
    border-color: #ff4d7a;
}
QToolBar#MainToolbar QToolButton#SemanticToggle {
    color: #9b9ca4;
    font-size: 12px;
    font-weight: 500;
    padding: 0px 10px;
    min-height: 24px;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
}
QToolBar#MainToolbar QToolButton#SemanticToggle:hover {
    background-color: rgba(255, 255, 255, 0.06);
}
QToolBar#MainToolbar QToolButton#SemanticToggle:checked {
    background-color: rgba(255, 77, 122, 0.14);
    border-color: rgba(255, 77, 122, 0.40);
    color: #ececed;
}
QToolBar#MainToolbar QToolButton#SemanticToggle:disabled {
    color: #55565e;
}
QToolBar#ContextToolbar {
    background-color: #222327;
    border: none;
    border-bottom: 1px solid #2b2c31;
    padding: 4px 10px;
    spacing: 4px;
}
QToolBar#ContextToolbar QToolButton#CtxButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 3px 8px;
    color: #ececed;
    font-size: 12px;
}
QToolBar#ContextToolbar QToolButton#CtxButton:hover {
    background-color: rgba(255, 255, 255, 0.06);
}
QToolBar#ContextToolbar QToolButton#CtxButton:checked {
    background-color: rgba(255, 77, 122, 0.14);
    border-color: rgba(255, 77, 122, 0.40);
}
QToolBar#ContextToolbar QLabel#CtxLabel {
    color: #9b9ca4;
    font-size: 12px;
}
QToolBar#ContextToolbar QComboBox#CtxCombo,
QToolBar#ContextToolbar QSpinBox#CtxSpin {
    background-color: #2a2b30;
    color: #ececed;
    border: 1px solid #3a3b42;
    border-radius: 5px;
    padding: 3px 6px;
    min-height: 22px;
}
QTabBar {
    background: transparent;
}
QTabBar::tab {
    background: transparent;
    color: #9b9ca4;
    padding: 5px 14px;
    margin: 5px 3px;
    border: 1px solid transparent;
    border-radius: 7px;
    min-height: 18px;
}
QTabBar::tab:selected {
    background-color: #2a2b30;
    color: #ececed;
    border-color: #35363c;
}
QTabBar::tab:hover:!selected {
    background-color: rgba(255, 255, 255, 0.06);
    color: #ececed;
}
#TabStrip {
    background-color: #1a1b1e;
    border-bottom: 1px solid #2b2c31;
}
QToolButton#NewTabButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 0px;
}
QToolButton#NewTabButton:hover {
    background-color: rgba(255, 255, 255, 0.06);
}
QToolButton#TabCloseButton {
    background-color: transparent;
    border: none;
    border-radius: 5px;
    color: #8b8c94;
    font-size: 15px;
    font-weight: 500;
    padding: 0px;
}
QToolButton#TabCloseButton:hover {
    background-color: rgba(255, 255, 255, 0.09);
    color: #ececed;
}
QToolButton#TabCloseButton:pressed {
    background-color: rgba(255, 255, 255, 0.13);
}
QPushButton {
    background-color: #2a2b30;
    color: #ececed;
    border: 1px solid #3a3b42;
    padding: 5px 14px;
    border-radius: 6px;
    min-height: 22px;
}
QPushButton:hover {
    background-color: #33343a;
    border-color: #46474f;
}
QPushButton:pressed {
    background-color: #3b3c44;
}
QPushButton:default {
    background-color: #ff4d7a;
    color: #1a1b1e;
    border-color: #ff4d7a;
}
QPushButton:default:hover {
    background-color: #ff6690;
    border-color: #ff6690;
}
QPushButton:checked {
    background-color: rgba(255, 77, 122, 0.14);
    color: #ececed;
    border-color: rgba(255, 77, 122, 0.40);
}
QPushButton:disabled {
    background-color: #212226;
    color: #55565e;
    border-color: #2c2d32;
}
QPushButton#OpenEmptyButton {
    background-color: #ff4d7a;
    color: #1a1b1e;
    border: none;
    border-radius: 7px;
    padding: 9px 22px;
    font-weight: 600;
}
QPushButton#OpenEmptyButton:hover {
    background-color: #ff6690;
}
QPushButton#OpenEmptyButton:pressed {
    background-color: #e63d67;
}
QLineEdit {
    background-color: #2a2b30;
    color: #ececed;
    border: 1px solid #3a3b42;
    padding: 5px 8px;
    border-radius: 6px;
    selection-background-color: #ff4d7a;
    selection-color: #1a1b1e;
}
QLineEdit:focus {
    border-color: #ff4d7a;
}
QSpinBox {
    background-color: #2a2b30;
    color: #ececed;
    border: 1px solid #3a3b42;
    padding: 4px;
    border-radius: 6px;
}
QSpinBox:focus {
    border-color: #ff4d7a;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #34353b;
    border: none;
    width: 18px;
}
QLabel {
    color: #ececed;
    background-color: transparent;
}
QLabel#EmptyTitle {
    color: #ececed;
    font-size: 19px;
    font-weight: 600;
}
QLabel#EmptySubtitle {
    color: #9b9ca4;
    font-size: 13px;
}
QLabel#PdfPage, QLabel#ContinuousPage {
    background-color: #ffffff;
    border: 1px solid #3a3b42;
}
QStatusBar {
    background-color: #222327;
    color: #9b9ca4;
    border-top: 1px solid #2b2c31;
    padding: 2px 8px;
}
QScrollArea {
    background-color: #141518;
    border: none;
}
QWidget#ContinuousDocument, QWidget#DocumentViewport {
    background-color: #141518;
}
QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background-color: #45464e;
    border-radius: 4px;
    min-height: 36px;
    margin: 0px 2px;
}
QScrollBar::handle:vertical:hover {
    background-color: #5c5d66;
}
QScrollBar:horizontal {
    background: transparent;
    height: 12px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background-color: #45464e;
    border-radius: 4px;
    min-width: 36px;
    margin: 2px 0px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #5c5d66;
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0px;
    height: 0px;
}
QScrollBar::add-page, QScrollBar::sub-page {
    background: transparent;
}
QProgressDialog {
    background-color: #1a1b1e;
    color: #ececed;
}
QMessageBox {
    background-color: #1a1b1e;
    color: #ececed;
}
QMessageBox QLabel {
    color: #ececed;
}
QMessageBox QPushButton {
    min-width: 84px;
}
QInputDialog {
    background-color: #1a1b1e;
    color: #ececed;
}
QGroupBox {
    background-color: #222327;
    border: 1px solid #34353b;
    border-radius: 8px;
    margin-top: 12px;
    padding: 14px 12px 12px 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0px 4px;
    color: #9b9ca4;
    font-size: 12px;
    font-weight: 600;
}
QToolTip {
    background-color: #33343a;
    color: #f2f2f4;
    border: 1px solid #45464e;
    border-radius: 6px;
    padding: 5px 8px;
}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class PdfSafetyError(Exception):
    pass


class PdfPageLabel(QLabel):
    selection_finished = Signal(QRect)
    sticky_note_requested = Signal(QPoint)

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.drag_start = None
        self.drag_current = None
        self.annotation_mode = None  # None or "sticky_note"
        self.setMouseTracking(True)

    def clear_drag_selection(self):
        self.drag_start = None
        self.drag_current = None
        self.update()

    def set_annotation_mode(self, mode):
        self.annotation_mode = mode
        if mode == "sticky_note":
            self.setCursor(Qt.CrossCursor)
            self.setText("Click on the PDF to place a sticky note")
        else:
            self.setCursor(Qt.ArrowCursor)

    def clear_annotation_mode(self):
        self.set_annotation_mode(None)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.pixmap() is not None:
            if self.annotation_mode == "sticky_note":
                pos = event.position().toPoint()
                self.clear_annotation_mode()
                self.sticky_note_requested.emit(pos)
                event.accept()
                return
            self.drag_start = event.position().toPoint()
            self.drag_current = self.drag_start
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_start is not None:
            self.drag_current = event.position().toPoint()
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drag_start is not None:
            self.drag_current = event.position().toPoint()
            rect = QRect(self.drag_start, self.drag_current).normalized()
            self.clear_drag_selection()
            self.selection_finished.emit(rect)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.drag_start is None or self.drag_current is None:
            return
        painter = QPainter(self)
        painter.setPen(QColor(37, 99, 235))
        painter.setBrush(QColor(37, 99, 235, 45))
        painter.drawRect(QRect(self.drag_start, self.drag_current).normalized())
        painter.end()


# ---------------------------------------------------------------------------
# Zoom icon factory
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Toolbar design system — theme-aware vector icons
# ---------------------------------------------------------------------------

TOOLBAR_ICON_SIZE = 18
TOOLBAR_BUTTON_SIZE = 30
TOOLBAR_SMALL_BUTTON_SIZE = 26


def _toolbar_icon_colors(dark_mode: bool) -> dict[str, str]:
    """Fluent-style icon palette for the active theme."""
    if dark_mode:
        return {
            "stroke": "#e9e9ee",
            "muted": "#9b9ca4",
            "accent": "#ff4d7a",
            "highlight": "#f5c518",
            "disabled": "#4c4d55",
            "surface": "#232428",
        }
    return {
        "stroke": "#232329",
        "muted": "#6f7076",
        "accent": "#ff255f",
        "highlight": "#e8a800",
        "disabled": "#c3c4c9",
        "surface": "#fbfbfc",
    }


def _icon_pen(color: str, width: float = 1.6) -> QPen:
    pen = QPen(QColor(color), width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _draw_open_icon(p: QPainter, s: float, c: dict[str, str]):
    p.setPen(_icon_pen(c["stroke"], 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(2.8, 5.4)
    path.lineTo(7.1, 5.4)
    path.lineTo(8.6, 7.3)
    path.lineTo(15.2, 7.3)
    path.lineTo(15.2, 14.3)
    path.lineTo(2.8, 14.3)
    path.closeSubpath()
    p.drawPath(path)


def _draw_save_icon(p: QPainter, s: float, c: dict[str, str]):
    p.setPen(_icon_pen(c["stroke"], 1.6))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QPointF(9, 3.2), QPointF(9, 11.1))
    arrow = QPainterPath()
    arrow.moveTo(5.9, 8.2)
    arrow.lineTo(9, 11.3)
    arrow.lineTo(12.1, 8.2)
    p.drawPath(arrow)
    tray = QPainterPath()
    tray.moveTo(3.5, 12.2)
    tray.lineTo(3.5, 15.0)
    tray.lineTo(14.5, 15.0)
    tray.lineTo(14.5, 12.2)
    p.drawPath(tray)


def _chevron(p: QPainter, c: dict[str, str], points: tuple):
    p.setPen(_icon_pen(c["stroke"], 1.8))
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(*points[0])
    path.lineTo(*points[1])
    path.lineTo(*points[2])
    p.drawPath(path)


def _draw_chevron_left(p: QPainter, s: float, c: dict[str, str]):
    _chevron(p, c, ((11.6, 4.6), (6.4, 9.0), (11.6, 13.4)))


def _draw_chevron_right(p: QPainter, s: float, c: dict[str, str]):
    _chevron(p, c, ((6.4, 4.6), (11.6, 9.0), (6.4, 13.4)))


def _draw_chevron_up(p: QPainter, s: float, c: dict[str, str]):
    _chevron(p, c, ((4.8, 11.4), (9.0, 6.6), (13.2, 11.4)))


def _draw_chevron_down(p: QPainter, s: float, c: dict[str, str]):
    _chevron(p, c, ((4.8, 6.6), (9.0, 11.4), (13.2, 6.6)))


def _draw_plus_icon(p: QPainter, s: float, c: dict[str, str]):
    p.setPen(_icon_pen(c["stroke"], 1.8))
    p.drawLine(QPointF(4.4, 9), QPointF(13.6, 9))
    p.drawLine(QPointF(9, 4.4), QPointF(9, 13.6))


def _draw_minus_icon(p: QPainter, s: float, c: dict[str, str]):
    p.setPen(_icon_pen(c["stroke"], 1.8))
    p.drawLine(QPointF(4.4, 9), QPointF(13.6, 9))


def _draw_fit_icon(p: QPainter, s: float, c: dict[str, str]):
    p.setPen(_icon_pen(c["stroke"], 1.6))
    # Four corner brackets.
    p.drawLine(QPointF(3.2, 6.6), QPointF(3.2, 3.2))
    p.drawLine(QPointF(3.2, 3.2), QPointF(6.6, 3.2))
    p.drawLine(QPointF(11.4, 3.2), QPointF(14.8, 3.2))
    p.drawLine(QPointF(14.8, 3.2), QPointF(14.8, 6.6))
    p.drawLine(QPointF(3.2, 11.4), QPointF(3.2, 14.8))
    p.drawLine(QPointF(3.2, 14.8), QPointF(6.6, 14.8))
    p.drawLine(QPointF(11.4, 14.8), QPointF(14.8, 14.8))
    p.drawLine(QPointF(14.8, 14.8), QPointF(14.8, 11.4))


def _draw_copy_icon(p: QPainter, s: float, c: dict[str, str]):
    p.setPen(_icon_pen(c["muted"], 1.4))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(4.2, 3.2, 7.8, 9.8), 1.8, 1.8)
    # Front sheet occludes the back one.
    p.setBrush(QColor(c["surface"]))
    p.drawRoundedRect(QRectF(7.2, 6.2, 7.0, 9.0), 1.8, 1.8)


def _draw_highlight_icon(p: QPainter, s: float, c: dict[str, str]):
    pen = QPen(QColor(c["highlight"]), 4.4)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(QPointF(4.8, 13.2), QPointF(12.2, 4.9))
    p.setPen(_icon_pen(c["muted"], 1.5))
    p.drawLine(QPointF(12.9, 3.6), QPointF(14.6, 5.3))


def _draw_underline_icon(p: QPainter, s: float, c: dict[str, str]):
    p.setPen(_icon_pen(c["stroke"], 1.7))
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(5.5, 3.4)
    path.lineTo(5.5, 9.1)
    path.cubicTo(5.5, 12.6, 12.5, 12.6, 12.5, 9.1)
    path.lineTo(12.5, 3.4)
    p.drawPath(path)
    p.setPen(_icon_pen(c["accent"], 1.8))
    p.drawLine(QPointF(4.0, 15.1), QPointF(14.0, 15.1))


def _draw_strike_icon(p: QPainter, s: float, c: dict[str, str]):
    p.setPen(_icon_pen(c["stroke"], 1.55))
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(12.2, 5.5)
    path.cubicTo(12.2, 3.4, 6.2, 3.2, 6.2, 6.4)
    path.cubicTo(6.2, 8.8, 12.4, 8.3, 12.4, 11.8)
    path.cubicTo(12.4, 14.8, 6.0, 14.8, 6.0, 12.5)
    p.drawPath(path)
    p.setPen(_icon_pen(c["accent"], 1.8))
    p.drawLine(QPointF(3.6, 9.1), QPointF(14.4, 9.1))


def _draw_sticky_icon(p: QPainter, s: float, c: dict[str, str]):
    p.setPen(_icon_pen(c["muted"], 1.45))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(4.2, 3.2, 9.6, 11.6), 1.7, 1.7)
    fold = QPainterPath()
    fold.moveTo(10.8, 3.2)
    fold.lineTo(10.8, 6.8)
    fold.lineTo(13.8, 6.8)
    p.drawPath(fold)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(c["accent"]))
    p.drawEllipse(QPointF(6.9, 6.5), 1.05, 1.05)
    p.setPen(_icon_pen(c["muted"], 1.2))
    p.drawLine(QPointF(6.9, 9.5), QPointF(11.1, 9.5))
    p.drawLine(QPointF(6.9, 11.5), QPointF(10.1, 11.5))


def _draw_search_icon(p: QPainter, s: float, c: dict[str, str]):
    p.setPen(_icon_pen(c["muted"], 1.6))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(7.8, 7.8), 4.5, 4.5)
    p.drawLine(QPointF(11.2, 11.2), QPointF(14.8, 14.8))


def _draw_close_icon(p: QPainter, s: float, c: dict[str, str]):
    p.setPen(_icon_pen(c["muted"], 1.6))
    p.drawLine(QPointF(5.2, 5.2), QPointF(12.8, 12.8))
    p.drawLine(QPointF(12.8, 5.2), QPointF(5.2, 12.8))


def _draw_fill_icon(p: QPainter, s: float, c: dict[str, str]):
    p.setPen(_icon_pen(c["stroke"], 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(3.0, 3.5, 8.2, 11.0), 1.5, 1.5)
    p.setPen(_icon_pen(c["muted"], 1.2))
    p.drawLine(QPointF(4.8, 6.2), QPointF(9.2, 6.2))
    p.drawLine(QPointF(4.8, 8.6), QPointF(8.4, 8.6))
    p.setPen(_icon_pen(c["accent"], 1.7))
    p.drawLine(QPointF(10.0, 7.2), QPointF(14.4, 11.6))
    p.drawLine(QPointF(14.4, 11.6), QPointF(14.4, 14.0))
    p.drawLine(QPointF(14.4, 14.0), QPointF(12.0, 14.0))


def _draw_text_icon(p: QPainter, s: float, c: dict[str, str]):
    p.setPen(_icon_pen(c["stroke"], 1.8))
    p.drawLine(QPointF(4.0, 4.2), QPointF(14.0, 4.2))
    p.drawLine(QPointF(9.0, 4.2), QPointF(9.0, 14.6))
    p.drawLine(QPointF(6.2, 14.6), QPointF(11.8, 14.6))


def _draw_signature_icon(p: QPainter, s: float, c: dict[str, str]):
    p.setPen(_icon_pen(c["stroke"], 1.6))
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(3.4, 13.8)
    path.cubicTo(6.2, 10.4, 8.4, 4.4, 11.6, 4.4)
    path.cubicTo(14.4, 4.4, 12.6, 9.6, 8.6, 12.4)
    p.drawPath(path)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(c["accent"]))
    nib = QPolygonF([QPointF(13.0, 3.2), QPointF(15.2, 5.4), QPointF(13.2, 7.4), QPointF(11.0, 5.2)])
    p.drawPolygon(nib)


def _draw_image_icon(p: QPainter, s: float, c: dict[str, str]):
    p.setPen(_icon_pen(c["stroke"], 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(2.8, 3.8, 12.4, 10.4), 1.5, 1.5)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(c["accent"]))
    p.drawEllipse(QPointF(6.3, 7.0), 1.2, 1.2)
    p.setPen(_icon_pen(c["muted"], 1.35))
    path = QPainterPath()
    path.moveTo(3.4, 13.0)
    path.lineTo(7.0, 9.4)
    path.lineTo(9.4, 11.8)
    path.lineTo(11.3, 9.9)
    path.lineTo(14.4, 13.0)
    p.drawPath(path)


_TOOLBAR_ICONS = {
    "open": _draw_open_icon,
    "save": _draw_save_icon,
    "chevron_left": _draw_chevron_left,
    "chevron_right": _draw_chevron_right,
    "chevron_up": _draw_chevron_up,
    "chevron_down": _draw_chevron_down,
    "plus": _draw_plus_icon,
    "minus": _draw_minus_icon,
    "fit": _draw_fit_icon,
    "copy": _draw_copy_icon,
    "highlight": _draw_highlight_icon,
    "underline": _draw_underline_icon,
    "strike": _draw_strike_icon,
    "sticky": _draw_sticky_icon,
    "search": _draw_search_icon,
    "close": _draw_close_icon,
    "fill": _draw_fill_icon,
    "text": _draw_text_icon,
    "signature": _draw_signature_icon,
    "image": _draw_image_icon,
}


def _make_toolbar_icon(draw_fn, dark_mode: bool, size: int = TOOLBAR_ICON_SIZE) -> QIcon:
    """Render a crisp icon (plus a muted disabled variant) for the theme."""
    colors = _toolbar_icon_colors(dark_mode)
    scale = 2.0
    icon = QIcon()
    for mode, palette in (
        (QIcon.Mode.Normal, colors),
        (
            QIcon.Mode.Disabled,
            {
                **colors,
                "stroke": colors["disabled"],
                "muted": colors["disabled"],
                "accent": colors["disabled"],
                "highlight": colors["disabled"],
            },
        ),
    ):
        pixmap = QPixmap(int(size * scale), int(size * scale))
        pixmap.fill(Qt.GlobalColor.transparent)
        pixmap.setDevicePixelRatio(scale)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # QPainter already works in logical pixels for a DPR-aware pixmap.
        draw_fn(painter, size, palette)
        painter.end()
        icon.addPixmap(pixmap, mode)
    return icon


def _make_empty_state_icon(dark_mode: bool, size: int = 60) -> QPixmap:
    """A quiet document glyph for the empty reading surface."""
    colors = _toolbar_icon_colors(dark_mode)
    scale = 2.0
    pixmap = QPixmap(int(size * scale), int(size * scale))
    pixmap.fill(Qt.GlobalColor.transparent)
    pixmap.setDevicePixelRatio(scale)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(colors["muted"]), 1.5)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    sheet = QPainterPath()
    sheet.moveTo(14, 4)
    sheet.lineTo(38, 4)
    sheet.lineTo(48, 14)
    sheet.lineTo(48, 56)
    sheet.lineTo(14, 56)
    sheet.closeSubpath()
    painter.drawPath(sheet)
    painter.drawLine(QPointF(38, 4), QPointF(38, 14))
    painter.drawLine(QPointF(38, 14), QPointF(48, 14))
    line_color = QColor(colors["muted"])
    line_color.setAlpha(150)
    painter.setPen(QPen(line_color, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for y in (26, 34, 42):
        painter.drawLine(QPointF(21, y), QPointF(41, y))
    painter.end()
    return pixmap


# ---------------------------------------------------------------------------
# AcroForm overlays — Phase 2 PDF Form Intelligence (v1.3.0 / 1.3.1 / 1.3.2)
# ---------------------------------------------------------------------------
#
# The FormController owns one tab's AcroForm state: native Qt overlay widgets
# positioned over each fillable field rect (Approach A), a dirty flag, advisory
# validation, autosave/recovery via FormStateStore, and the data feeding the
# Form Navigator dock. All field logic lives in pdfreader_lib.form_fields.


class _FormLineEdit(QLineEdit):
    """Single-line text field overlay."""

    def __init__(self, controller, field):
        super().__init__()
        self._controller = controller
        self._field = field
        if field.password:
            self.setEchoMode(QLineEdit.Password)
        if field.max_length:
            self.setMaxLength(field.max_length)
        self.textEdited.connect(lambda _t: controller.on_edited(field))
        self.editingFinished.connect(lambda: controller.on_commit(field, self.text()))

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._controller.on_focus(self._field)


class _FormMultilineEdit(QTextEdit):
    """Multiline text field overlay."""

    def __init__(self, controller, field):
        super().__init__()
        self._controller = controller
        self._field = field
        self.setFrameShape(QFrame.NoFrame)
        self.setTabChangesFocus(True)  # Tab moves between fields, not tabs
        if field.max_length:
            self.textChanged.connect(lambda: self._enforce_max_length())

    def _enforce_max_length(self):
        text = self.toPlainText()
        limit = self._field.max_length
        if limit and len(text) > limit:
            cursor = self.textCursor()
            pos = cursor.position()
            self.blockSignals(True)
            self.setPlainText(text[:limit])
            cursor.setPosition(min(pos, limit))
            self.setTextCursor(cursor)
            self.blockSignals(False)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._controller.on_focus(self._field)


class _FormCheck(QCheckBox):
    """Checkbox overlay."""

    def __init__(self, controller, field):
        super().__init__()
        self._controller = controller
        self._field = field
        self.toggled.connect(lambda checked: controller.on_toggled(field, checked))

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._controller.on_focus(self._field)


class _FormCombo(QComboBox):
    """Combo/listbox overlay."""

    def __init__(self, controller, field):
        super().__init__()
        self._controller = controller
        self._field = field
        for choice in field.choices:
            self.addItem(choice)
        self.setEditable(bool(field.editable_choice))
        self.currentTextChanged.connect(lambda _t: controller.on_edited(field))

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._controller.on_focus(self._field)


# Overlay colors — brand accent #ff255F for focus, blue accent for fillables.
_FORM_FILLABLE_BORDER = (37, 99, 235, 150)
_FORM_FILLABLE_FILL = (37, 99, 235, 26)
_FORM_READONLY_BORDER = (150, 150, 150, 130)
_FORM_REQUIRED_EMPTY_BORDER = (245, 158, 11, 200)
_FORM_FOCUS_BORDER = (255, 37, 95)


class _FormController(QObject):
    """Owns one tab's AcroForm overlays, dirty tracking and autosave."""

    def __init__(self, window, tab_id: int):
        super().__init__(window)
        self.window = window
        self.tab_id = tab_id
        self.fields: list = []
        self._by_name: dict = {}
        self._widgets: dict = {}          # QWidget -> FormField
        self._field_widgets: dict = {}    # field.name -> list[QWidget]
        self._radio_buttons: dict = {}    # QRadioButton -> (field, caption)
        self._radio_groups: dict = {}     # field.name -> QButtonGroup
        self._button_group = None
        self.dirty = False
        self.readonly = False
        self._dirty_names: set = set()
        self._seeding = 0
        self._current_index = -1
        self._user_overrides: dict = {}   # "page:name" -> detected_type
        self._state_store = None
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(1200)
        self._autosave_timer.timeout.connect(self._autosave_now)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def load(self, doc, path) -> int:
        """Build the field index for a document. Returns the field count."""
        self.fields = _ff.build_field_index(doc)
        _ff.annotate_field_types(self.fields, doc)
        self._by_name = {f.name: f for f in self.fields}
        self.dirty = False
        self._dirty_names = set()
        self._current_index = -1
        self._user_overrides = {}
        self._state_store = getattr(self.window, "_form_store", None)
        self._apply_stored_state(path)
        return len(self.fields)

    @property
    def editable_fields(self):
        return [f for f in self.fields if f.is_editable()]

    def detach_all(self):
        """Remove every overlay widget from the UI."""
        for widget in list(self._widgets.keys()):
            widget.setParent(None)
            widget.deleteLater()
        self._widgets = {}
        self._field_widgets = {}
        self._radio_buttons = {}
        self._radio_groups = {}
        self._button_group = None

    def detach_page(self, label):
        """Remove overlay widgets attached to a single page label."""
        self._clear_overlays(label)

    # ------------------------------------------------------------------
    # Overlay rendering
    # ------------------------------------------------------------------

    def attach_page(self, label, page_index, zoom, page_rect):
        """Create/reposition overlay widgets for one rendered page label."""
        self._clear_overlays(label)
        if not self.fields:
            return
        page_fields = [f for f in self.fields if f.page_index == page_index]
        if not page_fields:
            return
        style = self._overlay_style(bool(getattr(self.window, "_dark_mode", False)))
        self._seeding += 1
        try:
            for field in page_fields:
                if not field.is_editable():
                    continue
                if field.field_type == _ff.FieldType.RADIO:
                    self._attach_radio(label, field, zoom, page_rect, style)
                    continue
                widget = self._make_widget(field)
                widget.setParent(label)
                widget.setStyleSheet(style)
                widget.setGeometry(
                    round((field.rect[0] - page_rect.x0) * zoom),
                    round((field.rect[1] - page_rect.y0) * zoom),
                    max(8, round((field.rect[2] - field.rect[0]) * zoom)),
                    max(8, round((field.rect[3] - field.rect[1]) * zoom)),
                )
                widget.show()
                self._register_widget(widget, field)
                self._seed_widget(widget, field)
                # v1.3.1 — visible date-picker affordance on detected date fields.
                if (
                    field.detected_type == _ff.TYPE_DATE
                    and field.field_type in (_ff.FieldType.TEXT, _ff.FieldType.MULTILINE)
                ):
                    self._attach_date_button(label, field, zoom, page_rect)
        finally:
            self._seeding -= 1
        self._set_tab_order(page_fields)

    def _make_widget(self, field):
        ftype = field.field_type
        if ftype == _ff.FieldType.MULTILINE:
            widget = _FormMultilineEdit(self, field)
            widget.textChanged.connect(lambda: self.on_edited(field))
        elif ftype == _ff.FieldType.CHECKBOX:
            widget = _FormCheck(self, field)
        elif ftype in (_ff.FieldType.COMBO, _ff.FieldType.LISTBOX):
            widget = _FormCombo(self, field)
        else:
            widget = _FormLineEdit(self, field)
        widget.setAccessibleName(field.display_name())
        widget.setToolTip(self._tooltip_for(field))
        widget.setContextMenuPolicy(Qt.CustomContextMenu)
        widget.customContextMenuRequested.connect(
            lambda pos, w=widget, f=field: self._on_context_menu(w, f, pos)
        )
        return widget

    def _attach_radio(self, label, field, zoom, page_rect, style):
        group = QButtonGroup(label)
        group.setExclusive(True)
        for caption, opt_rect in zip(field.choices, field.option_rects):
            rb = QRadioButton(label)
            rb.setText("")
            rb.setToolTip(caption)
            rb.setAccessibleName(f"{field.display_name()} — {caption}")
            rb.setGeometry(
                round((opt_rect[0] - page_rect.x0) * zoom),
                round((opt_rect[1] - page_rect.y0) * zoom),
                max(8, round((opt_rect[2] - opt_rect[0]) * zoom)),
                max(8, round((opt_rect[3] - opt_rect[1]) * zoom)),
            )
            rb.setStyleSheet(style)
            rb.setEnabled(not self.readonly)
            if field.value == caption:
                rb.setChecked(True)
            group.addButton(rb)
            rb.clicked.connect(lambda _c, f=field, cap=caption: self.on_radio(f, cap))
            self._widgets[rb] = field
            self._field_widgets.setdefault(field.name, []).append(rb)
            self._radio_buttons[rb] = (field, caption)
            rb.show()
        self._button_group = group
        self._radio_groups[field.name] = group

    def _attach_date_button(self, label, field, zoom, page_rect):
        """Small calendar button to the right of a detected date field."""
        button = QToolButton(label)
        button.setText("📅")
        button.setToolTip("Pick a date")
        button.setAccessibleName(f"Pick a date for {field.display_name()}")
        button.setGeometry(
            round((field.rect[2] - page_rect.x0) * zoom),
            round((field.rect[1] - page_rect.y0) * zoom),
            max(16, round((field.rect[3] - field.rect[1]) * zoom)),
            max(16, round((field.rect[3] - field.rect[1]) * zoom)),
        )
        button.clicked.connect(lambda _c, f=field: self._open_date_picker(f))
        button.show()
        # Keep it above the field widget so clicks reach it.
        button.raise_()

    def _open_date_picker(self, field):
        dialog = QDialog(self.window)
        dialog.setWindowTitle(f"Pick a date — {field.display_name()}")
        layout = QVBoxLayout(dialog)
        calendar = QCalendarWidget()
        layout.addWidget(calendar)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.Accepted:
            iso = calendar.selectedDate().toString("yyyy-MM-dd")
            self._set_widget_value(field, iso)
            self._mark_dirty(field)
            self.on_commit(field, iso)

    def _register_widget(self, widget, field):
        self._widgets[widget] = field
        self._field_widgets.setdefault(field.name, []).append(widget)
        if self.readonly:
            widget.setEnabled(False)

    def _seed_widget(self, widget, field):
        value = field.value
        ftype = field.field_type
        if ftype in (_ff.FieldType.TEXT, _ff.FieldType.MULTILINE):
            if isinstance(widget, QTextEdit):
                widget.setPlainText(str(value))
            else:
                widget.setText(str(value))
        elif ftype == _ff.FieldType.CHECKBOX:
            widget.setChecked(bool(value))
        elif ftype in (_ff.FieldType.COMBO, _ff.FieldType.LISTBOX):
            index = widget.findText(str(value))
            if index >= 0:
                widget.setCurrentIndex(index)

    def _clear_overlays(self, label):
        for widget in list(self._widgets.keys()):
            if widget.parent() is label:
                widget.setParent(None)
                widget.deleteLater()
                self._widgets.pop(widget, None)
        self._field_widgets = {}
        for widget, field in self._widgets.items():
            self._field_widgets.setdefault(field.name, []).append(widget)
        self._radio_buttons = {
            rb: pair for rb, pair in self._radio_buttons.items() if rb.parent() is not label
        }
        for name, group in list(self._radio_groups.items()):
            if group.parent() is label:
                del self._radio_groups[name]
        if self._button_group is not None and self._button_group.parent() is label:
            self._button_group = None

    def _set_tab_order(self, page_fields):
        widgets = []
        for field in page_fields:
            widgets.extend(self._field_widgets.get(field.name, []))
        for a, b in zip(widgets, widgets[1:]):
            QWidget.setTabOrder(a, b)

    @staticmethod
    def _overlay_style(dark: bool) -> str:
        if dark:
            return (
                "QLineEdit, QTextEdit, QComboBox { background: rgba(30,34,48,150); color: #e8e8f0;"
                " border: 1px solid rgba(120,150,255,150); border-radius: 2px; }"
                "QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 1px solid #ff255f; }"
            )
        return (
            "QLineEdit, QTextEdit, QComboBox { background: rgba(255,255,255,175); color: #1a1a1a;"
            " border: 1px solid rgba(37,99,235,140); border-radius: 2px; }"
            "QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 1px solid #ff255f; }"
        )

    # ------------------------------------------------------------------
    # Value handling
    # ------------------------------------------------------------------

    def current_value(self, field):
        widgets = self._field_widgets.get(field.name)
        if not widgets:
            return field.value
        widget = widgets[0]
        ftype = field.field_type
        if ftype == _ff.FieldType.CHECKBOX:
            return widget.isChecked()
        if ftype == _ff.FieldType.RADIO:
            for rb, (fld, caption) in self._radio_buttons.items():
                if fld.name == field.name and rb.isChecked():
                    return caption
            return ""
        if ftype in (_ff.FieldType.COMBO, _ff.FieldType.LISTBOX):
            return widget.currentText()
        if isinstance(widget, QTextEdit):
            return widget.toPlainText()
        return widget.text()

    def _set_widget_value(self, field, value):
        self._seeding += 1
        try:
            widgets = self._field_widgets.get(field.name)
            if not widgets:
                return
            widget = widgets[0]
            ftype = field.field_type
            if ftype == _ff.FieldType.CHECKBOX:
                widget.setChecked(bool(value))
            elif ftype == _ff.FieldType.RADIO:
                group = self._radio_groups.get(field.name)
                if group is not None:
                    group.setExclusive(False)  # allow clearing the whole group
                try:
                    for rb, (fld, caption) in self._radio_buttons.items():
                        if fld.name == field.name:
                            rb.setChecked(caption == value)
                finally:
                    if group is not None:
                        group.setExclusive(True)
            elif ftype in (_ff.FieldType.COMBO, _ff.FieldType.LISTBOX):
                index = widget.findText(str(value))
                widget.setCurrentIndex(index if index >= 0 else -1)
            elif isinstance(widget, QTextEdit):
                widget.setPlainText(str(value))
            else:
                widget.setText(str(value))
        finally:
            self._seeding -= 1

    def clear_field(self, field):
        if not field.is_editable():
            return
        empty = False if field.field_type == _ff.FieldType.CHECKBOX else ""
        self._set_widget_value(field, empty)
        self._mark_dirty(field)

    def clear_form(self):
        for field in self.editable_fields:
            self.clear_field(field)

    # ------------------------------------------------------------------
    # Editing / focus signals
    # ------------------------------------------------------------------

    def on_edited(self, field):
        if self._seeding:
            return
        self._mark_dirty(field)

    def on_toggled(self, field, _checked):
        if self._seeding:
            return
        self._mark_dirty(field)

    def on_radio(self, field, _caption):
        if self._seeding:
            return
        self._mark_dirty(field)

    def on_focus(self, field):
        self._current_index = self._index_of(field)
        self.window._on_form_focus(field)

    def on_commit(self, field, text):
        if field.detected_type and text:
            ok, message = _ff.FormValidator.validate(field, text)
            field.validation_message = "" if ok else message
            self.window._on_form_validation(field, field.validation_message)
        self.window._update_navigator_item(field)

    def _mark_dirty(self, field):
        self.dirty = True
        self._dirty_names.add(field.name)
        self.window._on_form_dirty(self.tab_id)
        self._autosave_timer.start()

    def _index_of(self, field):
        for i, candidate in enumerate(self.editable_fields):
            if candidate.name == field.name:
                return i
        return -1

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def focus_next(self, forward: bool = True):
        fields = self.editable_fields
        if not fields:
            return
        count = len(fields)
        index = self._current_index
        index = -1 if index < 0 else index
        self._current_index = (index + (1 if forward else -1)) % count
        self.focus_field(fields[self._current_index])

    def focus_field(self, field):
        self.window._jump_to_page(field.page_index)
        widgets = self._field_widgets.get(field.name)
        if widgets:
            widget = widgets[0]
            widget.show()
            widget.setFocus(Qt.OtherFocusReason)
        self.window._ensure_field_visible(field)

    # ------------------------------------------------------------------
    # Context menu (type override, clear)
    # ------------------------------------------------------------------

    def _on_context_menu(self, widget, field, pos):
        menu = QMenu(self.window)
        if field.detected_type:
            marker = " (inferred)" if field.is_inferred else ""
            menu.addSection(f"Detected: {field.detected_type}{marker}")
        type_menu = menu.addMenu("Set field type")
        for label, ftype in [
            ("Text", None),
            ("Date", _ff.TYPE_DATE),
            ("Phone", _ff.TYPE_PHONE),
            ("ZIP / Postal code", _ff.TYPE_ZIP),
            ("Email", _ff.TYPE_EMAIL),
            ("Currency", _ff.TYPE_CURRENCY),
            ("Number", _ff.TYPE_NUMERIC),
        ]:
            action = type_menu.addAction(label)
            action.triggered.connect(lambda _c, t=ftype, f=field: self._apply_override(f, t))
        if field.detected_type == _ff.TYPE_DATE and field.is_editable():
            date_action = menu.addAction("Pick a date…")
            date_action.triggered.connect(lambda _c, f=field: self._open_date_picker(f))
        menu.addSeparator()
        clear_action = menu.addAction("Clear field")
        clear_action.triggered.connect(lambda: self.clear_field(field))
        menu.exec(widget.mapToGlobal(pos))

    def _apply_override(self, field, ftype):
        field.detected_type = ftype
        field.is_inferred = False
        field.validation_message = ""
        key = f"{field.page_index}:{field.name}"
        if ftype:
            self._user_overrides[key] = ftype
        else:
            self._user_overrides.pop(key, None)
        self.window._on_form_validation(field, "Field type overridden." if ftype else "Field type cleared.")
        self.window._update_navigator_item(field)
        widgets = self._field_widgets.get(field.name)
        if widgets:
            widgets[0].setToolTip(self._tooltip_for(field))
            self.on_commit(field, str(self.current_value(field)))

    # ------------------------------------------------------------------
    # Tooltips / status helpers
    # ------------------------------------------------------------------

    def _tooltip_for(self, field) -> str:
        parts = []
        if field.label and field.label != field.name:
            parts.append(field.label)
        parts.append(field.name)
        if field.required:
            parts.append("Required")
        if field.detected_type:
            parts.append(f"Type: {field.detected_type}{' (inferred)' if field.is_inferred else ''}")
        if field.validation_message:
            parts.append(field.validation_message)
        return " • ".join(parts)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, doc, path) -> bool:
        """Write dirty field values into the PDF and persist incrementally."""
        if not self.dirty:
            return True
        for name in self._dirty_names:
            field = self._by_name.get(name)
            if field is None or not field.is_editable():
                continue
            try:
                _ff.set_field_value(doc, field, self.current_value(field))
            except Exception:  # nosec B112
                continue
        self._persist(doc, path)
        self.dirty = False
        self._dirty_names = set()
        if self._state_store is not None:
            self._state_store.clear(path)
        return True

    def save_as(self, doc, new_path):
        doc.save(str(new_path), garbage=1, deflate=True)
        self.dirty = False
        self._dirty_names = set()
        if self._state_store is not None:
            self._state_store.clear(new_path)

    @staticmethod
    def _persist(doc, path):
        try:
            doc.save(str(path), incremental=True, encryption=0)
        except Exception:
            doc.save(str(path), garbage=1, deflate=True)

    def _autosave_now(self):
        if not self.dirty or self._state_store is None:
            return
        path = getattr(self.window, "current_path", None)
        if not path:
            return
        values = {}
        for field in self.fields:
            if field.is_editable():
                values[f"{field.page_index}:{field.name}"] = self.current_value(field)
        self._state_store.save(path, values, dict(self._user_overrides))

    def discard_autosave(self, path):
        if self._state_store is not None:
            self._state_store.clear(path)

    def _apply_stored_state(self, path):
        if self._state_store is None or not self._state_store.has_state(path):
            return
        data = self._state_store.load(path)
        values = data.get("values", {})
        overrides = data.get("overrides", {})
        for field in self.fields:
            key = f"{field.page_index}:{field.name}"
            if overrides.get(key):
                field.detected_type = overrides[key]
                field.is_inferred = False
                self._user_overrides[key] = overrides[key]
            if key in values:
                field.value = values[key]
            elif field.name in values:
                field.value = values[field.name]
        # Restored state is unsaved form work → mark the tab dirty.
        if values:
            self.dirty = True

    # ------------------------------------------------------------------
    # Navigator / summary data
    # ------------------------------------------------------------------

    def field_status(self, field) -> str:
        if not field.is_editable():
            return "readonly"
        value = self.current_value(field)
        empty = value is None or value == "" or (isinstance(value, bool) and not value)
        if field.validation_message:
            return "invalid"
        if field.required and empty:
            return "required"
        if not empty:
            return "filled"
        return "empty"

    def _summary_value(self, field) -> str:
        value = self.current_value(field)
        if isinstance(value, bool):
            return "✓" if value else ""
        text = str(value or "")
        return text if len(text) <= 40 else text[:37] + "…"

    def navigator_rows(self):
        rows = []
        for field in self.fields:
            rows.append(
                {
                    "page": field.page_index,
                    "name": field.display_name(),
                    "field_type": field.field_type,
                    "status": self.field_status(field),
                    "value": self._summary_value(field),
                    "validation": field.validation_message,
                }
            )
        return rows

    def completion_summary(self):
        counts = {"filled": 0, "empty": 0, "required": 0, "invalid": 0}
        for field in self.fields:
            status = self.field_status(field)
            if status == "filled":
                counts["filled"] += 1
            elif status == "required":
                counts["required"] += 1
            elif status == "invalid":
                counts["invalid"] += 1
            elif status == "empty":
                counts["empty"] += 1
        return counts


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class PdfReaderWindow(QMainWindow):
    APP_NAME = "OpenReader"
    MAX_PDF_SIZE_BYTES = 500 * 1024 * 1024
    MAX_PAGE_DIMENSION_POINTS = 14400
    MAX_RENDER_PIXELS = 80_000_000
    MAX_SEARCH_MATCHES = 20_000
    MAX_SPLIT_PAGES = 1000
    MAX_OCR_CACHE_PAGES = 3
    MIN_ZOOM = 0.25
    MAX_ZOOM = 5.0
    ZOOM_STEP = 0.15

    # Continuous scrolling (virtualized): every page keeps a sized placeholder
    # so the scroll range always spans the whole document, while pixmaps exist
    # only for the viewport plus a small overscan.
    CONTINUOUS_OVERSCAN = 2      # pages rendered on each side of the viewport
    CONTINUOUS_CACHE = 4         # rendered pages kept on each side before release
    CONTINUOUS_PAGE_GAP = 12
    CONTINUOUS_PAGE_MARGIN = 16
    CONTINUOUS_RENDER_DELAY_MS = 40

    # Dark mode constants
    THEME_AUTO = 0
    THEME_LIGHT = 1
    THEME_DARK = 2

    # Annotation colors
    ANNOT_HIGHLIGHT = (1.0, 0.882, 0.235)      # yellow
    ANNOT_UNDERLINE = (0.075, 0.533, 0.867)    # blue
    ANNOT_STRIKEOUT = (0.953, 0.318, 0.302)    # red
    ABOUT_SHORTCUTS = (
        ("Open PDF", "Ctrl+O"),
        ("Save", "Ctrl+S"),
        ("Find", "Ctrl+F"),
        ("Copy", "Ctrl+C"),
        ("Prev / Next Page", "Page Up / Page Down"),
        ("Zoom In / Out", "Ctrl+= / Ctrl+-"),
        ("Fit Width", "Ctrl+0"),
        ("Close Tab", "Ctrl+W"),
        ("New Tab (blank)", "Ctrl+T"),
    )
    REGISTERED_SHORTCUTS = (
        ("open_pdf", "Ctrl+O"),
        ("save", "Ctrl+S"),
        ("find", "Ctrl+F"),
        ("copy", "Ctrl+C"),
        ("previous_page", "Page Up"),
        ("next_page", "Page Down"),
        ("zoom_in", "Ctrl+="),
        ("zoom_out", "Ctrl+-"),
        ("fit_width", "Ctrl+0"),
        ("close_tab", "Ctrl+W"),
        ("new_tab", "Ctrl+T"),
        ("next_field", "Ctrl+Down"),
        ("previous_field", "Ctrl+Up"),
    )

    def __init__(self, ipc_server: QLocalServer | None = None):
        _perf_start_t = _perf_start()
        super().__init__()
        self.setWindowTitle(self.APP_NAME)
        self.resize(1240, 840)
        self.setMinimumSize(900, 560)

        # ---- IPC server for single-instance tab routing ----
        self._ipc_server = ipc_server
        if ipc_server is not None:
            ipc_server.newConnection.connect(self._on_ipc_connection)

        # ---- Continuous scroll (virtualized) ----
        self._continuous_mode = True  # default to continuous
        self._continuous_pages: list[QLabel] = []
        self._continuous_rendered: set[int] = set()
        self._continuous_container = None
        self._continuous_layout = None
        self._continuous_layout_zoom: float | None = None
        self._continuous_layout_document = None
        self._continuous_syncing_scroll = False
        self._pending_scroll_page: int | None = None
        self._continuous_render_timer = QTimer(self)
        self._continuous_render_timer.setSingleShot(True)
        self._continuous_render_timer.setInterval(self.CONTINUOUS_RENDER_DELAY_MS)
        self._continuous_render_timer.timeout.connect(self._render_visible_continuous)

        # App icon
        self._set_app_icon()

        # Enable drag-and-drop
        self.setAcceptDrops(True)

        self.settings = QSettings("Sparsh Sam", "OpenReader")

        # ---- Render debounce timer ----
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(80)  # ms
        self._render_timer.timeout.connect(self._do_render)

        # ---- Single-document state (swapped on tab switch) ----
        self.document = None
        self.current_path = None
        self.current_page = 0
        self.zoom = 1.25
        self.fit_to_window = True
        self.search_text = ""
        self.search_results = []
        self.current_result_index = -1
        self.current_render_zoom = 1.0
        self.selected_text = ""
        self.selected_rects = []
        self.ocr_text_pages = OrderedDict()
        self.ocr_warning_shown = False

        # ---- Tab management ----
        self.tabs: dict[int, TabData] = {}
        self.tab_counter = 0
        self.current_tab_id: int | None = None

        # ---- AcroForm controllers (Phase 2) ----
        self._form_controllers: dict[int, _FormController] = {}
        _app_data = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        self._form_store = _ff.FormStateStore(base_dir=Path(_app_data))

        # ---- Editing: Fill / Add Text / Sign / Image (v1.3.0) ----
        self._edit_controllers: dict[int, edit_ui.EditController] = {}
        self._edit_tool_buttons: dict[str, QToolButton] = {}
        self._edit_tool: str | None = None
        self._context_toolbar = None
        self._ctx_updating = False
        self._ctx_color_value = "#000000"
        self._signed_warning_tabs: set[int] = set()
        self._signature_store = sig_store.SignatureStore(
            Path(_app_data) / "signatures"
        )
        self._form_menu = None
        self._navigator_action = None

        # ---- Dark mode ----
        self._theme = self.settings.value("theme", self.THEME_AUTO, int)
        self._dark_mode = self._compute_dark_mode()

        # ---- Recent files ----
        self._recent_files = self._load_recent_files()

        # ---- Workspace session ----
        self._auto_restore = self.settings.value("autoRestore", True, bool)
        self._session_dont_ask = self.settings.value("sessionDontAsk", False, bool)
        self._session_data: list[dict] | None = None
        self._open_in_progress = False

        # ---- Update system ----
        self._update_nam = QNetworkAccessManager(self)
        self._update_nam.finished.connect(self._on_update_check_reply)

        self._log_update(f"app_launch: version={__version__}")
        self._auto_update_check = self.settings.value(SETTINGS_AUTO_UPDATE_KEY, True, bool)
        self._install_source = install_source.detect_install_source()

        self._build_ui()
        self._build_actions()
        self._build_menus()
        self._build_shortcuts()
        self._apply_theme()
        self._update_controls()
        QApplication.instance().installEventFilter(self)

        # Defer non-critical init to after window is shown
        QTimer.singleShot(0, self._update_recent_menu)

        # Auto-update check on launch
        if self._auto_update_check:
            QTimer.singleShot(3000, self.check_for_updates_silent)

        # First-launch default PDF reader prompt (Windows only)
        QTimer.singleShot(1500, self._maybe_prompt_default_app)

        _perf_end(_perf_start_t, "PdfReaderWindow.__init__")
        QApplication.styleHints().colorSchemeChanged.connect(self._on_system_theme_change)

        # Restore workspace if available
        QTimer.singleShot(100, self._restore_session)

        _perf_end(_perf_start_t, "PdfReaderWindow.__init__")

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget(self)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Tab strip
        tab_strip = QWidget()
        tab_strip.setObjectName("TabStrip")
        tab_strip_layout = QHBoxLayout(tab_strip)
        tab_strip_layout.setContentsMargins(0, 0, 0, 0)
        tab_strip_layout.setSpacing(0)

        self.tab_bar = QTabBar()
        self.tab_bar.setTabsClosable(False)
        self.tab_bar.setMovable(True)
        self.tab_bar.setExpanding(False)
        self.tab_bar.setDocumentMode(True)
        self.tab_bar.setDrawBase(False)
        self.tab_bar.setUsesScrollButtons(True)
        self.tab_bar.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.tab_bar.tabBarDoubleClicked.connect(self._on_tab_double_click)
        self.tab_bar.currentChanged.connect(self._on_tab_switch)
        tab_strip_layout.addWidget(self.tab_bar)

        self.new_tab_button = QToolButton()
        self.new_tab_button.setObjectName("NewTabButton")
        self.new_tab_button.setIconSize(QSize(16, 16))
        self.new_tab_button.setFixedSize(28, 28)
        self.tab_bar.setMinimumWidth(1)
        self.new_tab_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.new_tab_button.setCursor(Qt.PointingHandCursor)
        self.new_tab_button.setToolTip("New Tab (Ctrl+T)")
        self.new_tab_button.setAccessibleName("New blank tab")
        self.new_tab_button.clicked.connect(self.new_tab)
        tab_strip_layout.addWidget(self.new_tab_button)
        tab_strip_layout.addStretch(1)

        root.addWidget(tab_strip)
        self._sync_tab_strip()


        # Page content — quiet empty state
        self.empty_state_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_state_widget)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.setSpacing(16)

        self._empty_icon_label = QLabel()
        self._empty_icon_label.setPixmap(_make_empty_state_icon(self._dark_mode))
        self._empty_icon_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(self._empty_icon_label)

        title_label = QLabel("Open a PDF to begin")
        title_label.setObjectName("EmptyTitle")
        title_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(title_label)

        subtitle_label = QLabel(
            "Drag and drop a PDF here, or use <b>File → Open PDF</b> (Ctrl+O)<br>"
            "to start reading locally and privately."
        )
        subtitle_label.setObjectName("EmptySubtitle")
        subtitle_label.setWordWrap(True)
        subtitle_label.setFixedWidth(460)
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_row = QHBoxLayout()
        subtitle_row.addStretch()
        subtitle_row.addWidget(subtitle_label)
        subtitle_row.addStretch()
        empty_layout.addLayout(subtitle_row)

        open_btn = QPushButton("Open PDF")
        open_btn.setObjectName("OpenEmptyButton")
        open_btn.setFixedWidth(180)
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setAccessibleName("Open PDF")
        open_btn.clicked.connect(self.open_pdf)
        open_btn_layout = QHBoxLayout()
        open_btn_layout.addStretch()
        open_btn_layout.addWidget(open_btn)
        open_btn_layout.addStretch()
        empty_layout.addLayout(open_btn_layout)

        self.page_label = PdfPageLabel()
        self.page_label.setObjectName("PdfPage")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.selection_finished.connect(self.select_text_in_rect)
        self.page_label.sticky_note_requested.connect(self._place_sticky_note)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.empty_state_widget)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.viewport().setObjectName("DocumentViewport")
        self.scroll_area.viewport().installEventFilter(self)
        self.scroll_area.verticalScrollBar().valueChanged.connect(
            self._on_continuous_scrolled
        )
        root.addWidget(self.scroll_area, 1)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar(self))

        # Stack for page_label vs empty_state
        self._content_stack = {None: self.empty_state_widget}
        self._current_content = None

        self._build_navigator_dock()

    def _build_navigator_dock(self):
        """Right-hand dock listing form fields and their status."""
        self.form_dock = QDockWidget("Form Navigator", self)
        self.form_dock.setObjectName("formNavigatorDock")
        self.form_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.form_tree = QTreeWidget()
        self.form_tree.setHeaderLabels(["Field", "Status", "Value"])
        self.form_tree.setColumnWidth(0, 170)
        self.form_tree.setColumnWidth(1, 70)
        self.form_tree.setRootIsDecorated(True)
        self.form_tree.setUniformRowHeights(True)
        self.form_tree.itemClicked.connect(self._on_navigator_item_clicked)
        self.form_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.form_dock.setWidget(self.form_tree)
        self.addDockWidget(Qt.RightDockWidgetArea, self.form_dock)
        self.form_dock.hide()

        # Debounce navigator rebuilds (fires on every keystroke in a field).
        self._navigator_rebuild_timer = QTimer(self)
        self._navigator_rebuild_timer.setSingleShot(True)
        self._navigator_rebuild_timer.setInterval(250)
        self._navigator_rebuild_timer.timeout.connect(self._rebuild_navigator)

    def _build_actions(self):
        """Build the single, unified application toolbar.

        Everything the reader needs lives on one 44 px Fluent-style row:
        file actions, page navigation, zoom, annotations, and search.
        """
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setObjectName("MainToolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE))
        toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        toolbar.setContextMenuPolicy(Qt.PreventContextMenu)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        self.toolbar = toolbar

        self._icon_buttons: dict[str, QToolButton] = {}
        self._icon_specs: dict[str, object] = {}
        self._search_icon_action = None
        # The tab strip's "+" button shares the vector plus icon.
        self._icon_specs["new_tab"] = _TOOLBAR_ICONS["plus"]
        self._icon_buttons["new_tab"] = self.new_tab_button

        def icon_button(
            spec: str,
            tooltip: str,
            accessible_name: str,
            *,
            checkable: bool = False,
            size: int = TOOLBAR_BUTTON_SIZE,
        ) -> QToolButton:
            button = QToolButton(toolbar)
            button.setObjectName("ToolbarButton")
            button.setIconSize(QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE))
            button.setFixedSize(size, size)
            button.setToolTip(tooltip)
            button.setAccessibleName(accessible_name)
            button.setCheckable(checkable)
            button.setCursor(Qt.PointingHandCursor)
            button.setFocusPolicy(Qt.StrongFocus)
            self._icon_specs[spec] = _TOOLBAR_ICONS[spec]
            self._icon_buttons[spec] = button
            return button

        # ── File ──
        open_button = icon_button("open", "Open PDF (Ctrl+O)", "Open PDF")
        open_button.clicked.connect(self.open_pdf)
        save_button = icon_button("save", "Save document (Ctrl+S)", "Save document")
        save_button.clicked.connect(self._save_document)
        toolbar.addWidget(open_button)
        toolbar.addWidget(save_button)

        # ── Page navigation ──
        toolbar.addSeparator()
        self.prev_button = icon_button(
            "chevron_left", "Previous page (Page Up)", "Previous page"
        )
        self.prev_button.clicked.connect(self.previous_page)
        self.next_button = icon_button(
            "chevron_right", "Next page (Page Down)", "Next page"
        )
        self.next_button.clicked.connect(self.next_page)

        self.page_spin = QSpinBox(toolbar)
        self.page_spin.setObjectName("PageSpin")
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(1)
        self.page_spin.setFixedWidth(46)
        self.page_spin.setAlignment(Qt.AlignCenter)
        self.page_spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.page_spin.setKeyboardTracking(False)
        self.page_spin.setToolTip("Page number — type a number and press Enter")
        self.page_spin.setAccessibleName("Page number")
        self.page_spin.valueChanged.connect(self.jump_to_page)

        self.page_count_label = QLabel("/ 0", toolbar)
        self.page_count_label.setObjectName("PageCount")
        self.page_count_label.setMinimumWidth(46)
        self.page_count_label.setAccessibleName("Page count")

        toolbar.addWidget(self.prev_button)
        toolbar.addWidget(self.page_spin)
        toolbar.addWidget(self.page_count_label)
        toolbar.addWidget(self.next_button)

        # ── Zoom ──
        toolbar.addSeparator()
        self.zoom_out_button = icon_button(
            "minus", "Zoom out (Ctrl+- or Ctrl+Mouse Wheel)", "Zoom out"
        )
        self.zoom_out_button.clicked.connect(self.zoom_out)

        self.zoom_label = QLabel("100%", toolbar)
        self.zoom_label.setObjectName("ZoomLabel")
        self.zoom_label.setAlignment(Qt.AlignCenter)
        self.zoom_label.setFixedWidth(42)
        self.zoom_label.setToolTip("Current zoom level")
        self.zoom_label.setAccessibleName("Zoom level")

        self.zoom_in_button = icon_button(
            "plus", "Zoom in (Ctrl+= or Ctrl+Mouse Wheel)", "Zoom in"
        )
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.fit_button = icon_button(
            "fit", "Fit page to window (Ctrl+0)", "Fit page", checkable=True
        )
        self.fit_button.setChecked(True)
        self.fit_button.toggled.connect(self._on_fit_toggled)

        toolbar.addWidget(self.zoom_out_button)
        toolbar.addWidget(self.zoom_label)
        toolbar.addWidget(self.zoom_in_button)
        toolbar.addWidget(self.fit_button)

        # ── Annotations ──
        toolbar.addSeparator()
        self.copy_button = icon_button(
            "copy", "Copy selected text (Ctrl+C)", "Copy selected text"
        )
        self.copy_button.clicked.connect(self.copy_selected_text)
        self.highlight_button = icon_button(
            "highlight", "Highlight selected text", "Highlight selected text"
        )
        self.highlight_button.clicked.connect(self.highlight_selection)
        self.underline_button = icon_button(
            "underline", "Underline selected text", "Underline selected text"
        )
        self.underline_button.clicked.connect(self.underline_selection)
        self.strike_button = icon_button(
            "strike", "Strikethrough selected text", "Strikethrough selected text"
        )
        self.strike_button.clicked.connect(self.strikeout_selection)
        self.sticky_button = icon_button(
            "sticky", "Place sticky note", "Place sticky note", checkable=True
        )
        self.sticky_button.clicked.connect(self._toggle_sticky_note_mode)
        for annotation_button in (
            self.copy_button,
            self.highlight_button,
            self.underline_button,
            self.strike_button,
            self.sticky_button,
        ):
            toolbar.addWidget(annotation_button)

        # ── Edit: Fill / Add Text / Sign / Image (v1.3.0) ──
        toolbar.addSeparator()
        self.fill_button = icon_button(
            "fill", "Fill form fields", "Fill form fields"
        )
        self.fill_button.clicked.connect(self._focus_first_form_field)
        self.text_button = icon_button(
            "text", "Add text", "Add text", checkable=True
        )
        self.text_button.clicked.connect(
            lambda checked: self._activate_edit_tool("text", checked)
        )
        self.sign_button = icon_button(
            "signature", "Add signature", "Add signature", checkable=True
        )
        self.sign_button.clicked.connect(self._choose_signature)
        self.image_button = icon_button(
            "image", "Insert image", "Insert image", checkable=True
        )
        self.image_button.clicked.connect(self._choose_image)
        self._edit_tool_buttons = {
            "text": self.text_button,
            "sign": self.sign_button,
            "image": self.image_button,
        }
        for edit_button in (
            self.fill_button,
            self.text_button,
            self.sign_button,
            self.image_button,
        ):
            toolbar.addWidget(edit_button)

        # Keep search anchored to the right edge of the toolbar.
        spacer = QWidget(toolbar)
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        # ── Search ──
        self.search_input = QLineEdit(toolbar)
        self.search_input.setObjectName("SearchInput")
        self.search_input.setPlaceholderText("Search document")
        self.search_input.setClearButtonEnabled(False)
        self.search_input.setMinimumWidth(160)
        self.search_input.setMaximumWidth(320)
        self.search_input.setFixedHeight(30)
        self.search_input.setAccessibleName("Search document")
        self._search_icon_action = self.search_input.addAction(
            _make_toolbar_icon(_TOOLBAR_ICONS["search"], self._dark_mode),
            QLineEdit.LeadingPosition,
        )
        self._search_clear_action = self.search_input.addAction(
            _make_toolbar_icon(_TOOLBAR_ICONS["close"], self._dark_mode),
            QLineEdit.TrailingPosition,
        )
        self._search_clear_action.setToolTip("Clear search")
        self._search_clear_action.setVisible(False)
        self._search_clear_action.triggered.connect(self.search_input.clear)
        self.search_input.textChanged.connect(
            lambda text: self._search_clear_action.setVisible(bool(text))
        )
        self.search_input.returnPressed.connect(self.search)
        self.search_input.textChanged.connect(self._search_text_changed)

        self.search_prev_button = icon_button(
            "chevron_up",
            "Previous match",
            "Previous match",
            size=TOOLBAR_SMALL_BUTTON_SIZE,
        )
        self.search_prev_button.clicked.connect(self.previous_search_result)
        self.search_next_button = icon_button(
            "chevron_down",
            "Next match",
            "Next match",
            size=TOOLBAR_SMALL_BUTTON_SIZE,
        )
        self.search_next_button.clicked.connect(self.next_search_result)

        self.search_count_label = QLabel("0", toolbar)
        self.search_count_label.setObjectName("SearchCount")
        self.search_count_label.setFixedWidth(40)
        self.search_count_label.setAlignment(Qt.AlignCenter)
        self.search_count_label.setAccessibleName("Search match count")

        # A text toggle rather than a checkbox: it inherits the toolbar's
        # hover/checked treatment and renders correctly in both themes.
        self.semantic_cb = QToolButton(toolbar)
        self.semantic_cb.setObjectName("SemanticToggle")
        self.semantic_cb.setText("Semantic")
        self.semantic_cb.setCheckable(True)
        self.semantic_cb.setToolTip(
            "Enable semantic (meaning-based) search instead of keyword exact match"
        )
        self.semantic_cb.setAccessibleName("Semantic search")
        self.semantic_cb.setCursor(Qt.PointingHandCursor)
        self.semantic_cb.setFocusPolicy(Qt.StrongFocus)

        toolbar.addWidget(self.search_input)
        toolbar.addWidget(self.search_prev_button)
        toolbar.addWidget(self.search_next_button)
        toolbar.addWidget(self.search_count_label)
        toolbar.addWidget(self.semantic_cb)

        self._refresh_toolbar_icons()
        self._build_context_toolbar()

    def _refresh_toolbar_icons(self):
        """Re-render every toolbar icon for the active theme."""
        for spec_name, button in getattr(self, "_icon_buttons", {}).items():
            draw_fn = self._icon_specs.get(spec_name)
            if draw_fn is not None:
                button.setIcon(_make_toolbar_icon(draw_fn, self._dark_mode))
        if getattr(self, "_search_icon_action", None) is not None:
            self._search_icon_action.setIcon(
                _make_toolbar_icon(_TOOLBAR_ICONS["search"], self._dark_mode)
            )
        if getattr(self, "_search_clear_action", None) is not None:
            self._search_clear_action.setIcon(
                _make_toolbar_icon(_TOOLBAR_ICONS["close"], self._dark_mode)
            )
        if getattr(self, "_empty_icon_label", None) is not None:
            self._empty_icon_label.setPixmap(_make_empty_state_icon(self._dark_mode))

    # ------------------------------------------------------------------
    # Editing: Fill / Add Text / Sign / Image (v1.3.0)
    # ------------------------------------------------------------------

    def _build_context_toolbar(self):
        self.addToolBarBreak(Qt.TopToolBarArea)
        bar = QToolBar("Context Toolbar", self)
        bar.setObjectName("ContextToolbar")
        bar.setMovable(False)
        bar.setFloatable(False)
        bar.setIconSize(QSize(16, 16))
        self.addToolBar(Qt.TopToolBarArea, bar)
        self.context_toolbar = bar

        self._ctx_font = QComboBox(bar)
        self._ctx_font.setObjectName("CtxCombo")
        for label, pdf_name in eo.TEXT_FONTS:
            self._ctx_font.addItem(label, pdf_name)
        self._ctx_font.setFixedWidth(150)
        self._ctx_font.currentIndexChanged.connect(self._on_context_style_changed)

        self._ctx_size = QSpinBox(bar)
        self._ctx_size.setObjectName("CtxSpin")
        self._ctx_size.setRange(6, 96)
        self._ctx_size.setValue(14)
        self._ctx_size.setFixedWidth(58)
        self._ctx_size.valueChanged.connect(self._on_context_style_changed)

        self._ctx_color = QToolButton(bar)
        self._ctx_color.setObjectName("CtxButton")
        self._ctx_color.setText("A")
        self._ctx_color.setToolTip("Text color")
        self._ctx_color.clicked.connect(self._choose_text_color)
        self._update_color_button()

        def toggle(label, tooltip, *, bold=False, italic=False, underline=False):
            button = QToolButton(bar)
            button.setObjectName("CtxButton")
            button.setText(label)
            button.setToolTip(tooltip)
            button.setCheckable(True)
            font = button.font()
            font.setBold(bold)
            font.setItalic(italic)
            font.setUnderline(underline)
            button.setFont(font)
            button.clicked.connect(self._on_context_style_changed)
            return button

        self._ctx_bold = toggle("B", "Bold", bold=True)
        self._ctx_italic = toggle("I", "Italic", italic=True)
        self._ctx_underline = toggle("U", "Underline", underline=True)

        self._ctx_align_group = QButtonGroup(self)
        self._ctx_align_group.setExclusive(True)
        self._ctx_align_left = toggle("L", "Align left")
        self._ctx_align_center = toggle("C", "Align center")
        self._ctx_align_right = toggle("R", "Align right")
        for button in (
            self._ctx_align_left,
            self._ctx_align_center,
            self._ctx_align_right,
        ):
            self._ctx_align_group.addButton(button)
        self._ctx_align_left.setChecked(True)

        self._ctx_rotate = QToolButton(bar)
        self._ctx_rotate.setObjectName("CtxButton")
        self._ctx_rotate.setText("Rotate 90°")
        self._ctx_rotate.setToolTip("Rotate the selected object by 90 degrees")
        self._ctx_rotate.clicked.connect(self._context_rotate)

        self._ctx_duplicate = QToolButton(bar)
        self._ctx_duplicate.setObjectName("CtxButton")
        self._ctx_duplicate.setText("Duplicate")
        self._ctx_duplicate.setToolTip("Duplicate the selected object")
        self._ctx_duplicate.clicked.connect(self._context_duplicate)

        self._ctx_delete = QToolButton(bar)
        self._ctx_delete.setObjectName("CtxButton")
        self._ctx_delete.setText("Delete")
        self._ctx_delete.setToolTip("Delete the selected object")
        self._ctx_delete.clicked.connect(self._context_delete)

        self._ctx_done = QToolButton(bar)
        self._ctx_done.setObjectName("CtxButton")
        self._ctx_done.setText("Done")
        self._ctx_done.setToolTip("Finish editing this text")
        self._ctx_done.clicked.connect(self._context_done)

        self._ctx_hint = QLabel("Select text or an object to format", bar)
        self._ctx_hint.setObjectName("CtxLabel")
        self._ctx_hint_action = bar.addWidget(self._ctx_hint)

        self._ctx_text_actions = []
        text_label = QLabel("Text", bar)
        text_label.setObjectName("CtxLabel")
        self._ctx_text_actions.append(bar.addWidget(text_label))
        for widget in (
            self._ctx_font,
            self._ctx_size,
            self._ctx_color,
            self._ctx_bold,
            self._ctx_italic,
            self._ctx_underline,
        ):
            self._ctx_text_actions.append(bar.addWidget(widget))
        self._ctx_text_actions.append(bar.addSeparator())
        for widget in (
            self._ctx_align_left,
            self._ctx_align_center,
            self._ctx_align_right,
        ):
            self._ctx_text_actions.append(bar.addWidget(widget))
        bar.addSeparator()
        for widget in (
            self._ctx_rotate,
            self._ctx_duplicate,
            self._ctx_delete,
        ):
            bar.addWidget(widget)
        self._ctx_done_action = bar.addWidget(self._ctx_done)
        self._ctx_text_widgets = [
            text_label,
            self._ctx_font,
            self._ctx_size,
            self._ctx_color,
            self._ctx_bold,
            self._ctx_italic,
            self._ctx_underline,
            self._ctx_align_left,
            self._ctx_align_center,
            self._ctx_align_right,
        ]
        for control in (
            self._ctx_font,
            self._ctx_size,
            self._ctx_color,
            self._ctx_bold,
            self._ctx_italic,
            self._ctx_underline,
            self._ctx_align_left,
            self._ctx_align_center,
            self._ctx_align_right,
            self._ctx_rotate,
            self._ctx_duplicate,
            self._ctx_delete,
            self._ctx_done,
        ):
            control.setFixedHeight(28)
        bar.hide()

    def _update_color_button(self):
        self._ctx_color.setStyleSheet(
            f"QToolButton#CtxButton {{ color: {self._ctx_color_value}; font-weight: 700; }}"
        )

    def _on_context_style_changed(self, *args):
        if self._ctx_updating:
            return
        controller = self._edit_for_current()
        obj = controller.selected_object() if controller else None
        if obj is None or obj.kind != eo.TEXT_KIND:
            return
        align = (
            "left"
            if self._ctx_align_left.isChecked()
            else "center"
            if self._ctx_align_center.isChecked()
            else "right"
        )
        style = eo.TextStyle(
            font_family=self._ctx_font.currentData() or "Helvetica",
            font_size=float(self._ctx_size.value()),
            color=self._ctx_color_value,
            bold=self._ctx_bold.isChecked(),
            italic=self._ctx_italic.isChecked(),
            underline=self._ctx_underline.isChecked(),
            align=align,
        )
        controller.apply_style(style)

    def _choose_text_color(self):
        color = QColorDialog.getColor(
            QColor(self._ctx_color_value), self, "Text Color"
        )
        if color.isValid():
            self._ctx_color_value = color.name()
            self._update_color_button()
            self._on_context_style_changed()

    def _context_rotate(self):
        controller = self._edit_for_current()
        if controller is not None:
            controller.rotate_selected(90)
            self._on_edit_selection_changed(controller.selected_object())

    def _context_duplicate(self):
        controller = self._edit_for_current()
        if controller is not None:
            controller.duplicate_selected()

    def _context_delete(self):
        controller = self._edit_for_current()
        if controller is not None:
            controller.delete_selected()

    def _context_done(self):
        controller = self._edit_for_current()
        if controller is not None:
            controller._finish_text_edit()

    def _on_edit_selection_changed(self, obj):
        if not getattr(self, "context_toolbar", None):
            return
        if obj is None:
            if self.document is None:
                self.context_toolbar.hide()
                return
            self._ctx_updating = True
            try:
                for action in getattr(self, "_ctx_text_actions", []):
                    action.setVisible(False)
                for widget in self._ctx_text_widgets:
                    widget.setVisible(False)
                if getattr(self, "_ctx_done_action", None) is not None:
                    self._ctx_done_action.setVisible(False)
                self._ctx_done.setVisible(False)
                if getattr(self, "_ctx_hint_action", None) is not None:
                    self._ctx_hint_action.setVisible(True)
                self._ctx_hint.setVisible(True)
                for control in (
                    self._ctx_rotate,
                    self._ctx_duplicate,
                    self._ctx_delete,
                ):
                    control.setEnabled(False)
            finally:
                self._ctx_updating = False
            self.context_toolbar.show()
            return
        controller = self._edit_for_current()
        self._ctx_updating = True
        try:
            if getattr(self, "_ctx_hint_action", None) is not None:
                self._ctx_hint_action.setVisible(False)
            self._ctx_hint.setVisible(False)
            for control in (
                self._ctx_rotate,
                self._ctx_duplicate,
                self._ctx_delete,
            ):
                control.setEnabled(True)
            is_text = obj.kind == eo.TEXT_KIND
            for action in getattr(self, "_ctx_text_actions", []):
                action.setVisible(is_text)
            for widget in self._ctx_text_widgets:
                widget.setVisible(is_text)
            editing = bool(
                is_text
                and controller is not None
                and getattr(controller, "_editor", None) is not None
            )
            if getattr(self, "_ctx_done_action", None) is not None:
                self._ctx_done_action.setVisible(editing)
            self._ctx_done.setVisible(editing)
            if is_text:
                style = obj.style.normalized()
                index = self._ctx_font.findData(style.font_family)
                self._ctx_font.setCurrentIndex(index if index >= 0 else 0)
                self._ctx_size.setValue(int(round(style.font_size)))
                self._ctx_color_value = style.color
                self._update_color_button()
                self._ctx_bold.setChecked(style.bold)
                self._ctx_italic.setChecked(style.italic)
                self._ctx_underline.setChecked(style.underline)
                self._ctx_align_left.setChecked(style.align == "left")
                self._ctx_align_center.setChecked(style.align == "center")
                self._ctx_align_right.setChecked(style.align == "right")
        finally:
            self._ctx_updating = False
        self.context_toolbar.show()

    def _on_edit_tool_changed(self, tool):
        for name, button in getattr(self, "_edit_tool_buttons", {}).items():
            button.blockSignals(True)
            button.setChecked(name == tool)
            button.blockSignals(False)
        self._edit_tool = tool
        controller = self._edit_for_current()
        self._on_edit_selection_changed(
            controller.selected_object() if controller is not None else None
        )

    def _init_edit(self):
        if self.current_tab_id is None or self.document is None or self.current_path is None:
            return None
        old = self._edit_controllers.pop(self.current_tab_id, None)
        if old is not None:
            old.detach_all()
        tab_id = self.current_tab_id
        controller = edit_ui.EditController(self, tab_id)
        controller.selectionChanged.connect(self._on_edit_selection_changed)
        controller.statusMessage.connect(
            lambda message: self.statusBar().showMessage(message, 6000)
        )
        controller.dirtyChanged.connect(
            lambda _dirty, tid=tab_id: self._on_edit_dirty(tid)
        )
        controller.toolChanged.connect(self._on_edit_tool_changed)
        controller.load(self.document, self.current_path)
        self._edit_controllers[self.current_tab_id] = controller
        self._edit_tool = None
        return controller

    def _edit_for_current(self):
        if self.current_tab_id is None:
            return None
        return self._edit_controllers.get(self.current_tab_id)

    def _drop_edit_controller(self, tab_id):
        controller = self._edit_controllers.pop(tab_id, None)
        if controller is not None:
            controller.detach_all()
        if tab_id == self.current_tab_id:
            self._edit_tool = None
            self._on_edit_selection_changed(None)

    def _on_edit_dirty(self, tab_id):
        self._update_window_title_dirty()
        self._refresh_tab_dirty(tab_id)

    def _refresh_tab_dirty(self, tab_id):
        form = self._form_controllers.get(tab_id)
        edit = self._edit_controllers.get(tab_id)
        dirty = bool(
            (form is not None and form.dirty)
            or (edit is not None and edit.is_dirty())
        )
        tab = self.tabs.get(tab_id)
        if tab is None:
            return
        for index in range(self.tab_bar.count()):
            if self.tab_bar.tabData(index) == tab_id:
                self.tab_bar.setTabText(
                    index, ("● " if dirty else "") + tab.name
                )
                break

    def _document_dirty(self, tab_id) -> bool:
        form = self._form_controllers.get(tab_id)
        edit = self._edit_controllers.get(tab_id)
        return bool(
            (form is not None and form.dirty)
            or (edit is not None and edit.is_dirty())
        )

    def _current_document_encrypted(self) -> bool:
        tab = self.tabs.get(self.current_tab_id) if self.current_tab_id else None
        return bool(getattr(tab, "encrypted", False))

    def _focus_first_form_field(self):
        form = self._form_for_current()
        if form is not None:
            self.form_dock.show()
            self._rebuild_navigator()
            if form.editable_fields:
                form.focus_next(forward=True)
                self.statusBar().showMessage(
                    "Form fields are editable — click any field.", 6000
                )
                return
        self.statusBar().showMessage(
            "This document has no interactive form fields; use Add Text instead.",
            6000,
        )

    def _activate_edit_tool(self, tool: str, checked: bool):
        if not checked:
            if self._edit_tool == tool:
                self._deactivate_edit_tool()
            return
        controller = self._edit_for_current()
        if controller is None or self.document is None:
            self._uncheck_edit_tools()
            return
        if not eo.document_allows_editing(self.document):
            self._uncheck_edit_tools()
            self.statusBar().showMessage(
                "This document is read-only or encrypted and cannot be edited.", 6000
            )
            return
        if not self._confirm_edit_on_signed():
            self._uncheck_edit_tools()
            return
        controller.set_tool(tool)
        self._edit_tool = tool
        if tool == "text":
            self.statusBar().showMessage(
                "Click on the page to add text. Escape to cancel.", 6000
            )

    def _uncheck_edit_tools(self):
        for button in self._edit_tool_buttons.values():
            button.blockSignals(True)
            button.setChecked(False)
            button.blockSignals(False)
        self._edit_tool = None

    def _deactivate_edit_tool(self):
        controller = self._edit_for_current()
        if controller is not None:
            controller.set_tool(None)
        self._uncheck_edit_tools()
        self._edit_tool = None
        self._on_edit_selection_changed(None)

    def _choose_signature(self):
        controller = self._edit_for_current()
        if controller is None or self.document is None:
            self.sign_button.setChecked(False)
            return
        if not eo.document_allows_editing(self.document):
            self.sign_button.setChecked(False)
            self.statusBar().showMessage(
                "This document cannot be edited.", 5000
            )
            return
        if not self._confirm_edit_on_signed():
            self.sign_button.setChecked(False)
            return
        dialog = edit_ui.SignatureDialog(self._signature_store, self)
        if dialog.exec() and dialog.result_png:
            controller.set_pending_image(
                "signature", dialog.result_png, dialog.result_name
            )
            self._edit_tool = "sign"
            self.statusBar().showMessage(
                "Click on the page to place the signature. Escape to cancel.",
                6000,
            )
        else:
            self._uncheck_edit_tools()
            controller.set_tool(None)

    def _choose_image(self):
        controller = self._edit_for_current()
        if controller is None or self.document is None:
            self.image_button.setChecked(False)
            return
        if not eo.document_allows_editing(self.document):
            self.image_button.setChecked(False)
            self.statusBar().showMessage("This document cannot be edited.", 5000)
            return
        if not self._confirm_edit_on_signed():
            self.image_button.setChecked(False)
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Insert Image",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif)",
        )
        if not path:
            self._uncheck_edit_tools()
            return
        image = QImage(path)
        if image.isNull():
            self.image_button.setChecked(False)
            self.statusBar().showMessage("That image could not be read.", 5000)
            return
        image = image.convertToFormat(QImage.Format_RGBA8888)
        buffer = QBuffer()
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        png = bytes(buffer.data())
        buffer.close()
        controller.set_pending_image("image", png, Path(path).name)
        self._edit_tool = "image"
        self.statusBar().showMessage(
            "Click on the page to place the image. Escape to cancel.", 6000
        )

    def _confirm_edit_on_signed(self) -> bool:
        if self.document is None or not eo.document_has_signatures(self.document):
            return True
        if self.current_tab_id in self._signed_warning_tabs:
            return True
        box = QMessageBox(self)
        box.setWindowTitle("Digital Signature Detected")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(
            "This PDF contains a digital signature.\n\n"
            "Editing it will invalidate the existing signature. "
            "OpenReader uses visual electronic signatures only and does not "
            "create certificate-based digital signatures."
        )
        continue_button = box.addButton("Continue Editing", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is continue_button:
            self._signed_warning_tabs.add(self.current_tab_id)
            return True
        return False

    def _confirm_save_signed(self) -> bool:
        if not self._document_dirty(self.current_tab_id):
            return True
        if self.document is None or not eo.document_has_signatures(self.document):
            return True
        box = QMessageBox(self)
        box.setWindowTitle("Signed Document")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(
            "Saving changes to this signed document will invalidate its "
            "existing digital signature."
        )
        save_button = box.addButton("Save Anyway", QMessageBox.ButtonRole.DestructiveRole)
        copy_button = box.addButton("Save As Copy…", QMessageBox.ButtonRole.ActionRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is save_button:
            return True
        if box.clickedButton() is copy_button:
            self._save_document_as()
            return False
        return False

    def _edit_undo(self) -> bool:
        controller = self._edit_for_current()
        if controller is not None:
            focus = QApplication.focusWidget()
            if controller._editor is not None and focus is controller._editor:
                controller._editor.undo()
                return True
            if controller.undo():
                return True
        focus = QApplication.focusWidget()
        if isinstance(focus, (QLineEdit, QTextEdit)):
            focus.undo()
            return True
        return False

    def _edit_redo(self) -> bool:
        controller = self._edit_for_current()
        if controller is not None:
            focus = QApplication.focusWidget()
            if controller._editor is not None and focus is controller._editor:
                controller._editor.redo()
                return True
            if controller.redo():
                return True
        focus = QApplication.focusWidget()
        if isinstance(focus, (QLineEdit, QTextEdit)):
            focus.redo()
            return True
        return False

    def _edit_escape(self) -> bool:
        controller = self._edit_for_current()
        if controller is None:
            return False
        if controller._editor is not None:
            controller._cancel_text_edit()
            return True
        if controller.tool is not None:
            self._deactivate_edit_tool()
            return True
        if controller.selected_object() is not None:
            controller.select(None)
            controller.set_tool(None)
            return True
        return False

    def _edit_delete_key(self) -> bool:
        focus = QApplication.focusWidget()
        if isinstance(focus, (QLineEdit, QTextEdit, QSpinBox, QComboBox)):
            return False
        controller = self._edit_for_current()
        if controller is not None and controller.selected_object() is not None:
            controller.delete_selected()
            return True
        return False

    def _edit_paste_shortcut(self) -> bool:
        focus = QApplication.focusWidget()
        if isinstance(focus, (QLineEdit, QTextEdit)):
            return False
        controller = self._edit_for_current()
        return bool(controller is not None and controller.paste())

    def _page_index_for_label(self, obj):
        if obj is self.page_label:
            return self.current_page
        labels = getattr(self, "_continuous_pages", [])
        try:
            return labels.index(obj)
        except ValueError:
            return None

    def _export_flattened(self):
        if self.document is None or self.current_path is None:
            self.statusBar().showMessage("No document open", 3000)
            return
        controller = self._edit_for_current()
        if controller is not None:
            controller._finish_text_edit()
        form = self._form_for_current()
        if form is not None:
            self._write_dirty_form_values(form)
        default_name = f"{Path(self.current_path).stem}_flattened.pdf"
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Export Flattened PDF",
            str(Path(self.current_path).with_name(default_name)),
            "PDF files (*.pdf)",
        )
        if not target:
            return
        if not target.lower().endswith(".pdf"):
            target += ".pdf"
        try:
            eo.export_flattened(self.document, target)
            self.statusBar().showMessage(
                f"Flattened copy saved as {Path(target).name}", 5000
            )
        except Exception as exc:
            self.statusBar().showMessage(f"Export failed: {exc}", 6000)

    def _save_tab(self, tab_id) -> bool:
        tab = self.tabs.get(tab_id)
        if tab is None or tab.document is None or not tab.path:
            return False
        form = self._form_controllers.get(tab_id)
        edit = self._edit_controllers.get(tab_id)
        try:
            if form is not None and form.dirty:
                for name in form._dirty_names:
                    field = form._by_name.get(name)
                    if field is None or not field.is_editable():
                        continue
                    try:
                        _ff.set_field_value(
                            tab.document, field, form.current_value(field)
                        )
                    except Exception:  # nosec B112
                        continue
            if edit is not None:
                edit._finish_text_edit()
            eo.save_document(tab.document, tab.path)
            if edit is not None:
                edit.mark_saved()
            if form is not None:
                form.dirty = False
                form._dirty_names = set()
                if getattr(form, "_state_store", None) is not None:
                    form._state_store.clear(tab.path)
            self._refresh_tab_dirty(tab_id)
            self._update_window_title_dirty()
            return True
        except Exception as exc:
            self.statusBar().showMessage(f"Save failed: {exc}", 6000)
            return False

    @staticmethod
    def _menu_label(label: str, shortcut: str) -> str:
        return f"{label}\t{shortcut}"

    def _build_shortcuts(self):
        self._app_shortcuts: list[QShortcut] = []
        shortcut_handlers = {
            "open_pdf": self.open_pdf,
            "save": self._save_document,
            "find": self.focus_search,
            "copy": self._copy_shortcut,
            "previous_page": self.previous_page,
            "next_page": self.next_page,
            "zoom_in": self.zoom_in,
            "zoom_out": self.zoom_out,
            "fit_width": self._fit_width_shortcut,
            "close_tab": self._close_current_tab,
            "new_tab": self.new_tab,
            "next_field": self._form_next_field,
            "previous_field": self._form_previous_field,
        }
        for shortcut_id, sequence in self.REGISTERED_SHORTCUTS:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.ApplicationShortcut)
            shortcut.activated.connect(shortcut_handlers[shortcut_id])
            self._app_shortcuts.append(shortcut)

    def eventFilter(self, obj, event):
        # Editing tools capture a click on a rendered page to place an object.
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            if self._edit_tool in ("text", "sign", "image"):
                page_index = self._page_index_for_label(obj)
                if page_index is not None:
                    edit = self._edit_for_current()
                    zoom = (
                        self._continuous_layout_zoom
                        if self._continuous_mode
                        else self.current_render_zoom
                    )
                    if edit is not None and edit.handle_page_click(
                        page_index, obj, event.position().toPoint(), zoom or 1.0
                    ):
                        return True
        # Ctrl + Mouse Wheel zoom on the scroll area viewport
        if (event.type() == QEvent.Wheel
                and obj is self.scroll_area.viewport()
                and event.modifiers() & Qt.ControlModifier
                and self.document is not None):
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()
            return True  # consumed — prevent scrolling
        if event.type() == QEvent.KeyPress and self.isActiveWindow():
            if self._handle_shortcut_key_event(event):
                return True
        return super().eventFilter(obj, event)

    def _handle_shortcut_key_event(self, event) -> bool:
        modifiers = event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier | Qt.AltModifier | Qt.MetaModifier)
        key = event.key()
        if modifiers == Qt.NoModifier:
            if key == Qt.Key_PageUp:
                self.previous_page()
                return True
            if key == Qt.Key_PageDown:
                self.next_page()
                return True
            if key == Qt.Key_Escape:
                return self._edit_escape()
            if key in (Qt.Key_Delete, Qt.Key_Backspace):
                return self._edit_delete_key()
            return False
        if modifiers == (Qt.ControlModifier | Qt.ShiftModifier):
            if key == Qt.Key_Z:
                return self._edit_redo()
            return False
        if modifiers != Qt.ControlModifier:
            return False

        if key in (Qt.Key_Z, Qt.Key_Y):
            return self._edit_undo() if key == Qt.Key_Z else self._edit_redo()
        if key == Qt.Key_V:
            focus = QApplication.focusWidget()
            if isinstance(focus, (QLineEdit, QTextEdit)):
                return False
            controller = self._edit_for_current()
            return bool(controller is not None and controller.paste())

        ctrl_handlers = {
            Qt.Key_O: self.open_pdf,
            Qt.Key_T: self.new_tab,
            Qt.Key_W: self._close_current_tab,
            Qt.Key_F: self.focus_search,
            Qt.Key_S: self._save_document,
            Qt.Key_Equal: self.zoom_in,
            Qt.Key_Plus: self.zoom_in,
            Qt.Key_Minus: self.zoom_out,
            Qt.Key_0: self._fit_width_shortcut,
        }
        if key == Qt.Key_C:
            focus = QApplication.focusWidget()
            if isinstance(focus, QLineEdit) and focus.hasSelectedText():
                return False
            if isinstance(focus, QTextEdit) and focus.textCursor().hasSelection():
                return False
            self._copy_shortcut()
            return True
        handler = ctrl_handlers.get(key)
        if handler is None:
            return False
        handler()
        return True

    def _copy_shortcut(self):
        focus = QApplication.focusWidget()
        if isinstance(focus, QLineEdit) and focus.hasSelectedText():
            focus.copy()
            return
        if isinstance(focus, QTextEdit) and focus.textCursor().hasSelection():
            focus.copy()
            return
        if not isinstance(focus, (QLineEdit, QTextEdit)):
            controller = self._edit_for_current()
            if (
                controller is not None
                and controller.selected_object() is not None
                and controller.copy_selected()
            ):
                return
        self.copy_selected_text()

    def _fit_width_shortcut(self):
        if self.document is None:
            return
        self._on_fit_toggled(True)

    def _show_empty_state(self):
        if self.scroll_area.widget() is not self.empty_state_widget:
            self.scroll_area.takeWidget()
            self.scroll_area.setWidget(self.empty_state_widget)
            self.scroll_area.setWidgetResizable(True)

    @classmethod
    def _about_shortcuts_html(cls) -> str:
        rows = "\n".join(
            f"<tr><td><b>{label}</b></td><td style='padding-left:16px;color:#888;'>{shortcut}</td></tr>"
            for label, shortcut in cls.ABOUT_SHORTCUTS
        )
        return f"<table style='font-size:12px; line-height:1.8; margin: 0 auto;'>{rows}</table>"

    def _build_menus(self):
        """File / Edit / View / Tools / Help menu bar."""
        menubar = self.menuBar()

        # ── File ──
        file_menu = menubar.addMenu("File")

        file_open = QAction(self._menu_label("Open PDF", "Ctrl+O"), self)
        file_open.triggered.connect(self.open_pdf)
        file_menu.addAction(file_open)

        file_menu.addSeparator()

        self._recent_menu = QMenu("Open Recent", self)
        file_menu.addMenu(self._recent_menu)

        file_menu.addSeparator()

        close_tab = QAction(self._menu_label("Close Tab", "Ctrl+W"), self)
        close_tab.triggered.connect(self._close_current_tab)
        file_menu.addAction(close_tab)

        close_all = QAction("Close All Tabs", self)
        close_all.triggered.connect(self._close_all_tabs)
        file_menu.addAction(close_all)

        file_menu.addSeparator()
        file_save = QAction(self._menu_label("Save PDF", "Ctrl+S"), self)
        file_save.triggered.connect(self._save_document)
        file_menu.addAction(file_save)

        file_save_as = QAction(self._menu_label("Save As…", "Ctrl+Shift+S"), self)
        file_save_as.triggered.connect(self._save_document_as)
        file_menu.addAction(file_save_as)

        file_export = QAction("Export Flattened PDF…", self)
        file_export.triggered.connect(self._export_flattened)
        file_menu.addAction(file_export)

        file_menu.addSeparator()

        settings_action = QAction("Settings…", self)
        settings_action.triggered.connect(self._open_settings_dialog)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # ── Edit ──
        edit_menu = menubar.addMenu("Edit")

        copy_action = QAction(self._menu_label("Copy Selected Text", "Ctrl+C"), self)
        copy_action.triggered.connect(self.copy_selected_text)
        edit_menu.addAction(copy_action)
        self.copy_action = copy_action

        edit_menu.addSeparator()

        find_menu_action = QAction(self._menu_label("Find", "Ctrl+F"), self)
        find_menu_action.triggered.connect(self.focus_search)
        edit_menu.addAction(find_menu_action)

        # ── View ──
        view_menu = menubar.addMenu("View")

        self.theme_menu = QMenu("Theme", self)
        view_menu.addMenu(self.theme_menu)

        self.theme_auto_action = QAction("System (Auto)", self, checkable=True)
        self.theme_auto_action.triggered.connect(lambda: self.set_theme(self.THEME_AUTO))
        self.theme_menu.addAction(self.theme_auto_action)

        self.theme_light_action = QAction("Light", self, checkable=True)
        self.theme_light_action.triggered.connect(lambda: self.set_theme(self.THEME_LIGHT))
        self.theme_menu.addAction(self.theme_light_action)

        self.theme_dark_action = QAction("Dark", self, checkable=True)
        self.theme_dark_action.triggered.connect(lambda: self.set_theme(self.THEME_DARK))
        self.theme_menu.addAction(self.theme_dark_action)

        self._sync_theme_menu_checks()
        view_menu.addSeparator()

        zoom_in_action = QAction(self._menu_label("Zoom In", "Ctrl+="), self)
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction(self._menu_label("Zoom Out", "Ctrl+-"), self)
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)

        fit_action = QAction(self._menu_label("Fit Width", "Ctrl+0"), self, checkable=True)
        fit_action.setChecked(True)
        fit_action.triggered.connect(self._on_fit_toggled)
        view_menu.addAction(fit_action)
        self._fit_menu_action = fit_action

        view_menu.addSeparator()

        self.show_annots_action = QAction("Show Annotations", self, checkable=True)
        self.show_annots_action.setChecked(True)
        self.show_annots_action.triggered.connect(self._toggle_annotations_visible)
        view_menu.addAction(self.show_annots_action)

        view_menu.addSeparator()

        continuous_action = QAction("Continuous Scroll", self, checkable=True)
        continuous_action.setChecked(self._continuous_mode)
        continuous_action.triggered.connect(self._toggle_continuous_mode)
        view_menu.addAction(continuous_action)
        self._continuous_menu_action = continuous_action

        # ── Tools ──
        tools_menu = menubar.addMenu("Tools")

        annot_menu = tools_menu.addMenu("Annotations")
        annot_menu.addAction("Highlight Selection", self.highlight_selection)
        annot_menu.addAction("Underline Selection", self.underline_selection)
        annot_menu.addAction("Strikethrough Selection", self.strikeout_selection)
        annot_menu.addSeparator()
        annot_menu.addAction("Place Sticky Note", self._toggle_sticky_note_mode)
        annot_menu.addSeparator()
        annot_menu.addAction("Delete All Annotations on This Page", self._delete_page_annotations)
        annot_menu.addAction("Delete All Annotations in Document", self._delete_all_annotations)

        tools_menu.addSeparator()
        tools_menu.addAction("Merge PDFs", self.merge_pdfs)
        tools_menu.addAction("Split PDF", self.split_pdf)
        tools_menu.addAction("Compress PDF", self.compress_pdf)
        tools_menu.addSeparator()
        tools_menu.addAction("Compare PDFs", self._open_compare_dialog)
        tools_menu.addAction("Library Search", self._open_library_dialog)

        # ── Form (Phase 2 — PDF Form Intelligence) ──
        form_menu = menubar.addMenu("Form")
        self._form_menu = form_menu

        self.navigator_action = QAction("Form Navigator", self, checkable=True)
        self.navigator_action.triggered.connect(self._toggle_navigator)
        form_menu.addAction(self.navigator_action)

        form_menu.addSeparator()
        form_menu.addAction(self._menu_label("Next Field", "Ctrl+Down"), self._form_next_field)
        form_menu.addAction(self._menu_label("Previous Field", "Ctrl+Up"), self._form_previous_field)
        form_menu.addSeparator()
        form_menu.addAction("Clear Field", self._form_clear_field)
        form_menu.addAction("Clear Form", self._form_clear_all)
        form_menu.addSeparator()
        form_menu.addAction("Review & Complete…", self._form_review_complete)
        self._form_menu_actions = []
        for action in form_menu.actions():
            self._form_menu_actions.append(action)
        self._update_form_menu_state()

        # ── Help ──
        help_menu = menubar.addMenu("Help")
        self.update_action = QAction("Check for Updates", self)
        self.update_action.triggered.connect(self.check_for_updates)
        help_menu.addAction(self.update_action)
        help_menu.addSeparator()

        auto_update_action = QAction("Automatically Check for Updates", self, checkable=True)
        auto_update_action.setChecked(self._auto_update_check)
        auto_update_action.triggered.connect(self._toggle_auto_update_check)
        help_menu.addAction(auto_update_action)

        help_menu.addSeparator()
        about_action = QAction("About PDFReader", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # ------------------------------------------------------------------
    # Theme / Dark Mode
    # ------------------------------------------------------------------

    def _compute_dark_mode(self) -> bool:
        if self._theme == self.THEME_LIGHT:
            return False
        if self._theme == self.THEME_DARK:
            return True
        scheme = QApplication.styleHints().colorScheme()
        return scheme == Qt.ColorScheme.Dark

    def _on_system_theme_change(self, scheme):
        if self._theme == self.THEME_AUTO:
            self._dark_mode = scheme == Qt.ColorScheme.Dark
            self._apply_theme()

    def _sync_theme_menu_checks(self):
        self.theme_auto_action.setChecked(self._theme == self.THEME_AUTO)
        self.theme_light_action.setChecked(self._theme == self.THEME_LIGHT)
        self.theme_dark_action.setChecked(self._theme == self.THEME_DARK)

    def set_theme(self, theme):
        self._theme = theme
        self.settings.setValue("theme", theme)
        self._sync_theme_menu_checks()
        self._dark_mode = self._compute_dark_mode()
        self._apply_theme()

    def _apply_theme(self):
        stylesheet = DARK_STYLESHEET if self._dark_mode else LIGHT_STYLESHEET
        self.setStyleSheet(stylesheet)
        if hasattr(self, "scroll_area"):
            # The scroll viewport paints from the palette, not the QSS, so
            # give it the reading-surface colour explicitly.
            content = QColor("#141518" if self._dark_mode else "#ececee")
            viewport = self.scroll_area.viewport()
            widgets = [self.scroll_area, viewport]
            # QScrollArea enables autoFillBackground on its scroll widget, so
            # the empty state needs the reading-surface palette too.
            if hasattr(self, "empty_state_widget"):
                widgets.append(self.empty_state_widget)
            for widget in widgets:
                palette = widget.palette()
                palette.setColor(QPalette.ColorRole.Window, content)
                palette.setColor(QPalette.ColorRole.Base, content)
                widget.setPalette(palette)
            viewport.setAutoFillBackground(True)
        if hasattr(self, "_icon_buttons"):
            self._refresh_toolbar_icons()

    @staticmethod
    def _asset_path(name: str) -> str:
        candidates = []
        if getattr(sys, "frozen", False):
            candidates.append(Path(sys.executable).parent / "assets" / name)
            candidates.append(Path(sys.executable).parent / "_internal" / "assets" / name)
        candidates.append(Path(__file__).parent / "assets" / name)
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            candidates.append(Path(sys._MEIPASS) / "assets" / name)
        for candidate in candidates:
            if candidate.exists():
                return candidate.as_posix()
        return name

    # ------------------------------------------------------------------
    # Recent Files
    # ------------------------------------------------------------------

    def _load_recent_files(self) -> list[str]:
        raw = self.settings.value(SETTINGS_RECENT_KEY, [])
        if raw is None:
            raw = []
        if isinstance(raw, str):
            raw = [raw]
        recents = [p for p in raw if p and Path(p).exists()]

        # Migrate recents stored under the old key that was accidentally
        # named "***" (v1.2.4 and earlier) so users keep their history.
        if not recents and self.settings.contains("***"):
            legacy = self.settings.value("***", [])
            if isinstance(legacy, str):
                legacy = [legacy]
            recents = [p for p in legacy if p and Path(p).exists()]
            if recents:
                self.settings.setValue(SETTINGS_RECENT_KEY, recents)
            self.settings.remove("***")

        return recents

    def _save_recent_files(self):
        self.settings.setValue(SETTINGS_RECENT_KEY, self._recent_files)

    def _add_recent_file(self, path: str):
        if path in self._recent_files:
            self._recent_files.remove(path)
        self._recent_files.insert(0, path)
        if len(self._recent_files) > RECENT_FILES_MAX:
            self._recent_files = self._recent_files[:RECENT_FILES_MAX]
        self._save_recent_files()
        self._update_recent_menu()

    def _update_recent_menu(self):
        self._recent_menu.clear()
        if not self._recent_files:
            empty_action = self._recent_menu.addAction("(No recent files)")
            empty_action.setEnabled(False)
            return
        for p in self._recent_files:
            entry = Path(p)
            label = entry.name
            if len(label) > 50:
                label = label[:47] + "..."
            # Mark documents that contain fillable AcroForm fields (Phase 2).
            if self._is_recent_form_doc(p):
                label = f"📝 {label}"
            action = self._recent_menu.addAction(label)
            action.setToolTip(str(entry))
            action.triggered.connect(lambda _=False, path=p: self._open_recent(path))
        self._recent_menu.addSeparator()
        clear_action = self._recent_menu.addAction("Clear Recent Files")
        clear_action.triggered.connect(self._clear_recent_files)

    def _open_recent(self, path: str):
        if not Path(path).exists():
            QMessageBox.information(
                self, "File Not Found",
                f"The file no longer exists:\n\n{path}\n\nIt will be removed from the recent list."
            )
            self._recent_files = [p for p in self._recent_files if p != path]
            self._save_recent_files()
            self._update_recent_menu()
            return
        self.open_pdf(path)

    def _clear_recent_files(self):
        self._recent_files = []
        self._save_recent_files()
        self._update_recent_menu()

    # ------------------------------------------------------------------
    # Tab Management
    # ------------------------------------------------------------------

    def _next_tab_name(self) -> str:
        self.tab_counter += 1
        return f"Tab {self.tab_counter}"

    def _save_current_state(self):
        """Dump live state into the current TabData."""
        if self.current_tab_id is not None and self.current_tab_id in self.tabs:
            tab = self.tabs[self.current_tab_id]
            tab.document = self.document
            tab.path = self.current_path
            tab.current_page = self.current_page
            tab.zoom = self.zoom
            tab.fit_to_window = self.fit_to_window
            tab.search_text = self.search_text
            tab.search_results = self.search_results
            tab.current_result_index = self.current_result_index
            tab.current_render_zoom = self.current_render_zoom
            tab.selected_text = self.selected_text
            tab.selected_rects = self.selected_rects
            tab.ocr_text_pages = self.ocr_text_pages
            tab.ocr_warning_shown = self.ocr_warning_shown

    def _restore_state(self, tab_id: int):
        """Load state from a TabData into the live instance variables."""
        tab = self.tabs[tab_id]
        self.document = tab.document
        self.current_path = tab.path
        self.current_page = tab.current_page
        self.zoom = tab.zoom
        self.fit_to_window = tab.fit_to_window
        self.search_text = tab.search_text
        self.search_results = tab.search_results
        self.current_result_index = tab.current_result_index
        self.current_render_zoom = tab.current_render_zoom
        self.selected_text = tab.selected_text
        self.selected_rects = tab.selected_rects
        self.ocr_text_pages = tab.ocr_text_pages
        self.ocr_warning_shown = tab.ocr_warning_shown
        self.current_tab_id = tab_id

        # The page controls belong to the document, so refresh them on switch.
        page_count = self.document.page_count if self.document is not None else 0
        self.page_spin.setMaximum(max(1, page_count))
        self.page_count_label.setText(f"/ {page_count}")

    def _on_tab_double_click(self, index: int):
        self.new_tab()

    def _on_tab_switch(self, index: int):
        if index < 0 or index >= self.tab_bar.count():
            return
        new_tab_id = self.tab_bar.tabData(index)
        if new_tab_id is None or new_tab_id == self.current_tab_id:
            return
        old_edit = self._edit_for_current()
        if old_edit is not None:
            old_edit.detach_all()
        self._save_current_state()
        self._save_current_tab_controls()
        self._restore_state(new_tab_id)
        self._restore_current_tab_controls()
        if (
            self.current_tab_id not in self._edit_controllers
            and self.document is not None
            and self.current_path is not None
        ):
            self._init_edit()
        self.clear_text_selection(render=False)
        self.statusBar().clearMessage()
        self.render_page()
        self._update_controls()
        self._refresh_tab_dirty(new_tab_id)
        # Refresh form-related chrome for the newly selected tab (Phase 2).
        self._update_window_title_dirty()
        self._update_form_menu_state()
        self._navigator_rebuild_timer.start()

    def _save_current_tab_controls(self):
        pass

    def _restore_current_tab_controls(self):
        if self.fit_button.isChecked() != self.fit_to_window:
            self.fit_button.blockSignals(True)
            self.fit_button.setChecked(self.fit_to_window)
            self.fit_button.blockSignals(False)
        if hasattr(self, "_fit_menu_action") and self._fit_menu_action.isChecked() != self.fit_to_window:
            self._fit_menu_action.blockSignals(True)
            self._fit_menu_action.setChecked(self.fit_to_window)
            self._fit_menu_action.blockSignals(False)
        self.search_input.blockSignals(True)
        self.search_input.setText(self.search_text)
        self.search_input.blockSignals(False)
        if hasattr(self, "_search_clear_action"):
            self._search_clear_action.setVisible(bool(self.search_input.text()))
        if self.search_results:
            self.search_count_label.setText(self._search_count_text())
        else:
            self.search_count_label.setText("0")

    def _sync_tab_strip(self):
        """Hide the tab bar while there are no documents open."""
        self.tab_bar.setVisible(self.tab_bar.count() > 0)

    def _create_tab(self, tab_data: TabData) -> int:
        self._save_current_state()
        tab_id = id(tab_data)
        self.tabs[tab_id] = tab_data
        self.tab_bar.blockSignals(True)
        try:
            idx = self.tab_bar.addTab(tab_data.name)
            self.tab_bar.setTabData(idx, tab_id)
            self.tab_bar.setTabButton(idx, QTabBar.ButtonPosition.RightSide, self._create_tab_close_button(tab_id, tab_data.name))
            self.tab_bar.setCurrentIndex(idx)
        finally:
            self.tab_bar.blockSignals(False)
        self.current_tab_id = tab_id
        self._sync_tab_strip()
        return tab_id

    def _create_tab_close_button(self, tab_id: int, tab_name: str) -> QToolButton:
        close_button = QToolButton(self.tab_bar)
        close_button.setText("×")
        close_button.setObjectName("TabCloseButton")
        close_button.setFixedSize(20, 20)
        close_button.setAutoRaise(True)
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.setToolTip(f"Close {tab_name}")
        close_button.setAccessibleName(f"Close {tab_name}")
        close_button.clicked.connect(lambda _checked=False, tid=tab_id: self._close_tab(tid))
        return close_button

    def new_tab(self):
        """Create a new blank tab without opening a file dialog."""
        next_num = self.tab_bar.count() + 1
        tab_data = TabData(name=f"Tab {next_num}")
        self._create_tab(tab_data)
        self._show_empty_state()
        self._update_controls()
        self.statusBar().showMessage(f"Opened new tab (Tab {next_num})", 2000)
        self._log_update(f"new_tab: created Tab {next_num}")

    def _close_current_tab(self):
        tab_id = self.current_tab_id
        if tab_id is None or tab_id not in self.tabs:
            index = self.tab_bar.currentIndex()
            if index >= 0:
                tab_id = self.tab_bar.tabData(index)
        if tab_id is not None:
            self._close_tab(tab_id)

    def _close_tab(self, tab_id: int):
        if tab_id not in self.tabs:
            return
        # Warn before discarding unsaved form work (Phase 2).
        if not self._confirm_discard_form(tab_id):
            return
        tab = self.tabs[tab_id]
        was_current = tab_id == self.current_tab_id
        if was_current:
            self._save_current_state()
        fallback_id = None
        if was_current:
            remaining_ids = [candidate_id for candidate_id in self.tabs.keys() if candidate_id != tab_id]
            if remaining_ids:
                fallback_id = remaining_ids[-1]
        if tab.document is not None:
            tab.document.close()
        self._drop_form_controller(tab_id)
        self._drop_edit_controller(tab_id)
        self.tab_bar.blockSignals(True)
        try:
            for i in range(self.tab_bar.count()):
                if self.tab_bar.tabData(i) == tab_id:
                    self.tab_bar.removeTab(i)
                    break
        finally:
            self.tab_bar.blockSignals(False)
        del self.tabs[tab_id]
        self._sync_tab_strip()

        if not self.tabs:
            self.current_tab_id = None
            self.document = None
            self.current_path = None
            self.current_page = 0
            self.zoom = 1.25
            self.fit_to_window = True
            self.search_text = ""
            self.search_results = []
            self.current_result_index = -1
            self.selected_text = ""
            self.selected_rects = []
            self.ocr_text_pages = OrderedDict()
            self.ocr_warning_shown = False
            self.setWindowTitle(self.APP_NAME)
            self._show_empty_state()
            self.page_label.setText("Open a PDF to begin")
            self.page_label.setPixmap(QPixmap())
            self.page_label.adjustSize()
            self._update_controls()
            return

        if was_current and fallback_id in self.tabs:
            self.tab_bar.blockSignals(True)
            try:
                for i in range(self.tab_bar.count()):
                    if self.tab_bar.tabData(i) == fallback_id:
                        self.tab_bar.setCurrentIndex(i)
                        break
            finally:
                self.tab_bar.blockSignals(False)
            self._restore_state(fallback_id)
            fallback_tab = self.tabs[fallback_id]
            if fallback_tab.path and Path(fallback_tab.path).exists():
                try:
                    if fallback_tab.document is not None:
                        fallback_tab.document.close()
                    fallback_tab.document = self._safe_open_pdf(fallback_tab.path)
                    self.document = fallback_tab.document
                    self.current_path = fallback_tab.path
                except Exception:  # nosec B110 — fallback: skip failed tab, continue restoring others
                    pass
            self._restore_current_tab_controls()
            self.clear_text_selection(render=False)
            self.render_page()
            self._update_controls()

    def _close_all_tabs(self):
        tab_ids = list(self.tabs.keys())
        for tab_id in tab_ids:
            if not self._confirm_discard_form(tab_id):
                return
        for controller in getattr(self, "_form_controllers", {}).values():
            controller.detach_all()
        for controller in getattr(self, "_edit_controllers", {}).values():
            controller.detach_all()
        for tid in tab_ids:
            if tid in self.tabs:
                tab = self.tabs[tid]
                if tab.document is not None:
                    tab.document.close()
        self.tabs.clear()
        self._form_controllers.clear()
        self._edit_controllers.clear()
        self._edit_tool = None
        if getattr(self, "context_toolbar", None):
            self.context_toolbar.hide()
        self.tab_bar.clear()
        self._sync_tab_strip()
        self.current_tab_id = None
        self.document = None
        self.current_path = None
        self.current_page = 0
        self.search_results = []
        self.current_result_index = -1
        self.selected_text = ""
        self.selected_rects = []
        self.ocr_text_pages = OrderedDict()
        self.ocr_warning_shown = False
        self.setWindowTitle(self.APP_NAME)
        self._show_empty_state()
        self.page_label.setText("Open a PDF to begin")
        self.page_label.setPixmap(QPixmap())
        self.page_label.adjustSize()
        self._update_controls()

    # ------------------------------------------------------------------
    # PDF File Operations
    # ------------------------------------------------------------------

    def _pick_file_qt_dialog(self, start_dir: str) -> str | None:
        """Tier 1: Non-native Qt file dialog."""
        self.statusBar().showMessage("Opening file picker...", 2000)
        QApplication.processEvents()
        try:
            dlg = QFileDialog(self, "Open PDF", start_dir)
            dlg.setFileMode(QFileDialog.ExistingFile)
            dlg.setNameFilter("PDF Files (*.pdf)")
            dlg.setOption(QFileDialog.DontUseNativeDialog, True)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                selected = dlg.selectedFiles()
                if selected:
                    return selected[0]
            self._log_update("qt_dialog: no file selected (cancelled or empty)")
        except Exception as exc:
            self._log_update(f"qt_dialog: exception={exc}")
        return None

    def _pick_file_tkinter(self) -> str | None:
        """Tier 2: Tkinter native file dialog (Windows-safe fallback)."""
        self.statusBar().showMessage("Qt file picker unavailable; trying Windows fallback...", 3000)
        QApplication.processEvents()
        self._log_update("tkinter_fallback: attempting")
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            result = filedialog.askopenfilename(
                title="Open PDF",
                filetypes=[("PDF Files", "*.pdf")],
            )
            root.destroy()
            if result:
                self._log_update(f"tkinter_fallback: selected={result}")
                return result
            self._log_update("tkinter_fallback: cancelled")
        except ImportError:
            self._log_update("tkinter_fallback: tkinter not available")
        except Exception as exc:
            self._log_update(f"tkinter_fallback: exception={exc}")
        return None

    def _pick_file_manual_input(self) -> str | None:
        """Tier 3: Manual path input dialog."""
        self.statusBar().showMessage("File dialogs unavailable; enter path manually...", 3000)
        QApplication.processEvents()
        self._log_update("manual_input: attempting")
        try:
            path, ok = QInputDialog.getText(
                self, "Open PDF", "Enter PDF file path:",
            )
            if ok and path:
                path = path.strip().strip("\"'")
                p = Path(path).expanduser()
                if p.suffix.lower() == ".pdf" and p.exists():
                    self._log_update(f"manual_input: path={p}")
                    return str(p)
                self._log_update(f"manual_input: invalid path={path}")
                self.statusBar().showMessage(f"Invalid PDF path: {path}", 5000)
            else:
                self._log_update("manual_input: cancelled")
        except Exception as exc:
            self._log_update(f"manual_input: exception={exc}")
        return None

    def open_pdf(self, file_name: str | None = None):
        """Primary open entry point — all open paths converge here.

        When file_name is not provided, shows a single file picker dialog.
        Guarded against re-entrant calls (double signals, rapid clicks).
        """
        if isinstance(file_name, bool):
            # QAction.triggered(bool) and QPushButton.clicked(bool) pass a
            # checked-state argument. This slot treats that as "no path".
            file_name = None
        if self._open_in_progress:
            self._log_update("open_pdf: re-entrant call blocked (picker already shown)")
            return
        self._log_update(f"open_pdf called with file_name={file_name}")
        if file_name is not None:
            # Direct path — no dialog needed
            file_path = str(Path(file_name).resolve())
            self._log_update(f"open_pdf: direct path={file_path}")
            self.statusBar().showMessage(f"Opening {Path(file_path).name}...", 3000)
            QApplication.processEvents()
            tab_data = TabData(name=Path(file_path).name)
            self._create_tab(tab_data)
            self.load_pdf(file_path)
            return

        # No path — show a single file picker dialog (no cascading fallbacks)
        start_dir = self.settings.value("lastFolder", str(Path.home()))
        self._open_in_progress = True
        try:
            file_name = self._pick_file_qt_dialog(start_dir)
        finally:
            self._open_in_progress = False
        if not file_name:
            self._log_update("open_pdf: no file selected (cancelled)")
            self.statusBar().showMessage("Open cancelled", 3000)
            return

        file_path = str(Path(file_name).resolve())
        self._log_update(f"open_pdf: resolved path={file_path}")
        self.statusBar().showMessage(f"Opening {Path(file_path).name}...", 3000)
        QApplication.processEvents()
        tab_data = TabData(name=Path(file_path).name)
        self._create_tab(tab_data)
        self.load_pdf(file_path)

    def load_pdf(self, file_name):
        try:
            document = self._safe_open_pdf(file_name)
        except Exception as exc:
            self._show_error("Could Not Open PDF", "Unable to open this PDF file.", exc)
            self.statusBar().showMessage("Failed to open PDF", 5000)
            self._close_tab(self.current_tab_id)
            return

        if self.current_tab_id is not None and self.current_tab_id in self.tabs:
            self.tabs[self.current_tab_id].document = document
            self.tabs[self.current_tab_id].path = file_name
            try:
                self.tabs[self.current_tab_id].encrypted = bool(
                    document.needs_pass or document.is_encrypted
                )
            except Exception:
                self.tabs[self.current_tab_id].encrypted = False

        self.document = document
        self.current_path = file_name
        self.current_page = 0
        self.search_results = []
        self.current_result_index = -1
        self.ocr_text_pages = OrderedDict()
        self.ocr_warning_shown = False
        self.clear_text_selection(render=False)
        self.search_count_label.setText("0")

        # Show page count in status bar during initial load
        page_count = self.document.page_count
        name = Path(file_name).name
        if page_count > 500:
            self.statusBar().showMessage(f"Opening {name} ({page_count} pages)...")
            QApplication.processEvents()

        self.page_spin.blockSignals(True)
        self.page_spin.setMaximum(page_count)
        self.page_spin.setValue(1)
        self.page_spin.blockSignals(False)
        self.page_count_label.setText(f"/ {page_count}")

        self.settings.setValue("lastFolder", str(Path(file_name).parent))
        self._add_recent_file(str(Path(file_name).resolve()))

        if self.current_tab_id is not None:
            self.tabs[self.current_tab_id].name = name
            for i in range(self.tab_bar.count()):
                if self.tab_bar.tabData(i) == self.current_tab_id:
                    self.tab_bar.setTabText(i, name)
                    self.tab_bar.setTabToolTip(i, str(file_name))
                    break

        self.setWindowTitle(f"{self.APP_NAME} - {name}")

        # Build AcroForm overlays (Phase 2) before the first render.
        self._init_form()
        self._init_edit()

        self.render_page()
        self._update_controls()
        self.statusBar().showMessage(f"Opened {name}", 5000)

    def _safe_open_pdf(self, file_name):
        path = self._validate_pdf_path(file_name)
        document = None
        try:
            document = fitz.open(str(path))
            if document.page_count == 0:
                raise PdfSafetyError("The PDF does not contain any pages.")
            self._validate_document_pages(document)
            return document
        except Exception:
            if document is not None:
                document.close()
            raise

    def _validate_pdf_path(self, file_name):
        path = Path(file_name).expanduser()
        if not path.exists() or not path.is_file():
            raise PdfSafetyError("The selected file does not exist.")
        if path.suffix.lower() != ".pdf":
            raise PdfSafetyError("Only .pdf files are supported.")
        size = path.stat().st_size
        if size <= 0:
            raise PdfSafetyError("The selected file is empty.")
        if size > self.MAX_PDF_SIZE_BYTES:
            max_mb = self.MAX_PDF_SIZE_BYTES // (1024 * 1024)
            raise PdfSafetyError(f"The selected PDF is larger than the {max_mb} MB safety limit.")
        with path.open("rb") as file:
            header = file.read(1024)
        if b"%PDF-" not in header:
            raise PdfSafetyError("The selected file does not look like a valid PDF.")
        return path

    def _validate_document_pages(self, document):
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            if (
                page.rect.width <= 0
                or page.rect.height <= 0
                or page.rect.width > self.MAX_PAGE_DIMENSION_POINTS
                or page.rect.height > self.MAX_PAGE_DIMENSION_POINTS
            ):
                raise PdfSafetyError(
                    f"Page {page_index + 1} is outside the supported page size limits."
                )

    def _show_error(self, title, public_message, exception):
        detail = str(exception) if isinstance(exception, PdfSafetyError) else "The file could not be processed safely."
        QMessageBox.critical(self, title, f"{public_message}\n\n{detail}")

    def close_document(self):
        if self.document is not None:
            self.document.close()
        self.document = None
        self._teardown_continuous_layout()

    # ------------------------------------------------------------------
    # Page Rendering
    # ------------------------------------------------------------------

    def render_page(self):
        """Schedule a page render (debounced for rapid calls)."""
        self._render_timer.start()

    def _do_render(self):
        """Perform the actual page render (called by debounce timer)."""
        _t = _perf_start()
        if self.document is None or getattr(self.document, "is_closed", False):
            if self.document is None:
                self._teardown_continuous_layout()
                # Show empty state if not already
                if self.scroll_area.widget() is not self.empty_state_widget:
                    self.scroll_area.takeWidget()
                    self.scroll_area.setWidget(self.empty_state_widget)
                    self.scroll_area.setWidgetResizable(True)
                self._update_controls()
            return

        # Switch to page label if showing empty state
        if self.scroll_area.widget() is not self.page_label or self._continuous_mode:
            pass  # handled below

        if self._continuous_mode:
            self._render_continuous()
        else:
            self._render_single_page()
        _perf_end(_t, f"_do_render page={self.current_page} zoom={self.current_render_zoom:.2f}")

    def _render_single_page(self):
        """Render a single page in the scroll area at display resolution."""
        if self._continuous_container is not None:
            self._teardown_continuous_layout()
        try:
            page = self.document.load_page(self.current_page)
            zoom = self._effective_zoom(page)
            self.current_render_zoom = zoom
            self._validate_render_size(page, zoom)

            # HiDPI-aware rendering: render at device pixel ratio for crisp output
            dpr = self.devicePixelRatioF() if hasattr(self, 'devicePixelRatioF') else 1.0
            render_zoom = zoom * dpr
            matrix = fitz.Matrix(render_zoom, render_zoom)
            highlight_rects = self._active_highlight_rects()

            show_annots = hasattr(self, "show_annots_action") and self.show_annots_action.isChecked()

            pixmap = page.get_pixmap(matrix=matrix, alpha=False, annots=show_annots)
            image = QImage(
                pixmap.samples,
                pixmap.width,
                pixmap.height,
                pixmap.stride,
                QImage.Format_RGB888,
            )
            if highlight_rects:
                self._paint_highlights(image, page, highlight_rects, render_zoom)
            if self.selected_rects:
                self._paint_selection(image, page, self.selected_rects, render_zoom)
            self._paint_form_highlights(image, page, self.current_page, render_zoom)
        except Exception as exc:
            self._show_error("Render Error", "Unable to render this page.", exc)
            return

        # Switch to page_label widget
        if self.scroll_area.widget() is not self.page_label:
            self.scroll_area.takeWidget()
            self.scroll_area.setWidget(self.page_label)
            self.scroll_area.setWidgetResizable(False)

        qp = QPixmap.fromImage(image)
        qp.setDevicePixelRatio(dpr)
        self.page_label.setPixmap(qp)
        # Drop overlay widgets left over from continuous mode, then attach
        # this page's native form controls.
        current_form = self._form_for_current()
        if current_form is not None:
            current_form.detach_all()
        self._attach_form_overlays(self.page_label, self.current_page, zoom)
        edit = self._edit_for_current()
        if edit is not None:
            edit.attach_page(self.page_label, self.current_page, zoom)
        self.page_label.adjustSize()
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(self.current_page + 1)
        self.page_spin.blockSignals(False)
        self._update_controls()

    def _render_continuous(self):
        """Render the continuous view around the current scroll position.

        The layout always holds one sized widget per page, so the scroll
        range spans the whole document. Pixmaps are created lazily for the
        viewport plus overscan and released once they leave the cache
        window, which keeps memory bounded for very long documents.
        """
        if self.document is None or getattr(self.document, "is_closed", False):
            return
        page_count = self.document.page_count
        if page_count <= 0:
            return

        page0 = self.document.load_page(0)
        zoom = self._effective_zoom(page0)
        self.current_render_zoom = zoom

        if self._continuous_layout_needs_rebuild(zoom, page_count):
            self._build_continuous_layout(zoom, page_count)
        else:
            self._show_continuous_container()

        # An explicit render (search, annotations, theme, zoom) invalidates
        # cached pixmaps. Plain scrolling goes through the scroll handler and
        # does not, so the cache survives normal reading.
        self._release_all_continuous_pixmaps()
        self._render_visible_continuous()
        self._update_page_controls()

    # -- continuous layout -------------------------------------------------

    def _continuous_layout_needs_rebuild(self, zoom: float, page_count: int) -> bool:
        if self._continuous_container is None or self._continuous_layout is None:
            return True
        if self._continuous_layout_document is not self.document:
            return True
        if len(self._continuous_pages) != page_count:
            return True
        if self._continuous_layout_zoom is None:
            return True
        return abs(self._continuous_layout_zoom - zoom) > 1e-4

    def _show_continuous_container(self):
        if self._continuous_container is None:
            return
        if self.scroll_area.widget() is not self._continuous_container:
            self.scroll_area.takeWidget()
            self.scroll_area.setWidget(self._continuous_container)
            self.scroll_area.setWidgetResizable(True)

    def _build_continuous_layout(self, zoom: float, page_count: int):
        """Create a correctly sized placeholder for every page."""
        # Keep the reader on the same page across zoom/theme rebuilds even
        # though the scrollbar briefly collapses while the widget is swapped.
        target_page = max(0, min(self.current_page, page_count - 1))
        self._teardown_continuous_layout()

        container = QWidget()
        container.setObjectName("ContinuousDocument")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            self.CONTINUOUS_PAGE_MARGIN,
            self.CONTINUOUS_PAGE_MARGIN,
            self.CONTINUOUS_PAGE_MARGIN,
            self.CONTINUOUS_PAGE_MARGIN,
        )
        layout.setSpacing(self.CONTINUOUS_PAGE_GAP)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        pages: list[QLabel] = []
        for page_index in range(page_count):
            page = self.document.load_page(page_index)
            width = max(1, int(round(page.rect.width * zoom)))
            height = max(1, int(round(page.rect.height * zoom)))
            label = QLabel()
            label.setObjectName("ContinuousPage")
            label.setAlignment(Qt.AlignCenter)
            # +2 accounts for the 1 px border drawn by the stylesheet.
            label.setFixedSize(width + 2, height + 2)
            layout.addWidget(label, 0, Qt.AlignHCenter)
            pages.append(label)

        self._continuous_container = container
        self._continuous_layout = layout
        self._continuous_pages = pages
        self._continuous_rendered.clear()
        self._continuous_layout_zoom = zoom
        self._continuous_layout_document = self.document

        # Pin the target page before the widget is attached: scrollbar range
        # changes during the swap must not reset the reader's position.
        self.current_page = target_page
        self._pending_scroll_page = target_page
        self._show_continuous_container()
        layout.activate()
        container.adjustSize()
        self._scroll_to_page(target_page)

    def _teardown_continuous_layout(self):
        self._continuous_render_timer.stop()
        self._pending_scroll_page = None
        form = self._form_for_current()
        if form is not None:
            form.detach_all()
        edit = self._edit_for_current()
        if edit is not None:
            edit.detach_all()
        # Clear the page list before detaching the widget so scroll events
        # raised by the swap are ignored.
        self._continuous_pages = []
        self._continuous_rendered.clear()
        if self._continuous_container is not None:
            if self.scroll_area.widget() is self._continuous_container:
                self.scroll_area.takeWidget()
            self._continuous_container.setParent(None)
            self._continuous_container.deleteLater()
        self._continuous_container = None
        self._continuous_layout = None
        self._continuous_layout_zoom = None
        self._continuous_layout_document = None

    # -- lazy rendering ----------------------------------------------------

    def _release_all_continuous_pixmaps(self):
        for index in list(self._continuous_rendered):
            self._release_pixmap(index)

    def _release_pixmap(self, page_index: int):
        form = self._form_for_current()
        if form is not None and 0 <= page_index < len(self._continuous_pages):
            form.detach_page(self._continuous_pages[page_index])
        edit = self._edit_for_current()
        if edit is not None and 0 <= page_index < len(self._continuous_pages):
            edit.detach_page(self._continuous_pages[page_index])
        if 0 <= page_index < len(self._continuous_pages):
            self._continuous_pages[page_index].clear()
        self._continuous_rendered.discard(page_index)

    def _continuous_visible_range(self) -> tuple[int, int]:
        """Return the first and last page index intersecting the viewport."""
        if not self._continuous_pages:
            return (0, -1)
        scrollbar = self.scroll_area.verticalScrollBar()
        top = scrollbar.value()
        bottom = top + max(1, self.scroll_area.viewport().height())
        first = None
        last = None
        for index, label in enumerate(self._continuous_pages):
            label_top = label.y()
            label_bottom = label_top + label.height()
            if label_bottom > top and first is None:
                first = index
            if label_top < bottom:
                last = index
            elif last is not None:
                break
        if first is None:
            first = len(self._continuous_pages) - 1
        if last is None:
            last = first
        return (first, last)

    def _render_visible_continuous(self):
        """Render the viewport and overscan; release pixmaps outside cache."""
        if not self._continuous_mode:
            return
        if self.document is None or getattr(self.document, "is_closed", False):
            return
        if not self._continuous_pages:
            return

        first, last = self._continuous_visible_range()
        if last < first:
            return

        keep_start = max(0, first - self.CONTINUOUS_CACHE)
        keep_end = min(len(self._continuous_pages), last + self.CONTINUOUS_CACHE + 1)
        for index in list(self._continuous_rendered):
            if index < keep_start or index >= keep_end:
                self._release_pixmap(index)

        render_start = max(0, first - self.CONTINUOUS_OVERSCAN)
        render_end = min(len(self._continuous_pages), last + self.CONTINUOUS_OVERSCAN + 1)
        for page_index in range(render_start, render_end):
            if page_index not in self._continuous_rendered:
                self._render_continuous_page(page_index)

    def _render_continuous_page(self, page_index: int):
        if page_index < 0 or page_index >= len(self._continuous_pages):
            return
        try:
            page = self.document.load_page(page_index)
            dpr = self.devicePixelRatioF() if hasattr(self, "devicePixelRatioF") else 1.0
            layout_zoom = self._continuous_layout_zoom or self.current_render_zoom
            render_zoom = layout_zoom * dpr
            self._validate_render_size(page, render_zoom)
            show_annots = (
                hasattr(self, "show_annots_action")
                and self.show_annots_action.isChecked()
            )
            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(render_zoom, render_zoom),
                alpha=False,
                annots=show_annots,
            )
            image = QImage(
                pixmap.samples,
                pixmap.width,
                pixmap.height,
                pixmap.stride,
                QImage.Format_RGB888,
            )
            self._paint_form_highlights(image, page, page_index, render_zoom)
            if page_index == self.current_page:
                highlight_rects = self._active_highlight_rects()
                if highlight_rects:
                    self._paint_highlights(image, page, highlight_rects, render_zoom)
            qp = QPixmap.fromImage(image)
            qp.setDevicePixelRatio(dpr)
            self._continuous_pages[page_index].setPixmap(qp)
            self._continuous_rendered.add(page_index)
            self._attach_form_overlays(
                self._continuous_pages[page_index], page_index, layout_zoom
            )
            edit = self._edit_for_current()
            if edit is not None:
                edit.attach_page(
                    self._continuous_pages[page_index], page_index, layout_zoom
                )
        except Exception:
            # Leave the placeholder in place — one unrenderable page must not
            # take the rest of the document down with it.
            return  # nosec — unrenderable pages are skipped, not fatal

    # -- scroll position ---------------------------------------------------

    def _on_continuous_scrolled(self, value: int):
        if not self._continuous_mode:
            return
        if (
            self.document is None
            or getattr(self.document, "is_closed", False)
            or not self._continuous_pages
        ):
            return
        if self._continuous_syncing_scroll or self._pending_scroll_page is not None:
            return

        scrollbar = self.scroll_area.verticalScrollBar()
        first, _last = self._continuous_visible_range()
        if scrollbar.maximum() > 0 and scrollbar.value() >= scrollbar.maximum() - 1:
            first = len(self._continuous_pages) - 1
        if first != self.current_page:
            self.current_page = first
            self.page_spin.blockSignals(True)
            self.page_spin.setValue(first + 1)
            self.page_spin.blockSignals(False)
            self._update_controls()
        self._continuous_render_timer.start()

    def _scroll_to_page(self, page_index: int):
        """Scroll so the requested page sits at the top of the viewport."""
        if not self._continuous_pages:
            return
        page_index = max(0, min(page_index, len(self._continuous_pages) - 1))
        self.current_page = page_index
        self._pending_scroll_page = page_index
        self._apply_pending_scroll()
        # The scroll range can still be settling right after a layout rebuild;
        # retry once on the next event-loop turn.
        QTimer.singleShot(0, self._apply_pending_scroll)

    def _apply_pending_scroll(self):
        page_index = self._pending_scroll_page
        if self.document is None or getattr(self.document, "is_closed", False):
            self._pending_scroll_page = None
            return
        if page_index is None or not self._continuous_pages:
            return
        if page_index >= len(self._continuous_pages):
            self._pending_scroll_page = None
            return
        target = self._continuous_pages[page_index].y()
        scrollbar = self.scroll_area.verticalScrollBar()
        self._continuous_syncing_scroll = True
        try:
            scrollbar.setValue(target)
        finally:
            self._continuous_syncing_scroll = False
        if scrollbar.value() == target:
            self._pending_scroll_page = None
        # The scroll may have settled after the previous render pass (layout
        # rebuilds), so make sure the pages now on screen get pixmaps.
        self._continuous_render_timer.start()
        self._update_page_controls()

    def _update_page_controls(self):
        if self.document is None or getattr(self.document, "is_closed", False):
            return
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(self.current_page + 1)
        self.page_spin.blockSignals(False)
        self._update_controls()

    def _effective_zoom(self, page):
        if not self.fit_to_window:
            return self.zoom
        vp_w = max(1, self.scroll_area.viewport().width() - 24)
        vp_h = max(1, self.scroll_area.viewport().height() - 40)
        pw = max(1, page.rect.width)
        ph = max(1, page.rect.height)
        zoom = min(vp_w / pw, vp_h / ph)
        return max(self.MIN_ZOOM, min(self.MAX_ZOOM, zoom))

    def _validate_render_size(self, page, zoom):
        pixels = int(page.rect.width * zoom) * int(page.rect.height * zoom)
        if pixels > self.MAX_RENDER_PIXELS:
            raise PdfSafetyError("This page is too large to render at the current zoom level.")

    def _active_highlight_rects(self):
        if self.current_result_index < 0 or not self.search_results:
            return []
        result = self.search_results[self.current_result_index]
        if result["page"] != self.current_page:
            return []
        return result["rects"]

    def _paint_highlights(self, image, page, rects, zoom):
        painter = QPainter(image)
        painter.setCompositionMode(QPainter.CompositionMode_Multiply)
        painter.setBrush(QColor(255, 225, 60, 170))
        painter.setPen(Qt.NoPen)
        for rect in rects:
            x = int((rect.x0 - page.rect.x0) * zoom)
            y = int((rect.y0 - page.rect.y0) * zoom)
            width = max(1, int(rect.width * zoom))
            height = max(1, int(rect.height * zoom))
            painter.drawRect(x, y, width, height)
        painter.end()

    def _paint_selection(self, image, page, rects, zoom):
        painter = QPainter(image)
        painter.setCompositionMode(QPainter.CompositionMode_Multiply)
        painter.setBrush(QColor(96, 165, 250, 130))
        painter.setPen(Qt.NoPen)
        for rect in rects:
            x = int((rect.x0 - page.rect.x0) * zoom)
            y = int((rect.y0 - page.rect.y0) * zoom)
            width = max(1, int(rect.width * zoom))
            height = max(1, int(rect.height * zoom))
            painter.drawRect(x, y, width, height)
        painter.end()

    def select_text_in_rect(self, widget_rect):
        if self.document is None or widget_rect.width() < 3 or widget_rect.height() < 3:
            self.clear_text_selection()
            return

        page = self.document.load_page(self.current_page)
        selection = self._widget_rect_to_page_rect(widget_rect, page)
        words = self._words_in_rect(page, selection)
        used_ocr = False
        if not words:
            words = self._ocr_words_in_rect(page, selection)
            used_ocr = bool(words)
        self.selected_text = self._text_from_words(words)
        self.selected_rects = [fitz.Rect(word[:4]) for word in words]
        if self.selected_text:
            mode = "OCR text" if used_ocr else "text"
            self.statusBar().showMessage(f"Selected {mode}. Press Ctrl+C or click Copy.", 5000)
        else:
            self.statusBar().showMessage("No selectable text found in that area", 4000)
        self.render_page()

    def _widget_rect_to_page_rect(self, widget_rect, page):
        zoom = max(self.MIN_ZOOM, self.current_render_zoom)
        x0 = page.rect.x0 + widget_rect.left() / zoom
        y0 = page.rect.y0 + widget_rect.top() / zoom
        x1 = page.rect.x0 + widget_rect.right() / zoom
        y1 = page.rect.y0 + widget_rect.bottom() / zoom
        return fitz.Rect(x0, y0, x1, y1).normalize()

    def _words_in_rect(self, page, selection):
        words = page.get_text("words")
        selected_words = []
        for word in words:
            rect = fitz.Rect(word[:4])
            if rect.intersects(selection):
                selected_words.append(word)
        return sorted(selected_words, key=lambda item: (item[5], item[6], item[7]))

    def _ocr_words_in_rect(self, page, selection):
        textpage = self._get_ocr_textpage(page)
        if textpage is None:
            return []
        try:
            words = page.get_text("words", textpage=textpage)
        except Exception:
            return []
        selected_words = []
        for word in words:
            rect = fitz.Rect(word[:4])
            if rect.intersects(selection):
                selected_words.append(word)
        return sorted(selected_words, key=lambda item: (item[5], item[6], item[7]))

    def _get_ocr_textpage(self, page):
        if self.current_page in self.ocr_text_pages:
            return self.ocr_text_pages[self.current_page]
        try:
            self.statusBar().showMessage("Running OCR on this page...", 3000)
            QApplication.processEvents()
            textpage = page.get_textpage_ocr(language="eng", dpi=150, full=True)
        except Exception as exc:
            if not self.ocr_warning_shown:
                self.ocr_warning_shown = True
                QMessageBox.information(
                    self,
                    "OCR Not Available",
                    "This PDF page appears to need OCR, but OCR is not available on this computer.\n\n"
                    "PyMuPDF uses Tesseract OCR data for this feature. Install Tesseract OCR and English "
                    "language data, then reopen the app to select text from scanned/image-only PDFs.",
                )
            return None
        self.ocr_text_pages[self.current_page] = textpage
        self.ocr_text_pages.move_to_end(self.current_page)
        while len(self.ocr_text_pages) > self.MAX_OCR_CACHE_PAGES:
            self.ocr_text_pages.popitem(last=False)
        return textpage

    def _text_from_words(self, words):
        if not words:
            return ""
        lines = []
        current_key = None
        current_words = []
        for word in words:
            key = (word[5], word[6])
            if current_key is not None and key != current_key:
                lines.append(" ".join(current_words))
                current_words = []
            current_key = key
            current_words.append(word[4])
        if current_words:
            lines.append(" ".join(current_words))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Text Selection & Copy
    # ------------------------------------------------------------------

    def copy_selected_text(self):
        if not self.selected_text:
            self.statusBar().showMessage("Drag over text on the page first, then copy.", 4000)
            return
        QApplication.clipboard().setText(self.selected_text)
        self.statusBar().showMessage("Copied selected text", 3000)

    def clear_text_selection(self, render=True):
        self.selected_text = ""
        self.selected_rects = []
        self.page_label.clear_drag_selection()
        if render and self.document is not None:
            self.render_page()

    def _toggle_annotations_visible(self, visible):
        if self.document is not None:
            self.render_page()

    def _toggle_continuous_mode(self, checked):
        self._continuous_mode = checked
        if hasattr(self, "_continuous_menu_action"):
            self._continuous_menu_action.setChecked(checked)
        if not checked:
            self._teardown_continuous_layout()
        if self.document is not None:
            self.render_page()

    def _toggle_auto_update_check(self, checked):
        self._auto_update_check = checked
        self.settings.setValue(SETTINGS_AUTO_UPDATE_KEY, checked)

    # ------------------------------------------------------------------
    # Annotations (Highlight / Underline / Strikethrough / Sticky Note)
    # ------------------------------------------------------------------

    def _selected_quads(self):
        """Convert selected_rects to a list of fitz.Quad for annotation API."""
        return [fitz.Quad(r.tl, r.tr, r.bl, r.br) for r in self.selected_rects]

    def _apply_text_annotation(self, annot_method, color, name):
        """Common helper: add an annotation from the current text selection."""
        if not self.selected_rects or self.document is None:
            self.statusBar().showMessage("Select text on the page first, then annotate.", 4000)
            return
        page = self.document.load_page(self.current_page)
        quads = self._selected_quads()
        try:
            annot = annot_method(quads)
            annot.set_colors({"stroke": color})
            annot.set_opacity(0.5)
            annot.update()
        except Exception as exc:
            self.statusBar().showMessage(f"Could not add annotation: {exc}", 5000)
            return
        self._save_document_annotations()
        self.clear_text_selection()
        self.statusBar().showMessage(f"{name} added", 3000)

    def highlight_selection(self):
        self._apply_text_annotation(
            lambda quads: self.document.load_page(self.current_page).add_highlight_annot(quads),
            self.ANNOT_HIGHLIGHT,
            "Highlight",
        )

    def underline_selection(self):
        self._apply_text_annotation(
            lambda quads: self.document.load_page(self.current_page).add_underline_annot(quads),
            self.ANNOT_UNDERLINE,
            "Underline",
        )

    def strikeout_selection(self):
        self._apply_text_annotation(
            lambda quads: self.document.load_page(self.current_page).add_strikeout_annot(quads),
            self.ANNOT_STRIKEOUT,
            "Strikethrough",
        )

    def _toggle_sticky_note_mode(self):
        """Enter or exit sticky-note-placement mode."""
        if self.document is None:
            self.sticky_button.setChecked(False)
            return
        if self.page_label.annotation_mode == "sticky_note":
            self.page_label.clear_annotation_mode()
            self.sticky_button.setChecked(False)
            self.statusBar().showMessage("Sticky note mode cancelled", 3000)
        else:
            self.page_label.set_annotation_mode("sticky_note")
            self.sticky_button.setChecked(True)
            self.statusBar().showMessage("Click on the page to place a sticky note", 5000)

    def _place_sticky_note(self, widget_pos: QPoint):
        """Add a text annotation (sticky note) at the clicked position."""
        if self.document is None:
            return

        # Ask for note text
        text, ok = QInputDialog.getMultiLineText(
            self, "Sticky Note", "Enter note text:",
        )
        if not ok or not text.strip():
            self.sticky_button.setChecked(False)
            return

        # Convert widget position to PDF coordinates
        page = self.document.load_page(self.current_page)
        zoom = max(self.MIN_ZOOM, self.current_render_zoom)
        pdf_x = page.rect.x0 + widget_pos.x() / zoom
        pdf_y = page.rect.y0 + widget_pos.y() / zoom
        point = fitz.Point(pdf_x, pdf_y)

        try:
            annot = page.add_text_annot(point, text.strip(), icon="Note")
            annot.set_opacity(0.85)
            annot.update()
        except Exception as exc:
            self.statusBar().showMessage(f"Could not place sticky note: {exc}", 5000)
            self.sticky_button.setChecked(False)
            return

        self._save_document_annotations()
        self.render_page()
        self.sticky_button.setChecked(False)
        self.statusBar().showMessage("Sticky note placed", 3000)

    def _delete_page_annotations(self):
        """Delete all annotations on the current page."""
        if self.document is None:
            return
        page = self.document.load_page(self.current_page)
        annots = list(page.annots())
        if not annots:
            QMessageBox.information(self, "Annotations", "No annotations on this page.")
            return
        reply = QMessageBox.question(
            self, "Delete Annotations",
            f"Delete all {len(annots)} annotation(s) on this page?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        for annot in annots:
            page.delete_annot(annot)
        self._save_document_annotations()
        self.render_page()
        self.statusBar().showMessage(f"Deleted {len(annots)} annotation(s)", 3000)

    def _delete_all_annotations(self):
        """Delete all annotations in the entire document."""
        if self.document is None:
            return
        # Count first, ask for confirmation, then delete
        total = 0
        for page_index in range(self.document.page_count):
            page = self.document.load_page(page_index)
            total += len(list(page.annots()))
        if total == 0:
            QMessageBox.information(self, "Annotations", "No annotations in this document.")
            return
        reply = QMessageBox.question(
            self, "Delete Annotations",
            f"Delete all {total} annotation(s) in the entire document?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        # Now actually delete
        for page_index in range(self.document.page_count):
            page = self.document.load_page(page_index)
            for annot in list(page.annots()):
                page.delete_annot(annot)
        self._save_document_annotations()
        self.render_page()
        self.statusBar().showMessage(f"Deleted {total} annotation(s)", 3000)

    def _toggle_annotations_visible(self, visible):
        self.render_page()
        status = "shown" if visible else "hidden"
        self.statusBar().showMessage(f"Annotations {status}", 3000)

    def _save_document_annotations(self):
        """Save the current document to preserve annotations on disk."""
        if self.current_path is None or self.document is None:
            return
        try:
            self.document.save(self.current_path, incremental=True, encryption=0)
        except Exception:
            try:
                self.document.save(self.current_path, garbage=1, deflate=True)
            except Exception as exc:
                self.statusBar().showMessage(f"Could not save annotations: {exc}", 5000)

    def _save_document(self) -> bool:
        """Explicit save via File > Save (form values, edits, annotations)."""
        if self.current_path is None or self.document is None:
            self.statusBar().showMessage("No document open", 3000)
            return False
        edit = self._edit_for_current()
        if edit is not None:
            edit._finish_text_edit()
        if not self._confirm_save_signed():
            return False
        form = self._form_for_current()
        try:
            if form is not None and form.dirty:
                self._write_dirty_form_values(form)
            eo.save_document(self.document, self.current_path)
        except Exception as exc:
            self.statusBar().showMessage(f"Save failed: {exc}", 6000)
            return False
        if edit is not None:
            edit.mark_saved()
        if form is not None:
            form.dirty = False
            form._dirty_names = set()
            if getattr(form, "_state_store", None) is not None:
                form._state_store.clear(self.current_path)
        self._update_window_title_dirty()
        self._refresh_tab_dirty(self.current_tab_id)
        self._update_navigator_item_for_tab(self.current_tab_id)
        self.statusBar().showMessage("Document saved", 3000)
        return True

    def _save_document_as(self) -> bool:
        """Save As — atomic full save to a new path, updating the tab."""
        if self.document is None or self.current_path is None:
            self.statusBar().showMessage("No document open", 3000)
            return False
        edit = self._edit_for_current()
        if edit is not None:
            edit._finish_text_edit()
        default_name = f"{Path(self.current_path).stem}_completed.pdf"
        new_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save As",
            str(Path(self.current_path).with_name(default_name)),
            "PDF files (*.pdf)",
        )
        if not new_path:
            return False
        if not new_path.lower().endswith(".pdf"):
            new_path += ".pdf"
        form = self._form_for_current()
        try:
            if form is not None:
                self._write_dirty_form_values(form)
            eo.save_document(self.document, new_path)
        except Exception as exc:
            self.statusBar().showMessage(f"Save As failed: {exc}", 6000)
            return False
        if edit is not None:
            edit.mark_saved()
            edit.path = new_path
        if form is not None:
            form.dirty = False
            form._dirty_names = set()
            if getattr(form, "_state_store", None) is not None:
                form._state_store.clear(new_path)
        self.current_path = new_path
        if self.current_tab_id in self.tabs:
            self.tabs[self.current_tab_id].path = new_path
            self.tabs[self.current_tab_id].name = Path(new_path).name
        self._add_recent_file(new_path)
        self._update_window_title_dirty()
        self._refresh_tab_dirty(self.current_tab_id)
        self.statusBar().showMessage(f"Saved as {Path(new_path).name}", 4000)
        return True

    def _write_dirty_form_values(self, form):
        for name in form._dirty_names:
            field = form._by_name.get(name)
            if field is None or not field.is_editable():
                continue
            try:
                _ff.set_field_value(self.document, field, form.current_value(field))
            except Exception:  # nosec B112
                continue

    # ------------------------------------------------------------------
    # AcroForm — Phase 2 (v1.3.0 / 1.3.1 / 1.3.2)
    # ------------------------------------------------------------------

    def _init_form(self):
        """Build the FormController for the current tab if the doc has fields."""
        if self.current_tab_id is None or self.document is None or self.current_path is None:
            return None
        controllers = getattr(self, "_form_controllers", {})
        stale = controllers.pop(self.current_tab_id, None)
        if stale is not None:
            stale.detach_all()
        controller = _FormController(self, self.current_tab_id)
        controller.load(self.document, self.current_path)
        controller.readonly = not eo.document_allows_editing(
            self.document, encrypted=self._current_document_encrypted()
        )
        controllers[self.current_tab_id] = controller
        count = len(controller.fields)
        if controller.readonly and count:
            self.statusBar().showMessage(
                "This document is read-only; form fields are displayed but cannot be edited.",
                7000,
            )
        if count and _ff.has_form_fields(self.document):
            self._mark_recent_form_doc(self.current_path)
            self.statusBar().showMessage(
                f"Form detected — {len(controller.editable_fields)} fillable field(s). "
                "Click a field to complete it.",
                7000,
            )
        self._rebuild_navigator()
        self._update_form_menu_state()
        return controller

    def _form_for_current(self):
        if self.current_tab_id is None:
            return None
        return getattr(self, "_form_controllers", {}).get(self.current_tab_id)

    def _drop_form_controller(self, tab_id):
        controller = getattr(self, "_form_controllers", {}).pop(tab_id, None)
        if controller is not None:
            controller.detach_all()

    def _on_form_dirty(self, tab_id):
        self._update_window_title_dirty()
        self._update_form_menu_state()
        self._update_navigator_item_for_tab(tab_id)
        self._refresh_tab_dirty(tab_id)

    def _update_window_title_dirty(self):
        if self.current_path:
            base = f"{self.APP_NAME} - {Path(self.current_path).name}"
        else:
            base = self.APP_NAME
        form = self._form_for_current()
        edit = self._edit_for_current()
        dirty = bool(
            (form is not None and form.dirty)
            or (edit is not None and edit.is_dirty())
        )
        self.setWindowTitle(("● " if dirty else "") + base)

    def _on_form_focus(self, field):
        if field.validation_message:
            self.statusBar().showMessage(field.validation_message, 6000)
        else:
            hint = field.display_name()
            if field.detected_type:
                hint += f" ({field.detected_type}{' inferred' if field.is_inferred else ''})"
            if field.required:
                hint += " [Required]"
            self.statusBar().showMessage(hint, 6000)
        self._select_navigator_field(field)

    def _on_form_validation(self, field, message):
        if message:
            self.statusBar().showMessage(message, 6000)

    # -- highlight painting ------------------------------------------------

    def _paint_form_highlights(self, image, page, page_index, zoom):
        form = self._form_for_current()
        if form is None or not form.fields:
            return
        painter = QPainter(image)
        try:
            for field in form.fields:
                if field.page_index != page_index:
                    continue
                self._paint_field_highlight(painter, field, page, zoom)
        finally:
            painter.end()

    def _paint_field_highlight(self, painter, field, page, zoom):
        if field.field_type == _ff.FieldType.RADIO:
            for opt in field.option_rects:
                x = int((opt[0] - page.rect.x0) * zoom)
                y = int((opt[1] - page.rect.y0) * zoom)
                w = int((opt[2] - opt[0]) * zoom)
                h = int((opt[3] - opt[1]) * zoom)
                if w > 0 and h > 0:
                    painter.setPen(QColor(*_FORM_FILLABLE_BORDER))
                    painter.setBrush(QColor(*_FORM_FILLABLE_FILL))
                    painter.drawRect(x, y, w, h)
            return
        rx = field.rect
        x = int((rx[0] - page.rect.x0) * zoom)
        y = int((rx[1] - page.rect.y0) * zoom)
        w = int((rx[2] - rx[0]) * zoom)
        h = int((rx[3] - rx[1]) * zoom)
        if w <= 0 or h <= 0:
            return
        if field.is_editable():
            painter.setPen(QColor(*_FORM_FILLABLE_BORDER))
            painter.setBrush(QColor(*_FORM_FILLABLE_FILL))
        else:
            painter.setPen(QPen(QColor(*_FORM_READONLY_BORDER), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
        painter.drawRect(x, y, w, h)
        # Required-but-empty (or invalid) fields get an amber outline.
        if field.required and field.is_editable():
            status = self._form_for_current().field_status(field)
            if status in ("required", "invalid"):
                painter.setPen(QColor(*_FORM_REQUIRED_EMPTY_BORDER))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(x - 1, y - 1, w + 2, h + 2)

    def _attach_form_overlays(self, label, page_index, zoom):
        form = self._form_for_current()
        if form is None:
            return
        try:
            page = self.document.load_page(page_index)
        except Exception:
            return
        form.attach_page(label, page_index, zoom, page.rect)

    # -- field navigation -------------------------------------------------

    def _form_next_field(self):
        form = self._form_for_current()
        if form is not None:
            form.focus_next(forward=True)

    def _form_previous_field(self):
        form = self._form_for_current()
        if form is not None:
            form.focus_next(forward=False)

    def _jump_to_page(self, page_index):
        if self.document is None:
            return
        target = max(0, min(page_index, self.document.page_count - 1))
        if target != self.current_page:
            self.current_page = target
            self.clear_text_selection(render=False)
            self._sync_search_result_to_page()
            self.render_page()
        else:
            self.render_page()  # re-attach overlays for this page window

    def _ensure_field_visible(self, field):
        controller = self._form_for_current()
        if controller is None:
            return
        widgets = controller._field_widgets.get(field.name)
        if widgets:
            self.scroll_area.ensureWidgetVisible(widgets[0], 40, 40)

    # -- Form Navigator ----------------------------------------------------

    def _toggle_navigator(self, checked=None):
        if self.navigator_action.isChecked():
            self.form_dock.show()
            self._rebuild_navigator()
        else:
            self.form_dock.hide()

    def _rebuild_navigator(self):
        if not hasattr(self, "form_tree"):
            return
        form = self._form_for_current()
        self.form_tree.clear()
        if form is None or not form.fields:
            self.form_dock.hide()
            if self.navigator_action.isChecked():
                self.navigator_action.setChecked(False)
            return
        pages: dict = {}
        for row in form.navigator_rows():
            pages.setdefault(row["page"], []).append(row)
        for page_index in sorted(pages):
            page_item = QTreeWidgetItem(self.form_tree)
            page_item.setText(0, f"Page {page_index + 1}")
            page_item.setData(0, Qt.UserRole, None)
            for row in pages[page_index]:
                item = QTreeWidgetItem(page_item)
                item.setText(0, row["name"])
                item.setText(1, row["status"].capitalize())
                item.setText(2, row["value"])
                item.setData(0, Qt.UserRole, {"page": page_index, "name": row["name"]})
                if row["validation"]:
                    item.setToolTip(0, f"{row['name']}\n{row['validation']}")
                status = row["status"]
                if status == "required":
                    item.setForeground(0, QColor(245, 158, 11))
                elif status == "invalid":
                    item.setForeground(0, QColor(220, 38, 38))
            page_item.setExpanded(True)
        self.form_tree.expandAll()

    def _update_navigator_item_for_tab(self, tab_id):
        if tab_id == self.current_tab_id:
            self._navigator_rebuild_timer.start()

    def _update_navigator_item(self, field):
        self._navigator_rebuild_timer.start()

    def _select_navigator_field(self, field):
        if not hasattr(self, "form_tree"):
            return
        root = self.form_tree.invisibleRootItem()
        for i in range(root.childCount()):
            page_item = root.child(i)
            for j in range(page_item.childCount()):
                item = page_item.child(j)
                if item.data(0, Qt.UserRole) == {"page": field.page_index, "name": field.name}:
                    self.form_tree.setCurrentItem(item)
                    self.form_tree.scrollToItem(item)
                    return

    def _on_navigator_item_clicked(self, item, _column):
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        form = self._form_for_current()
        if form is None:
            return
        for field in form.fields:
            if field.page_index == data["page"] and field.name == data["name"]:
                form.focus_field(field)
                break

    # -- completion workflow ------------------------------------------------

    def _form_clear_field(self):
        form = self._form_for_current()
        if form is None or not form.fields:
            self.statusBar().showMessage("No form fields open", 3000)
            return
        editable = form.editable_fields
        if 0 <= form._current_index < len(editable):
            form.clear_field(editable[form._current_index])
            self._update_navigator_item_for_tab(self.current_tab_id)
        else:
            self.statusBar().showMessage("Focus a field first, then clear it", 3000)

    def _form_clear_all(self):
        form = self._form_for_current()
        if form is None or not form.fields:
            self.statusBar().showMessage("No form fields open", 3000)
            return
        answer = QMessageBox.question(
            self,
            "Clear Form",
            "Clear all fillable fields? Read-only fields are kept.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            form.clear_form()
            self._update_navigator_item_for_tab(self.current_tab_id)
            self.statusBar().showMessage("Form cleared", 3000)

    def _form_review_complete(self):
        form = self._form_for_current()
        if form is None or not form.fields:
            self.statusBar().showMessage("No form fields open", 3000)
            return
        counts = form.completion_summary()
        problems = [row for row in form.navigator_rows() if row["status"] in ("required", "invalid")]
        lines = [
            f"Fields filled:      {counts['filled']}",
            f"Fields empty:       {counts['empty']}",
            f"Required missing:   {counts['required']}",
            f"Invalid values:     {counts['invalid']}",
        ]
        if problems:
            lines.append("")
            lines.append("Needs attention:")
            for row in problems[:10]:
                tag = "required" if row["status"] == "required" else "invalid"
                lines.append(f"  • {tag} — {row['name']} (page {row['page'] + 1})")
            if len(problems) > 10:
                lines.append(f"  … and {len(problems) - 10} more")
        box = QMessageBox(self)
        box.setWindowTitle("Review & Complete")
        box.setText("\n".join(lines))
        box.setStandardButtons(QMessageBox.Ok | QMessageBox.Save)
        box.button(QMessageBox.Save).setText("Save Form")
        if box.exec() == QMessageBox.Save:
            self._save_document()

    # -- close warning ------------------------------------------------------

    def _confirm_discard_form(self, tab_id) -> bool:
        """If the tab has unsaved form or edit changes, ask. True to proceed."""
        form = getattr(self, "_form_controllers", {}).get(tab_id)
        edit = getattr(self, "_edit_controllers", {}).get(tab_id)
        form_dirty = form is not None and form.dirty
        edit_dirty = edit is not None and edit.is_dirty()
        if not form_dirty and not edit_dirty:
            return True
        tab = self.tabs.get(tab_id)
        answer = QMessageBox.question(
            self,
            "Unsaved Changes",
            "This document has unsaved changes. Save before closing?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if answer == QMessageBox.Save:
            return self._save_tab(tab_id)
        if answer == QMessageBox.Discard:
            path = (
                tab.path
                if tab is not None and tab.path
                else getattr(self, "current_path", None)
            )
            if (
                path
                and form is not None
                and getattr(form, "_state_store", None) is not None
            ):
                form._state_store.clear(path)
            return True
        return False

    # -- recent-file form markers --------------------------------------------

    def _mark_recent_form_doc(self, path):
        try:
            current = set(self.settings.value("formDocs", [], list))
            current.add(str(Path(path).resolve()))
            self.settings.setValue("formDocs", list(current))
        except Exception:  # nosec B110
            pass

    def _is_recent_form_doc(self, path) -> bool:
        try:
            return str(Path(path).resolve()) in set(self.settings.value("formDocs", [], list))
        except Exception:
            return False

    def _update_form_menu_state(self):
        if not self._form_menu:
            return
        form = self._form_for_current()
        has_form = form is not None and bool(form.fields)
        for action in self._form_menu_actions:
            if action is self.navigator_action:
                continue  # navigator toggle always available
            action.setEnabled(has_form)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def previous_page(self):
        if self.document is not None and self.current_page > 0:
            self._go_to_page(self.current_page - 1)

    def next_page(self):
        if self.document is not None and self.current_page < self.document.page_count - 1:
            self._go_to_page(self.current_page + 1)

    def jump_to_page(self, page_number):
        if self.document is None:
            return
        target = max(0, min(page_number - 1, self.document.page_count - 1))
        if target != self.current_page:
            self._go_to_page(target)

    def _go_to_page(self, page_index: int):
        """Move to a page without rebuilding the continuous document."""
        if self.document is None:
            return
        page_index = max(0, min(page_index, self.document.page_count - 1))
        self.current_page = page_index
        self.clear_text_selection(render=False)
        self._sync_search_result_to_page()
        if self._continuous_mode and self._continuous_pages:
            self._scroll_to_page(page_index)
            self._continuous_render_timer.start()
        else:
            self.render_page()

    def _reveal_current_page(self):
        """Make a programmatically selected page visible in continuous mode."""
        if self._continuous_mode and self._continuous_pages:
            self._scroll_to_page(self.current_page)
            self._continuous_render_timer.start()

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------

    def zoom_in(self):
        self.fit_to_window = False
        self.fit_button.blockSignals(True)
        self.fit_button.setChecked(False)
        self.fit_button.blockSignals(False)
        if hasattr(self, "_fit_menu_action"):
            self._fit_menu_action.blockSignals(True)
            self._fit_menu_action.setChecked(False)
            self._fit_menu_action.blockSignals(False)
        self.zoom = min(self.MAX_ZOOM, self.zoom + self.ZOOM_STEP)
        self.clear_text_selection(render=False)
        self.render_page()

    def zoom_out(self):
        self.fit_to_window = False
        self.fit_button.blockSignals(True)
        self.fit_button.setChecked(False)
        self.fit_button.blockSignals(False)
        if hasattr(self, "_fit_menu_action"):
            self._fit_menu_action.blockSignals(True)
            self._fit_menu_action.setChecked(False)
            self._fit_menu_action.blockSignals(False)
        self.zoom = max(self.MIN_ZOOM, self.zoom - self.ZOOM_STEP)
        self.clear_text_selection(render=False)
        self.render_page()

    def _on_fit_toggled(self, checked):
        self.fit_to_window = checked
        if hasattr(self, "_fit_menu_action") and self._fit_menu_action.isChecked() != checked:
            self._fit_menu_action.blockSignals(True)
            self._fit_menu_action.setChecked(checked)
            self._fit_menu_action.blockSignals(False)
        if self.fit_button.isChecked() != checked:
            self.fit_button.blockSignals(True)
            self.fit_button.setChecked(checked)
            self.fit_button.blockSignals(False)
        self.clear_text_selection(render=False)
        self.render_page()

    def set_fit_to_window(self, checked):
        self._on_fit_toggled(checked)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def focus_search(self):
        self.search_input.setFocus()
        self.search_input.selectAll()

    def _search_text_changed(self):
        if not self.search_input.text().strip():
            self.search_text = ""
            self.search_results = []
            self.current_result_index = -1
            self.search_count_label.setText("0")
            self.render_page()

    def search(self):
        if self.document is None:
            return
        needle = self.search_input.text().strip()
        if not needle:
            self._search_text_changed()
            return

        self.search_text = needle
        self.search_results = []
        for page_index in range(self.document.page_count):
            page = self.document.load_page(page_index)
            rects = page.search_for(needle)
            for rect in rects:
                self.search_results.append({"page": page_index, "rects": [rect]})
                if len(self.search_results) >= self.MAX_SEARCH_MATCHES:
                    self.statusBar().showMessage(
                        f"Search stopped after {self.MAX_SEARCH_MATCHES:,} matches.", 5000
                    )
                    break
            if len(self.search_results) >= self.MAX_SEARCH_MATCHES:
                break

        if self.search_results:
            first_on_or_after_page = next(
                (index for index, item in enumerate(self.search_results) if item["page"] >= self.current_page),
                0,
            )
            self.current_result_index = first_on_or_after_page
            self.current_page = self.search_results[self.current_result_index]["page"]
            self.clear_text_selection(render=False)
            self.search_count_label.setText(self._search_count_text())
        else:
            self.current_result_index = -1
            self.search_count_label.setText("0")
            self.statusBar().showMessage("No matches found", 4000)
        self.render_page()

    def next_search_result(self):
        if self.document is None:
            return
        if self.search_input.text().strip() != self.search_text:
            self.search()
            return
        if not self.search_results:
            return
        self.current_result_index = (self.current_result_index + 1) % len(self.search_results)
        self.current_page = self.search_results[self.current_result_index]["page"]
        self.clear_text_selection(render=False)
        self._reveal_current_page()
        self.search_count_label.setText(self._search_count_text())
        self.render_page()

    def previous_search_result(self):
        if self.document is None:
            return
        if self.search_input.text().strip() != self.search_text:
            self.search()
            return
        if not self.search_results:
            return
        self.current_result_index = (self.current_result_index - 1) % len(self.search_results)
        self.current_page = self.search_results[self.current_result_index]["page"]
        self.clear_text_selection(render=False)
        self._reveal_current_page()
        self.search_count_label.setText(self._search_count_text())
        self.render_page()

    def _sync_search_result_to_page(self):
        for index, result in enumerate(self.search_results):
            if result["page"] == self.current_page:
                self.current_result_index = index
                self.search_count_label.setText(self._search_count_text())
                return
        self.current_result_index = -1 if self.search_results else -1
        if self.search_results:
            self.search_count_label.setText(f"{len(self.search_results)}")

    def _search_count_text(self):
        if self.current_result_index < 0:
            return f"{len(self.search_results)}"
        return f"{self.current_result_index + 1}/{len(self.search_results)}"

    # ------------------------------------------------------------------
    # Merge / Split / Compress
    # ------------------------------------------------------------------

    def merge_pdfs(self):
        start_dir = self.settings.value("lastFolder", str(Path.home()))
        file_names, _ = QFileDialog.getOpenFileNames(
            self,
            "Select PDFs to Merge",
            start_dir,
            "PDF Files (*.pdf)",
        )
        if not file_names:
            return
        if len(file_names) < 2:
            QMessageBox.information(self, "Merge PDFs", "Select at least two PDFs to merge.")
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Merged PDF",
            str(Path(file_names[0]).with_name("merged.pdf")),
            "PDF Files (*.pdf)",
        )
        if not output_path:
            return
        if not output_path.lower().endswith(".pdf"):
            output_path += ".pdf"

        merged = fitz.open()
        opened_docs = []
        try:
            for file_name in file_names:
                source = self._safe_open_pdf(file_name)
                opened_docs.append(source)
                merged.insert_pdf(source)
            merged.save(
                output_path,
                garbage=4,
                deflate=True,
                deflate_images=True,
                deflate_fonts=True,
                use_objstms=1,
                compression_effort=9,
            )
        except Exception as exc:
            self._show_error("Merge Failed", "Could not merge the selected PDFs.", exc)
            return
        finally:
            for source in opened_docs:
                source.close()
            merged.close()

        QMessageBox.information(self, "Merge Complete", f"Saved merged PDF:\n\n{output_path}")
        self.statusBar().showMessage("Merged PDFs successfully", 5000)

    def split_pdf(self):
        if self.document is None or self.current_path is None:
            QMessageBox.information(self, "Split PDF", "Open a PDF before using Split.")
            return

        mode, ok = QInputDialog.getItem(
            self,
            "Split PDF",
            "Choose how to split this PDF:",
            ["Every page into separate PDFs", "Extract page range to one PDF"],
            0,
            False,
        )
        if not ok:
            return

        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Choose Output Folder",
            str(Path(self.current_path).parent),
        )
        if not output_dir:
            return

        try:
            if mode == "Every page into separate PDFs":
                if self.document.page_count > self.MAX_SPLIT_PAGES:
                    raise PdfSafetyError(
                        f"Splitting every page is limited to {self.MAX_SPLIT_PAGES} pages at a time."
                    )
                saved_paths = self._split_every_page(Path(output_dir))
                message = f"Saved {len(saved_paths)} PDFs to:\n\n{output_dir}"
            else:
                pages_text, ok = QInputDialog.getText(
                    self,
                    "Extract Pages",
                    "Pages to extract, for example 1-3,5:",
                )
                if not ok or not pages_text.strip():
                    return
                pages = self._parse_page_ranges(pages_text, self.document.page_count)
                saved_path = self._extract_pages(Path(output_dir), pages)
                message = f"Saved extracted pages:\n\n{saved_path}"
        except Exception as exc:
            self._show_error("Split Failed", "Could not split this PDF.", exc)
            return

        QMessageBox.information(self, "Split Complete", message)
        self.statusBar().showMessage("Split PDF successfully", 5000)

    def _split_every_page(self, output_dir):
        base_name = Path(self.current_path).stem
        saved_paths = []
        page_count = self.document.page_count
        show_progress = page_count > 50
        for page_index in range(page_count):
            if show_progress and page_index % 25 == 0:
                self.statusBar().showMessage(
                    f"Splitting... page {page_index + 1}/{page_count}"
                )
                QApplication.processEvents()
            target = output_dir / f"{base_name}_page_{page_index + 1}.pdf"
            new_doc = fitz.open()
            try:
                new_doc.insert_pdf(self.document, from_page=page_index, to_page=page_index)
                new_doc.save(target, garbage=4, deflate=True, use_objstms=1)
            finally:
                new_doc.close()
            saved_paths.append(target)
        return saved_paths

    def _extract_pages(self, output_dir, pages):
        base_name = Path(self.current_path).stem
        suffix = "_".join(str(page + 1) for page in pages[:6])
        if len(pages) > 6:
            suffix += "_etc"
        target = output_dir / f"{base_name}_pages_{suffix}.pdf"
        new_doc = fitz.open()
        try:
            for page_index in pages:
                new_doc.insert_pdf(self.document, from_page=page_index, to_page=page_index)
            new_doc.save(target, garbage=4, deflate=True, use_objstms=1)
        finally:
            new_doc.close()
        return target

    def _parse_page_ranges(self, text, page_count):
        pages = []
        for chunk in text.replace(" ", "").split(","):
            if not chunk:
                continue
            if "-" in chunk:
                start_text, end_text = chunk.split("-", 1)
                start = int(start_text)
                end = int(end_text)
                if start > end:
                    start, end = end, start
                pages.extend(range(start - 1, end))
            else:
                pages.append(int(chunk) - 1)

        unique_pages = []
        seen = set()
        for page in pages:
            if page < 0 or page >= page_count:
                raise ValueError(f"Page {page + 1} is outside the valid range 1-{page_count}.")
            if page not in seen:
                seen.add(page)
                unique_pages.append(page)
        if not unique_pages:
            raise ValueError("No valid pages were selected.")
        return unique_pages

    def compress_pdf(self):
        if self.current_path is None:
            QMessageBox.information(self, "Compress PDF", "Open a PDF before using Compress.")
            return

        input_path = Path(self.current_path)
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Compressed PDF",
            str(input_path.with_name(f"{input_path.stem}_compressed.pdf")),
            "PDF Files (*.pdf)",
        )
        if not output_path:
            return
        if not output_path.lower().endswith(".pdf"):
            output_path += ".pdf"

        try:
            source_size = input_path.stat().st_size
            source = self._safe_open_pdf(self.current_path)
            try:
                source.save(
                    output_path,
                    garbage=4,
                    clean=True,
                    deflate=True,
                    deflate_images=True,
                    deflate_fonts=True,
                    use_objstms=1,
                    compression_effort=9,
                )
            finally:
                source.close()
            output_size = Path(output_path).stat().st_size
        except Exception as exc:
            self._show_error("Compression Failed", "Could not compress this PDF.", exc)
            return

        if output_size >= source_size:
            # Compression not beneficial — remove the output and notify
            try:
                Path(output_path).unlink(missing_ok=True)
            except Exception:
                pass  # nosec B110 — best-effort cleanup
            saved_pct = round((1 - output_size / source_size) * 100, 1) if source_size > 0 else 0
            detail = (
                f"Original: {source_size:,} bytes\n"
                f"Compressed: {output_size:,} bytes ({saved_pct:+.1f}%)\n\n"
                "Compression was not beneficial — output is larger than or equal to the original.\n"
                "No file was saved."
            )
            QMessageBox.information(self, "Compression Not Beneficial", detail)
            self.statusBar().showMessage("Compression not beneficial — no file saved", 5000)
            return

        saved = source_size - output_size
        if source_size > 0:
            percent = saved / source_size * 100
            detail = f"Original: {source_size:,} bytes\nCompressed: {output_size:,} bytes\nSaved: {saved:,} bytes ({percent:.1f}%)"
        else:
            detail = f"Compressed: {output_size:,} bytes"
        QMessageBox.information(self, "Compression Complete", f"Saved compressed PDF:\n\n{output_path}\n\n{detail}")
        self.statusBar().showMessage("Compressed PDF successfully", 5000)

    # ------------------------------------------------------------------
    # Controls State
    # ------------------------------------------------------------------

    def _update_controls(self):
        has_document = bool(
            self.document is not None
            and not getattr(self.document, "is_closed", False)
        )
        can_go_previous = has_document and self.current_page > 0
        can_go_next = has_document and self.current_page < self.document.page_count - 1
        has_matches = bool(self.search_results)
        has_selection = bool(self.selected_text)

        self.prev_button.setEnabled(can_go_previous)
        self.next_button.setEnabled(can_go_next)
        self.page_spin.setEnabled(has_document)
        self.zoom_in_button.setEnabled(has_document)
        self.zoom_out_button.setEnabled(has_document)
        self.fit_button.setEnabled(has_document)
        self.copy_button.setEnabled(has_document and has_selection)
        self.highlight_button.setEnabled(has_document and has_selection)
        self.underline_button.setEnabled(has_document and has_selection)
        self.strike_button.setEnabled(has_document and has_selection)
        self.sticky_button.setEnabled(has_document)
        if hasattr(self, "copy_action"):
            self.copy_action.setEnabled(has_document and has_selection)
        self.search_input.setEnabled(has_document)
        self.search_prev_button.setEnabled(has_document and has_matches)
        self.search_next_button.setEnabled(has_document and has_matches)
        self.semantic_cb.setEnabled(has_document and HAS_LIB_MODULES)
        can_edit = bool(
            has_document
            and self.document is not None
            and eo.document_allows_editing(
                self.document, encrypted=self._current_document_encrypted()
            )
        )
        for edit_button in (
            getattr(self, "fill_button", None),
            getattr(self, "text_button", None),
            getattr(self, "sign_button", None),
            getattr(self, "image_button", None),
        ):
            if edit_button is not None:
                edit_button.setEnabled(can_edit)
        if hasattr(self, "zoom_label"):
            if has_document:
                self.zoom_label.setText(f"{int(round(self.current_render_zoom * 100))}%")
            else:
                self.zoom_label.setText("—")
            self.zoom_label.setEnabled(has_document)
        if getattr(self, "context_toolbar", None) is not None:
            if has_document:
                self.context_toolbar.show()
                controller = self._edit_for_current()
                self._on_edit_selection_changed(
                    controller.selected_object()
                    if controller is not None
                    else None
                )
            else:
                self.context_toolbar.hide()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.fit_to_window and self.document is not None:
            self._render_timer.start()  # Debounced re-render

    def _show_about(self):
        """Professional branded About dialog."""
        dlg = QDialog(self)
        dlg.setWindowTitle(f"About {self.APP_NAME}")
        dlg.setFixedSize(460, 500)
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(10)

        # App name
        name_label = QLabel(f"<h1 style='margin:0;'>{self.APP_NAME}</h1>")
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)

        # Version
        ver_label = QLabel(f"<p style='color:#888; font-size:13px; margin:0;'>"
                           f"Version {__version__} &mdash; <a href='https://github.com/{GITHUB_REPO}/releases' "
                           f"style='color:#89b4fa;'>Release Notes</a></p>")
        ver_label.setOpenExternalLinks(True)
        ver_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(ver_label)

        layout.addSpacing(8)

        # Description
        desc = QLabel(
            "<p style='font-size:13px; line-height:1.6;'>"
            "A local-first, private PDF reader for the desktop. "
            "Built with Python, PySide6, and PyMuPDF. "
            "No cloud uploads. No accounts. No telemetry.</p>"
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        layout.addSpacing(6)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #45475a;")
        layout.addWidget(sep)

        layout.addSpacing(4)

        # Keyboard shortcuts
        shortcuts_title = QLabel("<b style='font-size:12px;'>Keyboard Shortcuts</b>")
        shortcuts_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(shortcuts_title)

        shortcuts = QLabel(self._about_shortcuts_html())
        shortcuts.setAlignment(Qt.AlignCenter)
        layout.addWidget(shortcuts)

        layout.addSpacing(6)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("color: #45475a;")
        layout.addWidget(sep2)

        layout.addSpacing(4)

        # Links
        store_link = QLabel(
            "<p style='font-size:12px; margin:0;'>"
            "<a href='ms-windows-store://pdp/?productid=9MXDVW2645LL' "
            "style='color:#89b4fa;'>Get OpenReader on Microsoft Store</a>"
            "</p>"
        )
        store_link.setOpenExternalLinks(False)
        store_link.linkActivated.connect(self._open_store_listing)
        store_link.setAlignment(Qt.AlignCenter)
        layout.addWidget(store_link)

        links = QLabel(
            f"<p style='font-size:12px; line-height:1.8;'>"
            f"<a href='https://github.com/{GITHUB_REPO}' style='color:#89b4fa;'>GitHub Repository</a>"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;"
            f"<a href='https://github.com/sparshsam' style='color:#89b4fa;'>Sparsh Sam</a>"
            f"</p>"
        )
        links.setOpenExternalLinks(True)
        links.setAlignment(Qt.AlignCenter)
        layout.addWidget(links)

        # Build info
        try:
            build_info = f"Python {platform.python_version()} · PySide6 · {platform.system()} {platform.machine()}"
        except Exception:
            build_info = ""
        if build_info:
            build_label = QLabel(f"<p style='font-size:11px; color:#666; margin:0;'>{build_info}</p>")
            build_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(build_label)

        layout.addStretch()

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(dlg.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        dlg.exec()

    @staticmethod
    def _open_store_listing(_link=None):
        """Open the native Store listing, falling back to its web page."""
        store_uri = QUrl("ms-windows-store://pdp/?productid=9MXDVW2645LL")
        if not QDesktopServices.openUrl(store_uri):
            QDesktopServices.openUrl(QUrl("https://apps.microsoft.com/detail/9MXDVW2645LL"))

    def _set_app_icon(self):
        """Set window icon from bundled .ico file with exhaustive fallback logging."""
        icon_paths = []

        # 1. Frozen (PyInstaller) standard onedir layout: assets/ next to EXE
        if getattr(sys, "frozen", False):
            icon_paths.append(Path(sys.executable).parent / "assets" / "branding" / "pdfreader_by_sparsh.ico")
            # 2. _internal/assets/ layout (some PyInstaller configs)
            icon_paths.append(Path(sys.executable).parent / "_internal" / "assets" / "branding" / "pdfreader_by_sparsh.ico")

        # 3. Dev/source build: icon in repo root assets/
        icon_paths.append(Path(__file__).parent / "assets" / "branding" / "pdfreader_by_sparsh.ico")

        # 4. Frozen with MEIPASS (legacy PyInstaller attribute)
        if getattr(sys, "frozen", False) and hasattr(sys, '_MEIPASS'):
            icon_paths.append(Path(sys._MEIPASS) / "assets" / "branding" / "pdfreader_by_sparsh.ico")

        # Try each path
        for p in icon_paths:
            if p and p.exists():
                qicon = QIcon(str(p))
                self.setWindowIcon(qicon)
                # Also set on the application so taskbar picks it up
                QApplication.setWindowIcon(qicon)
                self._log_update(f"icon_set={p}")
                return

        # All bundled paths failed — search the install directory recursively
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).parent
            try:
                for ico in exe_dir.rglob("pdfreader_by_sparsh.ico"):
                    qicon = QIcon(str(ico))
                    self.setWindowIcon(qicon)
                    QApplication.setWindowIcon(qicon)
                    self._log_update(f"icon_set_recursive={ico}")
                    return
            except Exception:  # nosec B110 — last-resort icon search; real fallback follows
                pass

        # Log failure and fall back to style icon
        self._log_update("icon_not_found: checked paths=" + ";".join(str(p) for p in icon_paths if p))
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        self.setWindowIcon(icon)
        QApplication.setWindowIcon(icon)

    def check_for_updates_silent(self):
        """Silent update check — no user-visible feedback unless update is found."""
        if self._is_store():
            # Updates are managed by the Microsoft Store; don't hit GitHub.
            return
        self._update_nam_silent = QNetworkAccessManager(self)
        self._update_nam_silent.finished.connect(self._on_silent_update_reply)
        url = QUrl(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.UserAgentHeader, "OpenReader/1.0")
        request.setTransferTimeout(15000)
        self._update_nam_silent.get(request)

    def _on_silent_update_reply(self, reply):
        http_status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        network_error = reply.error() != QNetworkReply.NoError
        response_body = bytes(reply.readAll()).decode("utf-8")
        result = self._classify_update_response(
            http_status, network_error, reply.errorString(), response_body, __version__
        )
        reply.deleteLater()
        if result["outcome"] == "update_available":
            skip_version = self.settings.value(SETTINGS_UPDATE_SKIP_KEY, "")
            if should_suppress_silent_notify(result, skip_version):
                self._log_update("update_check=skipped_by_user_preference")
                return
            self.statusBar().showMessage(result["message"], 10000)

    # ------------------------------------------------------------------
    # Drag and drop support
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".pdf"):
                self.open_pdf(path)
                event.acceptProposedAction()
                return
        event.ignore()

    # ------------------------------------------------------------------
    # IPC — Single-instance tab routing
    # ------------------------------------------------------------------

    def _on_ipc_connection(self):
        """Receive file paths from a second instance and open in new tabs."""
        conn = self._ipc_server.nextPendingConnection()
        if conn is None:
            return
        try:
            conn.waitForReadyRead(3000)
            data = bytes(conn.readAll()).decode("utf-8")
            paths = json.loads(data)
            for path in paths:
                if isinstance(path, str) and path.lower().endswith(".pdf"):
                    self.open_pdf(path)
        except Exception as exc:
            self._log_update(f"ipc_handler: {exc}")
        finally:
            conn.disconnectFromServer()
            conn.deleteLater()

    # ------------------------------------------------------------------
    # Auto-update system
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_version(tag):
        match = re.search(r"(\d+)\.(\d+)\.(\d+)", tag)
        if not match:
            return None
        return tuple(int(x) for x in match.groups())

    @staticmethod
    def _is_packaged():
        return getattr(sys, "frozen", False)

    def _is_store(self):
        """True when installed as an MSIX/Store package (updates via Store)."""
        return self._install_source == install_source.STORE_MSIX

    @staticmethod
    def _updater_temp_dir():
        temp_dir = Path(tempfile.gettempdir()) / "PDFReader-Updates"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir

    @classmethod
    def _updater_log_path(cls):
        return cls._updater_temp_dir() / "updater-debug.log"

    @classmethod
    def _log_update(cls, message):
        try:
            with open(cls._updater_log_path(), "a", encoding="utf-8") as f:
                f.write(f"{message}\n")
        except OSError:
            pass


    @staticmethod
    def _classify_update_response(
        http_status, network_error, network_error_string, response_body, current_version_str
    ):
        """Classify an update check response into a structured result dict.

        Returns:
            outcome:  network_error | http_error | json_error | already_latest | update_available
            message:  user-facing status bar message
            latest_tag: str
            latest_version: tuple or None
            data:     parsed JSON dict or None
        """
        result = {
            "outcome": None,
            "message": "",
            "latest_tag": "",
            "latest_version": None,
            "data": None,
        }

        # Network-level failure (connection refused, timeout, host not found)
        if network_error and http_status is None:
            result["outcome"] = "network_error"
            result["message"] = "Could not check for updates — check your internet connection"
            return result

        # HTTP-level error (non-200 status)
        if http_status is not None and http_status != 200:
            if http_status == 403:
                result["outcome"] = "http_error"
                result["message"] = "Update check rate limited by GitHub. Please try again later."
            elif http_status == 404:
                result["outcome"] = "http_error"
                result["message"] = "Latest release not found on GitHub."
            elif http_status == 429:
                result["outcome"] = "http_error"
                result["message"] = "Update check rate limited. Please try again later."
            else:
                result["outcome"] = "http_error"
                result["message"] = (
                    f"Update check failed (HTTP {http_status}). Please try again later."
                )
            return result

        # Network error even though we have HTTP status (unusual)
        if network_error:
            result["outcome"] = "network_error"
            result["message"] = "Could not check for updates — check your internet connection"
            return result

        # Parse JSON response body
        try:
            data = json.loads(response_body)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            result["outcome"] = "json_error"
            result["message"] = "Update check failed — unexpected response from server"
            return result

        latest_tag = data.get("tag_name", "")
        if not latest_tag:
            result["outcome"] = "json_error"
            result["message"] = "Update check failed — release metadata missing"
            return result

        latest_version = PdfReaderWindow._parse_version(latest_tag)
        current_version = PdfReaderWindow._parse_version(current_version_str)

        if latest_version is None:
            result["outcome"] = "json_error"
            result["message"] = (
                f"Update check failed — could not parse release version: {latest_tag}"
            )
            result["latest_tag"] = latest_tag
            return result

        result["latest_tag"] = latest_tag
        result["latest_version"] = latest_version
        result["data"] = data

        # Version comparison
        if current_version is None:
            result["outcome"] = "update_available"
            result["message"] = f"Update available: {latest_tag}"
            return result

        if latest_version <= current_version:
            result["outcome"] = "already_latest"
            ver_str = ".".join(str(x) for x in current_version)
            result["message"] = f"PDFReader is up to date (v{ver_str})"
            return result

        result["outcome"] = "update_available"
        result["message"] = f"Update available: {latest_tag}"
        return result

    def check_for_updates(self):
        if self._is_store():
            dlg = _SoftwareUpdatesDialog(self, mode="store", current_version=__version__)
            dlg.exec()
            if dlg.action == "open_store":
                self._open_store_listing()
            return
        self.update_action.setEnabled(False)
        self.statusBar().showMessage("Checking for updates...")
        url = QUrl(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.UserAgentHeader, "OpenReader/1.0")
        request.setTransferTimeout(15000)
        self._update_nam.get(request)

    def _on_update_check_reply(self, reply):
        self.update_action.setEnabled(True)

        http_status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        network_error = reply.error() != QNetworkReply.NoError
        network_error_string = reply.errorString()
        response_body = bytes(reply.readAll()).decode("utf-8")

        result = self._classify_update_response(
            http_status, network_error, network_error_string, response_body, __version__
        )

        # Structured debug logging
        self._log_update(f"update_check=http_status={http_status}")
        self._log_update(f"update_check=network_error_code={reply.error()}")
        self._log_update(f"update_check=network_error_string={network_error_string}")
        self._log_update(f"update_check=outcome={result['outcome']}")
        self._log_update(f"update_check=latest_tag={result['latest_tag']}")
        self._log_update(f"update_check=current_version={__version__}")
        reply.deleteLater()

        # Record when an interactive check last ran.
        self.settings.setValue(
            SETTINGS_UPDATE_LAST_CHECKED_KEY, datetime.now().isoformat()
        )

        if result["outcome"] in ("network_error", "http_error", "json_error"):
            dlg = _SoftwareUpdatesDialog(self, mode="offline", message=result["message"])
            dlg.exec()
            if dlg.action == "try_again":
                self.check_for_updates()
            return

        if result["outcome"] == "already_latest":
            dlg = _SoftwareUpdatesDialog(self, mode="already_latest", current_version=__version__)
            dlg.exec()
            return

        # Update available
        data = result["data"]
        latest_tag = result["latest_tag"]
        release_url = data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases")
        release_notes = (data.get("body") or "")[:500]
        last_checked = self.settings.value(SETTINGS_UPDATE_LAST_CHECKED_KEY, "")

        dlg = _SoftwareUpdatesDialog(
            self,
            mode="update_available",
            current_version=__version__,
            latest_tag=latest_tag,
            release_url=release_url,
            release_notes=release_notes,
            last_checked=last_checked,
        )
        dlg.exec()

        if dlg.action == "open_releases":
            import webbrowser
            webbrowser.open(release_url)
            self.statusBar().showMessage("Opening releases page in your browser.", 5000)
        elif dlg.action == "skip":
            self.settings.setValue(SETTINGS_UPDATE_SKIP_KEY, latest_tag)
            self._log_update(f"update_check=skipped_version={latest_tag}")
            self.statusBar().showMessage("Update skipped for this version", 3000)

    # Workspace Session Restoration
    # ------------------------------------------------------------------

    def _restore_session(self, force=False):
        if not self._auto_restore and not force:
            return
        # If "Don't ask again" is set, use the stored preference silently
        if self._session_dont_ask:
            if self._auto_restore:
                self._log_update("session_restore: silent auto-restore (don't ask checked)")
                self._do_restore_session()
            else:
                self._log_update("session_restore: skipped (auto-restore disabled, don't ask checked)")
            return
        session = self.settings.value("session", [])
        if not session:
            return
        if not force:
            # Custom dialog with "Don't ask again" checkbox
            from PySide6.QtWidgets import QCheckBox
            msg = QMessageBox(self)
            msg.setWindowTitle("Restore Session")
            msg.setText(
                "You had documents open when you last closed PDFReader.\n"
                "Would you like to restore them?"
            )
            msg.setIcon(QMessageBox.Question)
            cb = QCheckBox("Don't ask again")
            msg.setCheckBox(cb)
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.Yes)
            reply = msg.exec()
            if cb.isChecked():
                self._session_dont_ask = True
                self.settings.setValue("sessionDontAsk", True)
                self._log_update("session_restore: don't ask again checked")
            if reply != QMessageBox.Yes:
                return
        self._do_restore_session()

    def _do_restore_session(self):
        """Restore saved session without prompting."""
        session = self.settings.value("session", [])
        for entry in session:
            path = entry.get("path", "")
            page = entry.get("page", 0)
            if path and Path(path).exists():
                self.open_pdf(path)
                if page > 0 and self.document is not None:
                    self.current_page = min(page, self.document.page_count - 1)
                    self.render_page()

    def _toggle_auto_restore(self, checked):
        self._auto_restore = checked
        self.settings.setValue("autoRestore", checked)

    def closeEvent(self, event):
        # A debounced render must not fire after the docs are closed below.
        self._render_timer.stop()
        # Warn before discarding unsaved form work (Phase 2).
        for tab_id in list(self.tabs.keys()):
            if not self._confirm_discard_form(tab_id):
                event.ignore()
                return
        try:
            self._save_current_state()
        except Exception:
            pass  # best-effort; don't let state save block window close  # nosec B110
        # Save workspace session
        try:
            session = []
            for tab_id, tab in self.tabs.items():
                if tab.path and Path(tab.path).exists():
                    session.append({"path": tab.path, "page": tab.current_page})
            self.settings.setValue("session", session)
        except Exception:
            pass  # best-effort session save  # nosec B110
        # Flush form autosaves + detach overlays before closing docs.
        for tab_id, controller in getattr(self, "_form_controllers", {}).items():
            try:
                controller.detach_all()
            except Exception:  # nosec B110
                pass
        for controller in getattr(self, "_edit_controllers", {}).values():
            try:
                controller.detach_all()
            except Exception:  # nosec B110
                pass
        # Close docs
        for tab_id, tab in self.tabs.items():
            if tab.document is not None:
                try:
                    tab.document.close()
                except Exception:
                    pass  # best-effort document close  # nosec B110
        self.tabs.clear()
        self._form_controllers.clear()
        self._edit_controllers.clear()
        self._edit_tool = None
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Library / Full-Text Search
    # ------------------------------------------------------------------

    def _open_library_dialog(self):
        if not HAS_LIB_MODULES:
            QMessageBox.information(self, "Library", "Library modules not available.")
            return
        dlg = _LibraryDialog(self)
        dlg.exec()

    # ------------------------------------------------------------------
    # PDF Comparison
    # ------------------------------------------------------------------

    def _open_compare_dialog(self):
        if not HAS_LIB_MODULES:
            QMessageBox.information(self, "Compare", "Comparison modules not available.")
            return
        start_dir = self.settings.value("lastFolder", str(Path.home()))
        path_a, _ = QFileDialog.getOpenFileName(self, "Select First PDF (older version)", start_dir, "PDF Files (*.pdf)")
        if not path_a:
            return
        path_b, _ = QFileDialog.getOpenFileName(self, "Select Second PDF (newer version)", str(Path(path_a).parent), "PDF Files (*.pdf)")
        if not path_b:
            return
        dlg = _CompareDialog(path_a, path_b, self)
        dlg.exec()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _open_settings_dialog(self):
        dlg = _SettingsDialog(self)
        dlg.exec()

    def _maybe_prompt_default_app(self):
        """First-launch prompt to set OpenReader as the default PDF reader."""
        if not win_default_apps.is_windows():
            return
        if self.settings.value(SETTINGS_DEFAULT_DONT_ASK_KEY, False, bool):
            return
        if self.settings.value(SETTINGS_DEFAULT_PROMPT_KEY, False, bool):
            return
        is_default, _ = win_default_apps.default_app_owner()
        if is_default:
            return

        box = QMessageBox(self)
        box.setWindowTitle("Default PDF Reader")
        box.setText(
            "OpenReader isn't your default PDF reader.\n\n"
            "Set it as the default to open PDFs from File Explorer with "
            "OpenReader?"
        )
        set_btn = box.addButton("Set as Default", QMessageBox.AcceptRole)
        _ = box.addButton("Maybe Later", QMessageBox.RejectRole)
        dont_ask_btn = box.addButton("Do Not Ask Again", QMessageBox.DestructiveRole)
        box.exec()

        clicked = box.clickedButton()
        if clicked == set_btn:
            self.settings.setValue(SETTINGS_DEFAULT_PROMPT_KEY, True)
            win_default_apps.open_default_apps_settings()
        elif clicked == dont_ask_btn:
            self.settings.setValue(SETTINGS_DEFAULT_PROMPT_KEY, True)
            self.settings.setValue(SETTINGS_DEFAULT_DONT_ASK_KEY, True)
        # "Maybe Later" — no-op; re-prompts on the next launch.

    # ------------------------------------------------------------------
    # Semantic Search (integrated with search bar)
    # ------------------------------------------------------------------

    def search(self):
        if self.document is None:
            return
        needle = self.search_input.text().strip()
        if not needle:
            self._search_text_changed()
            return

        # Semantic search on indexed library
        if HAS_LIB_MODULES and self.semantic_cb.isChecked():
            self._semantic_search(needle)
            return

        # Regular keyword search (existing logic)
        self._keyword_search(needle)

    def _keyword_search(self, needle):
        self.search_text = needle
        self.search_results = []
        page_count = self.document.page_count
        is_large_search = page_count > 100
        if is_large_search:
            self.statusBar().showMessage(f"Searching {page_count} pages...")
            QApplication.processEvents()
        for page_index in range(page_count):
            page = self.document.load_page(page_index)
            rects = page.search_for(needle)
            for rect in rects:
                self.search_results.append({"page": page_index, "rects": [rect]})
                if len(self.search_results) >= self.MAX_SEARCH_MATCHES:
                    self.statusBar().showMessage(
                        f"Search stopped after {self.MAX_SEARCH_MATCHES:,} matches.", 5000
                    )
                    break
            if len(self.search_results) >= self.MAX_SEARCH_MATCHES:
                break
            # Periodic progress update for large PDFs
            if is_large_search and page_index % 50 == 0 and page_index > 0:
                self.statusBar().showMessage(
                    f"Searching... page {page_index + 1}/{page_count}"
                )
                QApplication.processEvents()

        if self.search_results:
            first_on_or_after_page = next(
                (index for index, item in enumerate(self.search_results) if item["page"] >= self.current_page),
                0,
            )
            self.current_result_index = first_on_or_after_page
            self.current_page = self.search_results[self.current_result_index]["page"]
            self.clear_text_selection(render=False)
            self._reveal_current_page()
            self.search_count_label.setText(self._search_count_text())
        else:
            self.current_result_index = -1
            self.search_count_label.setText("0")
            self.statusBar().showMessage("No matches found", 4000)
        self.render_page()

    def _semantic_search(self, needle):
        self.statusBar().showMessage("Searching library...")
        QApplication.processEvents()
        try:
            idx = lib_idx.get_tfidf()
            results = idx.search(needle, max_results=50)
        except Exception as exc:
            self.statusBar().showMessage(f"Search error: {exc}", 5000)
            return

        if not results:
            self.statusBar().showMessage("No semantic matches found. Try keyword search or index some PDFs first.", 5000)
            return

        dlg = _LibrarySearchResultsDialog(results, self)
        if dlg.exec() and dlg.selected_result:
            r = dlg.selected_result
            # Open the PDF at the matching page
            if self.current_path != r.path:
                self.open_pdf(r.path)
            if self.document is not None:
                self.current_page = min(r.page - 1, self.document.page_count - 1)
                self._reveal_current_page()
                self.render_page()
                self.statusBar().showMessage(f"Opened: {r.filename} — page {r.page}", 5000)


# ---------------------------------------------------------------------------
# Settings Dialog
# ---------------------------------------------------------------------------

class _SettingsDialog(QDialog):
    """Application settings — Default Apps (Updates section added in v1.2.7)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(520, 340)

        layout = QVBoxLayout(self)

        # ── Files / Default Apps ──
        files_group = QGroupBox("Files / Default Apps")
        files_layout = QVBoxLayout(files_group)

        self.default_label = QLabel()
        self.default_label.setTextFormat(Qt.RichText)
        self.default_label.setWordWrap(True)
        files_layout.addWidget(self.default_label)

        self.set_default_button = QPushButton("Set OpenReader as Default PDF Reader")
        self.set_default_button.setToolTip(
            "Opens the Windows Default Apps page. "
            "Windows keeps the final confirmation."
        )
        self.set_default_button.clicked.connect(self._open_default_apps)
        files_layout.addWidget(self.set_default_button)

        refresh_button = QPushButton("Refresh Status")
        refresh_button.clicked.connect(self._refresh)
        files_layout.addWidget(refresh_button)

        self.recovery_label = QLabel()
        self.recovery_label.setTextFormat(Qt.RichText)
        self.recovery_label.setWordWrap(True)
        self.recovery_label.setStyleSheet("color: #b04040;")
        files_layout.addWidget(self.recovery_label)

        layout.addWidget(files_group)

        # ── Close ──
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self._refresh()

    @staticmethod
    def _esc(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _refresh(self):
        if not win_default_apps.is_windows():
            self.default_label.setText(
                "<b>Default PDF handling</b> is only configurable on Windows."
            )
            self.set_default_button.setEnabled(False)
            self.recovery_label.hide()
            return

        is_default, progid = win_default_apps.default_app_owner()

        if is_default:
            label = (
                "<b>OpenReader is the default PDF reader.</b><br>"
                "PDFs open in OpenReader from File Explorer."
            )
            self.set_default_button.setText("Open Default Apps")
            self.set_default_button.setToolTip(
                "Open the Windows Default Apps page to manage PDF handling."
            )
        else:
            self.set_default_button.setText("Set OpenReader as Default PDF Reader")
            self.set_default_button.setToolTip(
                "Opens the Windows Default Apps page. "
                "Windows keeps the final confirmation."
            )
            if progid:
                name = win_default_apps.friendly_app_name(progid) or progid
                label = f"<b>Current default for PDF:</b> {self._esc(name)}"
            else:
                label = (
                    "<b>Current default for PDF:</b> not detected — Windows has not "
                    "chosen a handler, or the setting couldn't be read."
                )
        self.default_label.setText(label)

        # Recovery only when OpenReader is neither the default nor registered.
        if is_default or win_default_apps.association_registered():
            self.recovery_label.hide()
        else:
            self.recovery_label.setText(
                "<b>OpenReader's PDF association isn't fully registered.</b> "
                "Reinstall OpenReader, or for Store installs use "
                "Settings → Apps → Installed apps → OpenReader → Advanced options → "
                "Repair."
            )
            self.recovery_label.show()

    def _open_default_apps(self):
        if not win_default_apps.open_default_apps_settings():
            QMessageBox.warning(
                self,
                "Default Apps",
                "Couldn't open the Windows Default Apps page. "
                "Open it manually: Settings → Apps → Default apps.",
            )


# ---------------------------------------------------------------------------
# Software Updates Dialog
# ---------------------------------------------------------------------------

class _SoftwareUpdatesDialog(QDialog):
    """Channel-aware Software Updates dialog (v1.2.7).

    ``mode`` selects the content and buttons:

      - ``store``           — Store-managed message + Open Microsoft Store.
      - ``update_available`` — current → latest, release notes, Open Releases
                               Page / Skip This Version / Later.
      - ``already_latest``   — up-to-date confirmation.
      - ``offline``          — clean error message + Try Again.

    After ``exec()``, ``self.action`` is one of ``open_store``,
    ``open_releases``, ``skip``, ``try_again``, or ``close``.
    """

    def __init__(
        self,
        parent,
        mode,
        *,
        current_version=None,
        latest_tag=None,
        release_url=None,
        release_notes=None,
        message=None,
        last_checked=None,
    ):
        super().__init__(parent)
        self.parent_window = parent
        self.action = "close"
        self.setWindowTitle("Software Updates")
        self.resize(480, 360)

        layout = QVBoxLayout(self)

        heading = QLabel()
        heading.setTextFormat(Qt.RichText)
        heading.setWordWrap(True)
        layout.addWidget(heading)

        body = QLabel()
        body.setTextFormat(Qt.RichText)
        body.setWordWrap(True)
        layout.addWidget(body)

        if mode == "update_available" and release_notes:
            notes = QLabel(f"<pre style='white-space:pre-wrap'>{release_notes}</pre>")
            notes.setTextFormat(Qt.RichText)
            notes.setWordWrap(True)
            layout.addWidget(notes)

        if last_checked:
            stamp = QLabel(f"<i>Last checked: {last_checked}</i>")
            stamp.setTextFormat(Qt.RichText)
            stamp.setWordWrap(True)
            layout.addWidget(stamp)

        buttons = QHBoxLayout()
        buttons.addStretch()
        layout.addLayout(buttons)

        if mode == "store":
            heading.setText("<h3>Updates are managed by the Microsoft Store</h3>")
            body.setText(
                f"You're running OpenReader <b>v{current_version}</b>.<br><br>"
                "Updates for Store installs are delivered automatically by the "
                "Microsoft Store. To check for updates, open the Store listing."
            )
            self._add(buttons, "Open Microsoft Store", "open_store")
            self._add(buttons, "Close", "close")
        elif mode == "update_available":
            heading.setText("<h3>Update Available</h3>")
            body.setText(
                f"You're running <b>v{current_version}</b> &rarr; "
                f"<b>{latest_tag}</b> is available."
            )
            self._add(buttons, "Open Releases Page", "open_releases")
            self._add(buttons, "Skip This Version", "skip")
            self._add(buttons, "Later", "close")
        elif mode == "already_latest":
            heading.setText("<h3>Up to Date</h3>")
            body.setText(
                f"You're already running the latest version of OpenReader "
                f"(v{current_version})."
            )
            self._add(buttons, "Close", "close")
        else:  # offline / error
            heading.setText("<h3>Couldn't Check for Updates</h3>")
            body.setText(message or "An error occurred while checking for updates.")
            self._add(buttons, "Try Again", "try_again")
            self._add(buttons, "Close", "close")

    def _add(self, layout, label, action):
        btn = QPushButton(label)
        btn.clicked.connect(lambda: self._finish(action))
        layout.addWidget(btn)

    def _finish(self, action):
        self.action = action
        self.accept()


# ---------------------------------------------------------------------------
# Library Search Dialog
# ---------------------------------------------------------------------------

class _LibraryDialog(QDialog):
    """Manage indexed folders and search across the library."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("PDF Library Search")
        self.resize(700, 500)

        layout = QVBoxLayout(self)

        # Folder management
        folder_group = QGroupBox("Tracked Folders")
        folder_layout = QVBoxLayout(folder_group)

        self.folder_list = QListWidget()
        self._refresh_folder_list()

        folder_buttons = QHBoxLayout()
        add_btn = QPushButton("Add Folder")
        add_btn.clicked.connect(self._add_folder)
        remove_btn = QPushButton("Remove Folder")
        remove_btn.clicked.connect(self._remove_folder)
        reindex_btn = QPushButton("Re-index All")
        reindex_btn.clicked.connect(self._reindex)
        folder_buttons.addWidget(add_btn)
        folder_buttons.addWidget(remove_btn)
        folder_buttons.addWidget(reindex_btn)
        folder_buttons.addStretch()

        folder_layout.addWidget(self.folder_list)
        folder_layout.addLayout(folder_buttons)
        layout.addWidget(folder_group)

        # Search
        search_group = QGroupBox("Full-Text Search")
        search_layout = QVBoxLayout(search_group)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search across all indexed PDFs...")
        self.search_input.returnPressed.connect(self._do_search)
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._do_search)
        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(search_btn)
        search_layout.addLayout(search_row)

        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self._open_result)
        search_layout.addWidget(self.results_list, 1)

        layout.addWidget(search_group, 1)

        # Close button
        btn_box = QDialogButtonBox(QDialogButtonBox.Close)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _refresh_folder_list(self):
        self.folder_list.clear()
        for folder in lib_idx.get_indexed_folders():
            self.folder_list.addItem(folder)

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder with PDFs")
        if folder:
            self._reindex_folder(folder)
            self._refresh_folder_list()

    def _remove_folder(self):
        current = self.folder_list.currentItem()
        if current:
            folder = current.text()
            count = lib_idx.remove_folder(folder)
            QMessageBox.information(
                self, "Folder Removed",
                f"Removed {count} document(s) from '{Path(folder).name}'.",
            )
            self._refresh_folder_list()

    def _reindex(self):
        folders = lib_idx.get_indexed_folders()
        if not folders:
            QMessageBox.information(self, "Library", "No folders added yet. Add a folder first.")
            return
        lib_idx.clear_index()
        for folder in folders:
            self._reindex_folder(folder)
        self._refresh_folder_list()
        QMessageBox.information(self, "Library", "Re-indexing complete.")

    def _reindex_folder(self, folder):
        progress = QProgressDialog(f"Indexing {Path(folder).name}...", "Cancel", 0, 0, self)
        progress.setWindowTitle("Indexing PDFs")
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        QApplication.processEvents()
        try:
            files, chars = lib_idx.index_folder(folder)
            progress.close()
            if files > 0:
                self.parent_window.statusBar().showMessage(
                    f"Indexed {files} PDF(s) ({chars:,} chars)", 5000
                )
            else:
                self.parent_window.statusBar().showMessage("No PDFs found in that folder", 5000)
        except Exception as exc:
            progress.close()
            QMessageBox.critical(self, "Index Error", f"Could not index folder:\n\n{exc}")

    def _do_search(self):
        query = self.search_input.text().strip()
        if not query:
            return
        self.results_list.clear()
        try:
            results = lib_idx.search_keyword(query, max_results=100)
        except Exception as exc:
            self.parent_window.statusBar().showMessage(f"Search error: {exc}", 5000)
            return
        if not results:
            self.results_list.addItem("(No results)")
            return
        for r in results:
            item = QListWidgetItem(f"{r.filename} — page {r.page}  (score: {r.score:.2f})\n   {r.snippet}")
            item.setData(Qt.UserRole, r)
            item.setToolTip(r.path)
            self.results_list.addItem(item)

    def _open_result(self, item):
        r = item.data(Qt.UserRole)
        if r:
            self.parent_window.open_pdf(r.path)
            if self.parent_window.document is not None:
                self.parent_window.current_page = min(r.page - 1, self.parent_window.document.page_count - 1)
                self.parent_window.render_page()
                self.parent_window.statusBar().showMessage(
                    f"Library: {r.filename} — page {r.page}", 5000
                )
            self.accept()


# ---------------------------------------------------------------------------
# Semantic Search Results Dialog
# ---------------------------------------------------------------------------

class _LibrarySearchResultsDialog(QDialog):
    """Results from semantic search — user picks one to open."""

    def __init__(self, results: list, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.selected_result = None
        self.setWindowTitle("Semantic Search Results")
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        label = QLabel(f"Found {len(results)} semantically similar result(s)")
        layout.addWidget(label)

        self.list_widget = QListWidget()
        for r in results:
            item = QListWidgetItem(f"{r.filename} — page {r.page}  (score: {r.score:.4f})")
            item.setData(Qt.UserRole, r)
            item.setToolTip(r.path)
            self.list_widget.addItem(item)
        self.list_widget.itemDoubleClicked.connect(self._select)
        layout.addWidget(self.list_widget, 1)

        btn_layout = QHBoxLayout()
        open_btn = QPushButton("Open")
        open_btn.clicked.connect(self._select)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(open_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _select(self):
        item = self.list_widget.currentItem()
        if item:
            self.selected_result = item.data(Qt.UserRole)
            self.accept()


# ---------------------------------------------------------------------------
# PDF Comparison Dialog
# ---------------------------------------------------------------------------

class _CompareDialog(QDialog):
    """Show two PDFs side by side with diff highlighting."""

    def __init__(self, path_a, path_b, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Compare: {Path(path_a).name} ↔ {Path(path_b).name}")
        self.resize(1000, 700)

        layout = QVBoxLayout(self)

        # Page navigation
        nav = QHBoxLayout()
        nav.addWidget(QLabel(f"<b>A:</b> {Path(path_a).name}"))
        nav.addStretch()
        nav.addWidget(QLabel(f"<b>B:</b> {Path(path_b).name}"))
        layout.addLayout(nav)

        # Side-by-side panels
        splitter = QSplitter(Qt.Horizontal)

        self.panel_a = QTextEdit()
        self.panel_a.setReadOnly(True)
        self.panel_b = QTextEdit()
        self.panel_b.setReadOnly(True)

        splitter.addWidget(self.panel_a)
        splitter.addWidget(self.panel_b)
        layout.addWidget(splitter, 1)

        # Summary
        self.summary_label = QLabel("Running comparison...")
        layout.addWidget(self.summary_label)

        # Close
        btn_box = QDialogButtonBox(QDialogButtonBox.Close)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        # Run comparison
        QTimer.singleShot(50, lambda: self._run(path_a, path_b))

    def _run(self, path_a, path_b):
        self.summary_label.setText("Extracting text and diffing...")
        QApplication.processEvents()
        try:
            result = pdf_compare.compare_pdfs(path_a, path_b)
        except Exception as exc:
            self.summary_label.setText(f"Comparison failed: {exc}")
            return

        # Render first page
        self._render_page(result, 0)

        # Page navigation
        page_row = QHBoxLayout()
        self.page_label = QLabel(f"Page 1 of {len(result.pages)}")
        prev_btn = QPushButton("← Prev")
        next_btn = QPushButton("Next →")
        page_row.addWidget(prev_btn)
        page_row.addWidget(self.page_label)
        page_row.addWidget(next_btn)
        page_row.addStretch()

        # Insert page nav above the splitter
        nav_layout = self.layout().itemAt(1)  # splitter
        self.layout().insertLayout(1, page_row)

        self._current_diff_page = 0
        self._diff_result = result

        def go_prev():
            if self._current_diff_page > 0:
                self._current_diff_page -= 1
                self._render_page(result, self._current_diff_page)

        def go_next():
            if self._current_diff_page < len(result.pages) - 1:
                self._current_diff_page += 1
                self._render_page(result, self._current_diff_page)

        prev_btn.clicked.connect(go_prev)
        next_btn.clicked.connect(go_next)

        self.summary_label.setText(pdf_compare.generate_diff_summary(result))
        self.summary_label.setWordWrap(True)

    def _render_page(self, result, idx):
        if idx < 0 or idx >= len(result.pages):
            return
        dp = result.pages[idx]
        self.page_label.setText(f"Page {dp.page_a} of {len(result.pages)}")

        html_a = self._segments_to_html(dp.segments_a, "left")
        html_b = self._segments_to_html(dp.segments_b, "right")

        self.panel_a.setHtml(f"<html><body style='font-family:monospace; font-size:11pt;'>\n{html_a}\n</body></html>")
        self.panel_b.setHtml(f"<html><body style='font-family:monospace; font-size:11pt;'>\n{html_b}\n</body></html>")

    @staticmethod
    def _segments_to_html(segments, side):
        parts = []
        for seg in segments:
            text = seg.text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            text = text.replace("\n", "<br>")
            if seg.tag == "equal":
                parts.append(text)
            elif seg.tag == "delete":
                parts.append(f"<span style='background-color:#ffcccc;color:#cc0000;'>{text}</span>")
            elif seg.tag == "insert":
                parts.append(f"<span style='background-color:#ccffcc;color:#006600;'>{text}</span>")
            elif seg.tag == "replace_old":
                parts.append(f"<span style='background-color:#ffcccc;color:#cc0000;text-decoration:line-through;'>{text}</span>")
            elif seg.tag == "replace_new":
                parts.append(f"<span style='background-color:#ccffcc;color:#006600;'>{text}</span>")
            if text:
                parts.append("<br>")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def filter_pdf_paths(args: list[str]) -> list[str]:
    """Return the subset of CLI args that look like PDF file paths.

    Windows passes a quoted ``%1`` for file activations, so a path survives
    intact even with spaces, parentheses, or non-ASCII characters. The IPC
    hand-off serializes these as JSON (Unicode-safe). Only the ``.pdf`` suffix
    is matched here; existence is checked by the callers.
    """
    return [a for a in args if Path(a).suffix.lower() == ".pdf"]


def _try_send_to_existing_instance(file_paths: list[str]) -> bool:
    """Send file paths to a running instance via QLocalSocket. Returns True if sent."""
    if not file_paths:
        return False
    socket = QLocalSocket()
    socket.connectToServer(IPC_SERVER_NAME)
    if not socket.waitForConnected(2000):
        socket.deleteLater()
        return False
    try:
        payload = json.dumps([p for p in file_paths if p.lower().endswith(".pdf")])
        socket.write(payload.encode("utf-8"))
        socket.waitForBytesWritten(2000)
        return True
    except Exception:
        return False
    finally:
        socket.disconnectFromServer()
        socket.deleteLater()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(PdfReaderWindow.APP_NAME)
    app.setOrganizationName("Sparsh Sam")

    # ---- Single-instance IPC: route file opens to existing window ----
    pdf_paths = filter_pdf_paths(sys.argv[1:])
    if pdf_paths and _try_send_to_existing_instance(pdf_paths):
        # Paths routed to existing instance — exit this one
        sys.exit(0)

    ipc_server = QLocalServer()
    # Clean up any stale server name from a previous crash
    ipc_server.removeServer(IPC_SERVER_NAME)
    ipc_server.listen(IPC_SERVER_NAME)

    # Set app-level icon before window creation for taskbar/Wayland
    icon_path = Path(__file__).parent / "assets" / "branding" / "pdfreader_by_sparsh.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = PdfReaderWindow(ipc_server=ipc_server)
    window.show()
    # Open command-line PDFs in tabs
    for path in pdf_paths:
        QTimer.singleShot(0, lambda p=path: window.open_pdf(p))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
