import json
import os
import platform
import re
import subprocess  # nosec B404 — needed for self-update mechanism
import sys
import tempfile
import zipfile
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

import fitz
from PySide6.QtCore import QByteArray, QEvent, QPoint, QRect, QSettings, QSize, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QDesktopServices, QIcon, QImage, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtNetwork import QLocalServer, QLocalSocket, QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
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
    QVBoxLayout,
    QWidget,
)


__version__ = "1.1.0-dev"
GITHUB_REPO = "sparshsam/pdfreader-by-sparsh"
WINDOWS_UPDATE_ASSET = "PDFReader-by-Sparsh-Windows.zip"
MACOS_APPLE_SILICON_UPDATE_ASSET = "PDFReader-by-Sparsh-macOS-Apple-Silicon.zip"
MACOS_INTEL_UPDATE_ASSET = "PDFReader-by-Sparsh-macOS-Intel.zip"
IPC_SERVER_NAME = "PDFReaderBySparsh-IPC"
RECENT_FILES_MAX = 10
SETTINGS_RECENT_KEY = "***"
SETTINGS_AUTO_UPDATE_KEY = "autoCheckUpdates"

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


# ---------------------------------------------------------------------------
# Stylesheets
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Stylesheets
# ---------------------------------------------------------------------------

LIGHT_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #f5f5f5;
    color: #1a1a1a;
}
QMainWindow::separator {
    background-color: #d0d0d0;
}
QPushButton {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 1px solid #c8c8c8;
    padding: 4px 14px;
    border-radius: 4px;
    min-height: 22px;
}
QPushButton:hover {
    background-color: #e8e8e8;
    border-color: #a0a0a0;
}
QPushButton:pressed {
    background-color: #d0d0d0;
}
QPushButton:checked {
    background-color: #4a90d9;
    color: #ffffff;
    border-color: #357abd;
}
QPushButton:disabled {
    background-color: #e8e8e8;
    color: #a0a0a0;
    border-color: #e0e0e0;
}
QLineEdit {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 1px solid #c8c8c8;
    padding: 4px 6px;
    border-radius: 4px;
    selection-background-color: #4a90d9;
    selection-color: #ffffff;
}
QLineEdit:focus {
    border-color: #4a90d9;
}
QSpinBox {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 1px solid #c8c8c8;
    padding: 4px;
    border-radius: 4px;
}
QSpinBox:focus {
    border-color: #4a90d9;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #e8e8e8;
    border: none;
    width: 18px;
}
QLabel {
    color: #1a1a1a;
    background-color: transparent;
}
QStatusBar {
    background-color: #e8e8e8;
    color: #666666;
    border-top: 1px solid #d0d0d0;
}
QScrollArea {
    background-color: #e0e0e0;
    border: none;
}
#TabStrip {
    background-color: #e0e0e0;
    border-bottom: 1px solid #d0d0d0;
}
QTabBar::tab {
    background-color: #e0e0e0;
    color: #666666;
    padding: 6px 16px 6px 18px;
    border: none;
    border-right: 1px solid #d0d0d0;
    min-height: 24px;
}
QTabBar::tab:selected {
    background-color: #f5f5f5;
    color: #1a1a1a;
    border-bottom: 2px solid #4a90d9;
}
QTabBar::tab:hover:!selected {
    background-color: #d8d8d8;
    color: #1a1a1a;
}
QToolButton#NewTabButton {
    background-color: transparent;
    color: #666666;
    border: 1px solid transparent;
    border-radius: 3px;
}
QToolButton#NewTabButton {
    font-size: 16px;
    font-weight: 400;
    margin: 0px 8px 0px 4px;
}
QToolButton#NewTabButton:hover {
    background-color: #d6d6d6;
    border-color: transparent;
    color: #1a1a1a;
}
QToolButton#TabCloseButton {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    color: #6b7280;
    font-size: 17px;
    font-weight: 400;
    padding: 0px;
}
QToolButton#TabCloseButton:hover {
    background-color: #e05252;
    color: #ffffff;
}
QToolButton#TabCloseButton:pressed {
    background-color: #c83f3f;
    color: #ffffff;
}
QMenuBar {
    background-color: #e8e8e8;
    color: #1a1a1a;
    border-bottom: 1px solid #d0d0d0;
    padding: 2px;
}
QMenuBar::item {
    padding: 4px 10px;
    background-color: transparent;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background-color: #d0d0d0;
}
QMenu {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 1px solid #c8c8c8;
    padding: 4px;
}
QMenu::item {
    padding: 6px 28px 6px 20px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #4a90d9;
    color: #ffffff;
}
QMenu::item:disabled {
    color: #a0a0a0;
}
QMenu::separator {
    height: 1px;
    background-color: #d0d0d0;
    margin: 4px 8px;
}
QProgressDialog {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 1px solid #c8c8c8;
}
QMessageBox {
    background-color: #f5f5f5;
    color: #1a1a1a;
}
QMessageBox QLabel {
    color: #1a1a1a;
}
QMessageBox QPushButton {
    min-width: 80px;
}
QInputDialog {
    background-color: #f5f5f5;
    color: #1a1a1a;
}
QScrollBar:horizontal {
    background-color: #e0e0e0;
    height: 10px;
    border: none;
}
QScrollBar::handle:horizontal {
    background-color: #b0b0b0;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #909090;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QScrollBar:vertical {
    background-color: #e0e0e0;
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: #b0b0b0;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #909090;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1a1b26;
    color: #c0caf5;
}
QMainWindow::separator {
    background-color: #292e42;
}
QPushButton {
    background-color: #24283b;
    color: #c0caf5;
    border: 1px solid #3b4261;
    padding: 4px 14px;
    border-radius: 4px;
    min-height: 22px;
}
QPushButton:hover {
    background-color: #33467c;
    border-color: #565f89;
}
QPushButton:pressed {
    background-color: #414868;
}
QPushButton:checked {
    background-color: #7aa2f7;
    color: #1a1b26;
    border-color: #7aa2f7;
}
QPushButton:disabled {
    background-color: #1a1b26;
    color: #3b4261;
    border-color: #24283b;
}
QLineEdit {
    background-color: #24283b;
    color: #c0caf5;
    border: 1px solid #3b4261;
    padding: 4px 6px;
    border-radius: 4px;
    selection-background-color: #7aa2f7;
    selection-color: #1a1b26;
}
QLineEdit:focus {
    border-color: #7aa2f7;
}
QSpinBox {
    background-color: #24283b;
    color: #c0caf5;
    border: 1px solid #3b4261;
    padding: 4px;
    border-radius: 4px;
}
QSpinBox:focus {
    border-color: #7aa2f7;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #3b4261;
    border: none;
    width: 18px;
}
QLabel {
    color: #c0caf5;
    background-color: transparent;
}
QStatusBar {
    background-color: #13141f;
    color: #565f89;
    border-top: 1px solid #292e42;
}
QScrollArea {
    background-color: #1a1b26;
    border: none;
}
#TabStrip {
    background-color: #13141f;
    border-bottom: 1px solid #292e42;
}
QTabBar::tab {
    background-color: #13141f;
    color: #565f89;
    padding: 6px 16px 6px 18px;
    border: none;
    border-right: 1px solid #292e42;
    min-height: 24px;
}
QTabBar::tab:selected {
    background-color: #1a1b26;
    color: #7aa2f7;
    border-bottom: 2px solid #7aa2f7;
}
QTabBar::tab:hover:!selected {
    background-color: #292e42;
    color: #c0caf5;
}
QToolButton#NewTabButton {
    background-color: transparent;
    color: #8b93b5;
    border: 1px solid transparent;
    border-radius: 3px;
}
QToolButton#NewTabButton {
    font-size: 16px;
    font-weight: 400;
    margin: 0px 8px 0px 4px;
}
QToolButton#NewTabButton:hover {
    background-color: #292e42;
    border-color: transparent;
    color: #c0caf5;
}
QToolButton#TabCloseButton {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    color: #7d86a9;
    font-size: 17px;
    font-weight: 400;
    padding: 0px;
}
QToolButton#TabCloseButton:hover {
    background-color: #e05252;
    color: #ffffff;
}
QToolButton#TabCloseButton:pressed {
    background-color: #c83f3f;
    color: #ffffff;
}
QMenuBar {
    background-color: #13141f;
    color: #c0caf5;
    border-bottom: 1px solid #292e42;
    padding: 2px;
}
QMenuBar::item {
    padding: 4px 10px;
    background-color: transparent;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background-color: #292e42;
}
QMenu {
    background-color: #1a1b26;
    color: #c0caf5;
    border: 1px solid #3b4261;
    padding: 4px;
}
QMenu::item {
    padding: 6px 28px 6px 20px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #33467c;
}
QMenu::item:disabled {
    color: #3b4261;
}
QMenu::separator {
    height: 1px;
    background-color: #292e42;
    margin: 4px 8px;
}
QProgressDialog {
    background-color: #1a1b26;
    color: #c0caf5;
    border: 1px solid #3b4261;
}
QMessageBox {
    background-color: #1a1b26;
    color: #c0caf5;
}
QMessageBox QLabel {
    color: #c0caf5;
}
QMessageBox QPushButton {
    min-width: 80px;
}
QInputDialog {
    background-color: #1a1b26;
    color: #c0caf5;
}
QScrollBar:horizontal {
    background-color: #13141f;
    height: 10px;
    border: none;
}
QScrollBar::handle:horizontal {
    background-color: #3b4261;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #565f89;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QScrollBar:vertical {
    background-color: #13141f;
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: #3b4261;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #565f89;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
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
# Main Window
# ---------------------------------------------------------------------------

class PdfReaderWindow(QMainWindow):
    APP_NAME = "PDFReader by Sparsh"
    MAX_PDF_SIZE_BYTES = 500 * 1024 * 1024
    MAX_PAGE_DIMENSION_POINTS = 14400
    MAX_RENDER_PIXELS = 80_000_000
    MAX_SEARCH_MATCHES = 20_000
    MAX_SPLIT_PAGES = 1000
    MAX_OCR_CACHE_PAGES = 3
    MIN_ZOOM = 0.25
    MAX_ZOOM = 5.0
    ZOOM_STEP = 0.15

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
        ("New Tab", "Ctrl+T"),
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
    )

    def __init__(self, ipc_server: QLocalServer | None = None):
        _perf_start_t = _perf_start()
        super().__init__()
        self.setWindowTitle(self.APP_NAME)
        self.resize(1000, 800)

        # ---- IPC server for single-instance tab routing ----
        self._ipc_server = ipc_server
        if ipc_server is not None:
            ipc_server.newConnection.connect(self._on_ipc_connection)

        # ---- Continuous scroll ----
        self._continuous_mode = True  # default to continuous
        self._continuous_pages: list[QLabel] = []
        self._continuous_container = None
        self._continuous_layout = None

        # App icon
        self._set_app_icon()

        # Enable drag-and-drop
        self.setAcceptDrops(True)

        self.settings = QSettings("Sparsh", "PDFReader by Sparsh")

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

        # ---- Dark mode ----
        self._theme = self.settings.value("theme", self.THEME_AUTO, int)
        self._dark_mode = self._compute_dark_mode()

        # ---- Recent files ----
        self._recent_files = self._load_recent_files()

        # ---- Workspace session ----
        self._auto_restore = self.settings.value("autoRestore", True, bool)
        self._session_data: list[dict] | None = None

        # ---- Update system ----
        self._update_nam = QNetworkAccessManager(self)
        self._update_nam.finished.connect(self._on_update_check_reply)
        self._download_nam = QNetworkAccessManager(self)
        self._download_nam.finished.connect(self._on_download_finished)
        self._update_progress = None
        self._update_latest_tag = None
        self._update_asset_name = None
        self._update_download_path = None
        self._auto_update_check = self.settings.value(SETTINGS_AUTO_UPDATE_KEY, True, bool)

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

        # Listen for system theme changes
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
        self.new_tab_button.setText("+")
        self.new_tab_button.setObjectName("NewTabButton")
        self.new_tab_button.setFixedSize(28, 28)
        self.new_tab_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.new_tab_button.setAutoRaise(True)
        self.new_tab_button.setCursor(Qt.PointingHandCursor)
        self.new_tab_button.setToolTip("Open another PDF")
        self.new_tab_button.setAccessibleName("Open another PDF")
        self.new_tab_button.clicked.connect(self.open_pdf)
        tab_strip_layout.addWidget(self.new_tab_button)
        tab_strip_layout.addStretch(1)

        root.addWidget(tab_strip)

        # Controls bar
        controls_widget = QWidget()
        controls_widget.setContentsMargins(8, 6, 8, 6)
        controls = QHBoxLayout(controls_widget)
        controls.setSpacing(4)
        controls.setContentsMargins(0, 0, 0, 0)

        self.prev_button = QPushButton("Prev")
        self.prev_button.setToolTip("Previous page (Page Up)")
        self.next_button = QPushButton("Next")
        self.next_button.setToolTip("Next page (Page Down)")
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(1)
        self.page_spin.setFixedWidth(70)
        self.page_spin.setToolTip("Jump to page number")
        self.page_count_label = QLabel("/ 0")

        self.zoom_out_button = QPushButton("\u2212")
        self.zoom_out_button.setFixedWidth(30)
        self.zoom_out_button.setToolTip("Zoom out (Ctrl+-)")
        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setFixedWidth(30)
        self.zoom_in_button.setToolTip("Zoom in (Ctrl+=)")
        self.fit_button = QPushButton("Fit")
        self.fit_button.setCheckable(True)
        self.fit_button.setChecked(True)
        self.fit_button.setFixedWidth(40)
        self.fit_button.setToolTip("Fit page to window width (Ctrl+0)")
        self.copy_button = QPushButton("Copy")
        self.copy_button.setToolTip("Copy selected text (Ctrl+C)")

        controls.addSpacing(4)
        controls.addWidget(self.prev_button)
        controls.addWidget(self.next_button)
        controls.addWidget(QLabel("Pg"))
        controls.addWidget(self.page_spin)
        controls.addWidget(self.page_count_label)
        controls.addSpacing(4)
        controls.addWidget(self.zoom_out_button)
        controls.addWidget(self.zoom_in_button)
        controls.addWidget(self.fit_button)
        controls.addWidget(self.copy_button)

        # Annotation buttons
        self.highlight_button = QPushButton("HL")
        self.highlight_button.setFixedWidth(34)
        self.highlight_button.setToolTip("Highlight selected text")
        self.underline_button = QPushButton("UL")
        self.underline_button.setFixedWidth(34)
        self.underline_button.setToolTip("Underline selected text")
        self.strike_button = QPushButton("ST")
        self.strike_button.setFixedWidth(34)
        self.strike_button.setToolTip("Strikethrough selected text")
        self.sticky_button = QPushButton("\U0001f4dd")
        self.sticky_button.setFixedWidth(34)
        self.sticky_button.setCheckable(True)
        self.sticky_button.setToolTip("Place sticky note")

        controls.addWidget(self.highlight_button)
        controls.addWidget(self.underline_button)
        controls.addWidget(self.strike_button)
        controls.addWidget(self.sticky_button)

        controls.addSpacing(4)
        self.semantic_cb = QCheckBox("Semantic")
        self.semantic_cb.setToolTip("Enable semantic (meaning-based) search instead of keyword exact match")

        controls.addSpacing(4)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search text")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(160)
        self.search_prev_button = QPushButton("\u25b2")
        self.search_prev_button.setFixedWidth(30)
        self.search_next_button = QPushButton("\u25bc")
        self.search_next_button.setFixedWidth(30)
        self.search_count_label = QLabel("0")
        self.search_count_label.setFixedWidth(32)

        controls.addWidget(self.search_input, 1)
        controls.addWidget(self.search_prev_button)
        controls.addWidget(self.search_next_button)
        controls.addWidget(self.search_count_label)
        controls.addWidget(self.semantic_cb)
        root.addWidget(controls_widget)

        # Page content — improved empty state
        self.empty_state_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_state_widget)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.setSpacing(14)

        # Icon / visual marker
        icon_label = QLabel()
        icon_pixmap = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogStart).pixmap(48, 48)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_opacity = QGraphicsOpacityEffect()
        icon_opacity.setOpacity(0.45)
        icon_label.setGraphicsEffect(icon_opacity)
        empty_layout.addWidget(icon_label)

        title_label = QLabel("<h2 style='color:#666; font-weight:400; margin:0;'>Open a PDF to begin</h2>")
        title_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(title_label)

        subtitle_label = QLabel(
            "<p style='color:#999; font-size:13px; margin:0; line-height:1.5;'>"
            "Drag and drop a PDF here, or use <b>File → Open PDF</b> (Ctrl+O)<br>"
            "to get started reading locally and privately.</p>"
        )
        subtitle_label.setWordWrap(True)
        subtitle_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(subtitle_label)

        open_btn = QPushButton("Open PDF")
        open_btn.setFixedWidth(160)
        open_btn.clicked.connect(self.open_pdf)
        open_btn_layout = QHBoxLayout()
        open_btn_layout.addStretch()
        open_btn_layout.addWidget(open_btn)
        open_btn_layout.addStretch()
        empty_layout.addLayout(open_btn_layout)

        self.page_label = PdfPageLabel()
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.selection_finished.connect(self.select_text_in_rect)
        self.page_label.sticky_note_requested.connect(self._place_sticky_note)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.empty_state_widget)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidgetResizable(True)
        root.addWidget(self.scroll_area, 1)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar(self))

        # Stack for page_label vs empty_state
        self._content_stack = {None: self.empty_state_widget}
        self._current_content = None

        # Signal connections
        self.prev_button.clicked.connect(self.previous_page)
        self.next_button.clicked.connect(self.next_page)
        self.page_spin.valueChanged.connect(self.jump_to_page)
        self.zoom_out_button.clicked.connect(self.zoom_out)
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.fit_button.toggled.connect(self._on_fit_toggled)
        self.copy_button.clicked.connect(self.copy_selected_text)
        self.highlight_button.clicked.connect(self.highlight_selection)
        self.underline_button.clicked.connect(self.underline_selection)
        self.strike_button.clicked.connect(self.strikeout_selection)
        self.sticky_button.clicked.connect(self._toggle_sticky_note_mode)
        self.search_input.returnPressed.connect(self.search)
        self.search_input.textChanged.connect(self._search_text_changed)
        self.search_prev_button.clicked.connect(self.previous_search_result)
        self.search_next_button.clicked.connect(self.next_search_result)

    def _build_actions(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(18, 18))
        self.addToolBar(toolbar)

        style = self.style()

        open_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), "Open", self)
        open_action.triggered.connect(self.open_pdf)
        toolbar.addAction(open_action)

        toolbar.addSeparator()
        save_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "Save", self)
        save_action.triggered.connect(self._save_document)
        toolbar.addAction(save_action)

        toolbar.addSeparator()
        prev_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowBack), "Previous Page", self)
        prev_action.triggered.connect(self.previous_page)
        toolbar.addAction(prev_action)

        next_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowForward), "Next Page", self)
        next_action.triggered.connect(self.next_page)
        toolbar.addAction(next_action)

        toolbar.addSeparator()
        zoom_in_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowUp), "Zoom In", self)
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)

        zoom_out_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowDown), "Zoom Out", self)
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)

        toolbar.addSeparator()
        find_action = QAction("Find", self)
        find_action.triggered.connect(self.focus_search)
        toolbar.addAction(find_action)

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
            "new_tab": self.open_pdf,
        }
        for shortcut_id, sequence in self.REGISTERED_SHORTCUTS:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.ApplicationShortcut)
            shortcut.activated.connect(shortcut_handlers[shortcut_id])
            self._app_shortcuts.append(shortcut)

    def eventFilter(self, obj, event):
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
            return False
        if modifiers != Qt.ControlModifier:
            return False

        ctrl_handlers = {
            Qt.Key_O: self.open_pdf,
            Qt.Key_T: self.open_pdf,
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
            return []
        if isinstance(raw, str):
            raw = [raw]
        return [p for p in raw if p and Path(p).exists()]

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

    def _on_tab_double_click(self, index: int):
        self.open_pdf()

    def _on_tab_switch(self, index: int):
        if index < 0 or index >= self.tab_bar.count():
            return
        new_tab_id = self.tab_bar.tabData(index)
        if new_tab_id is None or new_tab_id == self.current_tab_id:
            return
        self._save_current_state()
        self._save_current_tab_controls()
        self._restore_state(new_tab_id)
        self._restore_current_tab_controls()
        self.clear_text_selection(render=False)
        self.render_page()
        self._update_controls()

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
        if self.search_results:
            self.search_count_label.setText(self._search_count_text())
        else:
            self.search_count_label.setText("0")

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
        self.tab_bar.blockSignals(True)
        try:
            for i in range(self.tab_bar.count()):
                if self.tab_bar.tabData(i) == tab_id:
                    self.tab_bar.removeTab(i)
                    break
        finally:
            self.tab_bar.blockSignals(False)
        del self.tabs[tab_id]

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
        for tid in tab_ids:
            if tid in self.tabs:
                tab = self.tabs[tid]
                if tab.document is not None:
                    tab.document.close()
        self.tabs.clear()
        self.tab_bar.clear()
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

        When file_name is not provided, tries a 3-tier fallback chain:
          1. Qt non-native QFileDialog
          2. Tkinter native dialog
          3. Manual path input via QInputDialog
        """
        if isinstance(file_name, bool):
            # QAction.triggered(bool) and QPushButton.clicked(bool) pass a
            # checked-state argument. This slot treats that as "no path".
            file_name = None
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

        # No path — try the fallback dialog chain
        start_dir = self.settings.value("lastFolder", str(Path.home()))
        file_name = self._pick_file_qt_dialog(start_dir)
        if not file_name:
            file_name = self._pick_file_tkinter()
        if not file_name:
            file_name = self._pick_file_manual_input()
        if not file_name:
            self._log_update("open_pdf: all pickers returned no file")
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

    # ------------------------------------------------------------------
    # Page Rendering
    # ------------------------------------------------------------------

    def render_page(self):
        """Schedule a page render (debounced for rapid calls)."""
        self._render_timer.start()

    def _do_render(self):
        """Perform the actual page render (called by debounce timer)."""
        _t = _perf_start()
        if self.document is None:
            # Show empty state if not already
            if self.scroll_area.widget() is not self.empty_state_widget:
                self.scroll_area.takeWidget()
                empty_parent = self.empty_state_widget.parent()
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
        self.page_label.setStyleSheet(
            "border: 1px solid #3b4261; background-color: white;"
            if self._dark_mode else
            "border: 1px solid #c8c8c8; background-color: white;"
        )
        self.page_label.adjustSize()
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(self.current_page + 1)
        self.page_spin.blockSignals(False)
        self._update_controls()

    def _render_continuous(self):
        """Render pages in continuous vertical scroll layout."""
        page_count = self.document.page_count
        page0 = self.document.load_page(0)
        zoom = self._effective_zoom(page0)
        self.current_render_zoom = zoom

        # HiDPI-aware: render at device pixel ratio for crisp output
        dpr = self.devicePixelRatioF() if hasattr(self, 'devicePixelRatioF') else 1.0
        render_zoom = zoom * dpr
        border_style = ("border: 1px solid #3b4261; background-color: white;"
                        if self._dark_mode else
                        "border: 1px solid #c8c8c8; background-color: white;")

        # Determine visible range (current page + buffer)
        buffer_pages = 5
        start_page = max(0, self.current_page - buffer_pages)
        end_page = min(page_count, self.current_page + buffer_pages + 1)

        # Build or reuse continuous container
        if self._continuous_container is None:
            self._continuous_container = QWidget()
            self._continuous_layout = QVBoxLayout(self._continuous_container)
            self._continuous_layout.setContentsMargins(12, 12, 12, 12)
            self._continuous_layout.setSpacing(12)

        # Show continuous container in scroll area
        if self.scroll_area.widget() is not self._continuous_container:
            self.scroll_area.takeWidget()
            self.scroll_area.setWidget(self._continuous_container)
            self.scroll_area.setWidgetResizable(True)

        show_annots = hasattr(self, "show_annots_action") and self.show_annots_action.isChecked()

        # Clear and rebuild visible pages
        for label in self._continuous_pages:
            label.setParent(None)
            label.deleteLater()
        self._continuous_pages.clear()

        # Clear layout items
        while self._continuous_layout.count():
            item = self._continuous_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for page_idx in range(start_page, end_page):
            try:
                page = self.document.load_page(page_idx)
                self._validate_render_size(page, render_zoom)
                matrix = fitz.Matrix(render_zoom, render_zoom)
                pixmap = page.get_pixmap(matrix=matrix, alpha=False, annots=show_annots)
                image = QImage(
                    pixmap.samples,
                    pixmap.width,
                    pixmap.height,
                    pixmap.stride,
                    QImage.Format_RGB888,
                )
                qp = QPixmap.fromImage(image)
                qp.setDevicePixelRatio(dpr)
                label = QLabel()
                label.setPixmap(qp)
                label.setStyleSheet(border_style)
                label.setAlignment(Qt.AlignCenter)
                self._continuous_pages.append(label)
                self._continuous_layout.addWidget(label, 0, Qt.AlignCenter)
            except Exception:
                continue  # nosec — skip unrenderable pages gracefully

        # Scroll to show current page
        if self._continuous_pages:
            target_idx = self.current_page - start_page
            if 0 <= target_idx < len(self._continuous_pages):
                target_y = self._continuous_pages[target_idx].y()
                self.scroll_area.verticalScrollBar().setValue(max(0, target_y - 20))

        self.page_spin.blockSignals(True)
        self.page_spin.setValue(self.current_page + 1)
        self.page_spin.blockSignals(False)
        self._update_controls()
        _perf_end(_t, f"_do_render page={self.current_page} zoom={self.current_render_zoom:.2f}")

    def _effective_zoom(self, page):
        if not self.fit_to_window:
            return self.zoom
        viewport_width = max(1, self.scroll_area.viewport().width() - 24)
        page_width = max(1, page.rect.width)
        return max(self.MIN_ZOOM, min(self.MAX_ZOOM, viewport_width / page_width))

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

    def _save_document(self):
        """Explicit full save via File > Save."""
        if self.current_path is None or self.document is None:
            self.statusBar().showMessage("No document open", 3000)
            return
        try:
            self.document.save(self.current_path, garbage=1, deflate=True)
            self.statusBar().showMessage("Document saved", 3000)
        except Exception as exc:
            self.statusBar().showMessage(f"Save failed: {exc}", 5000)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def previous_page(self):
        if self.document is not None and self.current_page > 0:
            self.current_page -= 1
            self.clear_text_selection(render=False)
            self._sync_search_result_to_page()
            self.render_page()

    def next_page(self):
        if self.document is not None and self.current_page < self.document.page_count - 1:
            self.current_page += 1
            self.clear_text_selection(render=False)
            self._sync_search_result_to_page()
            self.render_page()

    def jump_to_page(self, page_number):
        if self.document is None:
            return
        target = page_number - 1
        if target != self.current_page:
            self.current_page = target
            self.clear_text_selection(render=False)
            self._sync_search_result_to_page()
            self.render_page()

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
        has_document = self.document is not None
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

    def _set_app_icon(self):
        """Set window icon from bundled .ico file with exhaustive fallback logging."""
        icon_paths = []

        # 1. Frozen (PyInstaller) standard onedir layout: assets/ next to EXE
        if getattr(sys, "frozen", False):
            icon_paths.append(Path(sys.executable).parent / "assets" / "pdfreader_by_sparsh.ico")
            # 2. _internal/assets/ layout (some PyInstaller configs)
            icon_paths.append(Path(sys.executable).parent / "_internal" / "assets" / "pdfreader_by_sparsh.ico")

        # 3. Dev/source build: icon in repo root assets/
        icon_paths.append(Path(__file__).parent / "assets" / "pdfreader_by_sparsh.ico")

        # 4. Frozen with MEIPASS (legacy PyInstaller attribute)
        if getattr(sys, "frozen", False) and hasattr(sys, '_MEIPASS'):
            icon_paths.append(Path(sys._MEIPASS) / "assets" / "pdfreader_by_sparsh.ico")

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
        if self._update_progress is not None:
            return
        self._update_nam_silent = QNetworkAccessManager(self)
        self._update_nam_silent.finished.connect(self._on_silent_update_reply)
        url = QUrl(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.UserAgentHeader, "PDFReader-by-Sparsh/1.0")
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
            self.statusBar().showMessage(result["message"], 10000)
            # Show the interactive update prompt
            self.check_for_updates()

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
    def _select_update_apply_method(system, asset_name, dest):
        suffix = Path(dest).suffix.lower()
        if system == "Windows" and asset_name == WINDOWS_UPDATE_ASSET and suffix == ".zip":
            return "windows_zip", ""
        if system == "Darwin" and suffix == ".zip":
            return "macos_zip", ""
        diagnostic = (
            "Unsupported update package.\n\n"
            f"System: {system}\n"
            f"Asset: {asset_name or '<missing>'}\n"
            f"Path: {dest}\n"
            f"Suffix: {suffix or '<missing>'}"
        )
        return None, diagnostic

    @staticmethod
    def _validate_download_metadata(asset_name, latest_tag):
        if not asset_name:
            return "Download metadata missing. The updater could not determine the release asset name."
        if not latest_tag:
            return "Download metadata missing. The updater could not determine the release tag."
        return ""

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

    def _get_platform_asset(self, assets):
        assets_by_name = {a.get("name", ""): a for a in assets}
        system = platform.system()
        if system == "Windows":
            asset = assets_by_name.get(WINDOWS_UPDATE_ASSET)
            if asset:
                return asset["browser_download_url"], asset["name"]
        elif system == "Darwin":
            is_arm = platform.machine() in ("arm64", "aarch64")
            expected_name = (
                MACOS_APPLE_SILICON_UPDATE_ASSET if is_arm else MACOS_INTEL_UPDATE_ASSET
            )
            asset = assets_by_name.get(expected_name)
            if asset:
                return asset["browser_download_url"], asset["name"]
        return None, None

    def check_for_updates(self):
        if self._update_progress is not None:
            return
        self.update_action.setEnabled(False)
        self.statusBar().showMessage("Checking for updates...")
        url = QUrl(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.UserAgentHeader, "PDFReader-by-Sparsh/1.0")
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

        if result["outcome"] in ("network_error", "http_error", "json_error"):
            self.statusBar().showMessage(result["message"], 5000)
            reply.deleteLater()
            return

        reply.deleteLater()

        # Already on latest version
        if result["outcome"] == "already_latest":
            QMessageBox.information(
                self,
                "Up to Date",
                f"You're already running the latest version of PDFReader (v{__version__}).",
            )
            self.statusBar().showMessage(result["message"], 5000)
            return

        # Update available - existing dialog flow
        latest_tag = result["latest_tag"]
        data = result["data"]
        current_version = self._parse_version(__version__)
        assets = data.get("assets", [])
        asset_url, asset_name = self._get_platform_asset(assets)

        release_url = data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases")
        release_notes = (data.get("body") or "")[:500]

        msg = (
            f"<h3>Update Available</h3>"
            f"<p><b>v{'.'.join(str(x) for x in current_version)}</b> \u2192 <b>{latest_tag}</b></p>"
        )
        if release_notes:
            msg += f"<hr><pre style='white-space:pre-wrap'>{release_notes}</pre>"

        btn = QMessageBox(self)
        btn.setWindowTitle("Update Available")
        btn.setTextFormat(Qt.RichText)
        btn.setText(msg)

        if asset_url and asset_name:
            download_button = btn.addButton("Download & Install", QMessageBox.AcceptRole)
        skip_button = btn.addButton("Skip This Version", QMessageBox.RejectRole)
        _ = btn.addButton("Later", QMessageBox.DestructiveRole)

        btn.exec()

        if btn.clickedButton() == skip_button:
            self.statusBar().showMessage("Update skipped", 3000)
            return

        if asset_url and btn.clickedButton() == download_button:
            self._start_download(asset_url, asset_name, latest_tag)
        elif not asset_url:
            import webbrowser
            webbrowser.open(release_url)
            self.statusBar().showMessage(
                "No installer for your platform. Opening releases page.", 5000
            )

    def _start_download(self, asset_url, asset_name, latest_tag):
        system = platform.system()
        self._log_update(f"current_version={__version__}")
        self._log_update(f"latest_tag={latest_tag}")
        self._log_update(f"selected_asset_name={asset_name}")
        self._log_update(f"asset_url={asset_url}")
        self._log_update(f"detected_os={system}")

        validation_errors = []
        if not asset_url:
            validation_errors.append("missing asset URL")
        if not asset_name:
            validation_errors.append("missing asset name")
        if not latest_tag:
            validation_errors.append("missing release tag")
        if system == "Windows" and asset_name != WINDOWS_UPDATE_ASSET:
            validation_errors.append(
                f"Windows updater expected {WINDOWS_UPDATE_ASSET}, got {asset_name or '<missing>'}"
            )
        if validation_errors:
            message = "Cannot start update download:\n\n" + "\n".join(validation_errors)
            self._log_update(f"failure={message}")
            QMessageBox.critical(self, "Update Error", message)
            return

        self._update_latest_tag = latest_tag
        self._update_asset_name = asset_name
        self._update_download_path = None

        self._update_progress = QProgressDialog(
            f"Downloading {asset_name}\u2026", "Cancel", 0, 0, self
        )
        self._update_progress.setWindowTitle("Downloading Update")
        self._update_progress.setWindowModality(Qt.WindowModal)
        self._update_progress.setMinimumDuration(0)
        self._update_progress.setValue(0)
        self._update_progress.canceled.connect(self._cancel_download)
        self._update_progress.show()

        self.update_action.setEnabled(False)
        self.statusBar().showMessage(f"Downloading {asset_name}\u2026")

        request = QNetworkRequest(QUrl(asset_url))
        request.setHeader(QNetworkRequest.UserAgentHeader, "PDFReader-by-Sparsh/1.0")
        request.setTransferTimeout(300000)
        reply = self._download_nam.get(request)
        reply.setProperty("asset_name", asset_name)
        reply.setProperty("latest_tag", latest_tag)
        reply.downloadProgress.connect(self._on_download_progress)

    def _on_download_progress(self, received, total):
        if self._update_progress is None:
            return
        if total > 0:
            self._update_progress.setMaximum(int(total))
            self._update_progress.setValue(int(received))
            mb_rec = received / (1024 * 1024)
            mb_tot = total / (1024 * 1024)
            self._update_progress.setLabelText(
                f"Downloading update\u2026 {mb_rec:.1f} / {mb_tot:.1f} MB"
            )
        else:
            self._update_progress.setMaximum(0)
            self._update_progress.setValue(0)

    def _cancel_download(self):
        self._download_nam.finished.disconnect(self._on_download_finished)
        self._download_nam = QNetworkAccessManager(self)
        self._download_nam.finished.connect(self._on_download_finished)
        self._update_progress = None
        self._update_latest_tag = None
        self._update_asset_name = None
        self.update_action.setEnabled(True)
        self.statusBar().showMessage("Download cancelled", 3000)

    def _on_download_finished(self, reply):
        self.update_action.setEnabled(True)
        if self._update_progress is not None:
            self._update_progress.close()
            self._update_progress = None

        asset_name = reply.property("asset_name")
        latest_tag = reply.property("latest_tag")
        metadata_error = self._validate_download_metadata(asset_name, latest_tag)
        if metadata_error:
            self._log_update("failure=download metadata missing")
            QMessageBox.critical(
                self,
                "Update Error",
                metadata_error,
            )
            reply.deleteLater()
            return

        if reply.error() != QNetworkReply.NoError:
            self._log_update(f"failure=download failed: {reply.errorString()}")
            QMessageBox.critical(
                self,
                "Download Failed",
                f"Could not download the update:\n{reply.errorString()}",
            )
            reply.deleteLater()
            return

        try:
            temp_dir = self._updater_temp_dir()
            dest = temp_dir / asset_name
            self._log_update(f"download_destination={dest}")
            data = reply.readAll()
            with open(dest, "wb") as f:
                f.write(bytes(data))
            self._update_download_path = dest
        except Exception as exc:
            self._log_update(f"failure=could not save download: {exc}")
            QMessageBox.critical(
                self,
                "Download Failed",
                f"Could not save the downloaded file:\n{exc}",
            )
            reply.deleteLater()
            return
        finally:
            reply.deleteLater()

        self._apply_update(dest, latest_tag, asset_name)

    def _apply_update(self, dest: Path, latest_tag: str, asset_name: str):
        if dest is None or not dest.exists():
            self._log_update("failure=update file not found")
            QMessageBox.critical(self, "Update Error", "Update file not found.")
            return

        system = platform.system()
        self._log_update(f"detected_os={system}")
        method, diagnostic = self._select_update_apply_method(system, asset_name, dest)
        self._log_update(f"selected_apply_method={method or 'unsupported'}")

        if method == "windows_zip":
            self._apply_update_windows_zip(dest, latest_tag)
        elif method == "macos_zip":
            self._apply_update_macos(dest, latest_tag)
        else:
            self._log_update(f"failure={diagnostic}")
            QMessageBox.critical(self, "Update Error", diagnostic)
            return

    # ------------------------------------------------------------------
    def _apply_update_windows_zip(self, dest, tag):
        """Replace the running app via ZIP extract + batch updater (onedir mode).

        The batch script is written to %TEMP%\\PDFReader-Updates\\ (writable)
        instead of the install directory (which is often protected like
        C:\\Program Files\\). If the install directory requires admin
        privileges, the script detects the failure and offers to relaunch
        with elevation.
        """
        current_exe = Path(sys.executable)
        app_dir = current_exe.parent
        if not app_dir.exists():
            self._log_update("failure=could not locate app directory")
            QMessageBox.critical(self, "Update Error", "Could not locate the app directory.")
            return

        # Use the writable temp directory for all updater scripts
        script_dir = self._updater_temp_dir()
        self._log_update(f"updater_scripts_dir={script_dir}")
        self._log_update(f"install_dir={app_dir}")

        extract_dir = dest.parent / f"extracted_{tag}"
        self._log_update(f"extract_directory={extract_dir}")
        try:
            if extract_dir.exists():
                import shutil
                shutil.rmtree(extract_dir)
            with zipfile.ZipFile(str(dest), "r") as zf:
                zf.extractall(str(extract_dir))
        except Exception as exc:
            self._log_update(f"failure=could not extract update: {exc}")
            QMessageBox.critical(
                self, "Update Error",
                f"Could not extract the update package.\n\n"
                f"Technical details: {exc}",
            )
            return

        log_path = self._updater_log_path()

        # Clean up any stale batch scripts left in the old location (app_dir)
        # from v1.0.0/v1.0.1 upgrades
        try:
            for old_script in app_dir.glob("_update_*.bat"):
                old_script.unlink(missing_ok=True)
                self._log_update(f"cleaned_stale_script={old_script}")
        except Exception:
            pass  # nosec — best-effort; old location may be protected

        # Write the batch updater script to the WRITABLE temp directory
        bat_path = script_dir / f"_update_{tag}.bat"
        self._log_update(f"batch_script_path={bat_path}")

        # Check if install dir is in a protected location
        needs_elevation_hint = "Program Files" in str(app_dir) or "Program Files (x86)" in str(app_dir)

        bat_content = (
            "@echo off\n"
            "title=PDFReader Updater\n"
            "setlocal enabledelayedexpansion\n"
            "set LOG=" + str(log_path) + "\n"
            'set BATCH_DIR=' + str(script_dir) + '\n'
            'set INSTALL_DIR=' + str(app_dir) + '\n'
            'set EXTRACT_DIR=' + str(extract_dir) + '\n'
            'set CURRENT_EXE=' + str(current_exe) + '\n'
            'set TAG=' + tag + '\n'  # nosec B608 — batch string, not SQL
            'echo [%date% %time%] Starting update... >> "%LOG%"\n'
            'echo [%date% %time%] Script dir: %BATCH_DIR% >> "%LOG%"\n'
            'echo [%date% %time%] Install dir: %INSTALL_DIR% >> "%LOG%"\n'
            '\n'
            ':wait\n'
            f'tasklist /FI "PID eq {os.getpid()}" 2>>"%LOG%" | find "{os.getpid()}" >nul\n'
            'if not errorlevel 1 (\n'
            '    timeout /t 1 /nobreak >nul\n'
            '    goto wait\n'
            ')\n'
            '\n'
            'echo [%date% %time%] Process exited, waiting 2s... >> "%LOG%"\n'
            'timeout /t 2 /nobreak >nul\n'
            '\n'
            ':try_update\n'
            'echo [%date% %time%] Copying _internal folder... >> "%LOG%"\n'
            'set RETRY=0\n'
            ':retry_xcopy\n'
            'xcopy /E /I /Y "%EXTRACT_DIR%\\_internal" "%INSTALL_DIR%\\_internal" >>"%LOG%" 2>&1\n'
            'if errorlevel 1 (\n'
            '    set /a RETRY+=1\n'
            '    if !RETRY! lss 3 (\n'
            '        timeout /t 1 /nobreak >nul\n'
            '        goto retry_xcopy\n'
            '    )\n'
            '    echo [%date% %time%] ERROR: xcopy failed after 3 retries >> "%LOG%"\n'
            '    goto check_elevation\n'
            ')\n'
            '\n'
            'echo [%date% %time%] Copying EXE... >> "%LOG%"\n'
            'set RETRY=0\n'
            ':retry_copy\n'
            'copy /Y /V "%EXTRACT_DIR%\\PDFReader by Sparsh.exe" "%CURRENT_EXE%" >>"%LOG%" 2>&1\n'
            'if errorlevel 1 (\n'
            '    set /a RETRY+=1\n'
            '    if !RETRY! lss 3 (\n'
            '        timeout /t 1 /nobreak >nul\n'
            '        goto retry_copy\n'
            '    )\n'
            '    echo [%date% %time%] ERROR: copy failed after 3 retries >> "%LOG%"\n'
            '    goto check_elevation\n'
            ')\n'
            '\n'
            'goto update_complete\n'
            '\n'
            ':check_elevation\n'
            'echo [%date% %time%] Checking if elevation (admin rights) is needed... >> "%LOG%"\n'
            'net session >nul 2>&1\n'
            'if %errorlevel% neq 0 (\n'
            '    echo [%date% %time%] Not running as admin. Requesting elevation... >> "%LOG%"\n'
            '    echo [%date% %time%] The update needs admin permission to write to "%INSTALL_DIR%". >> "%LOG%"\n'
            '    echo. >> "%LOG%"\n'
            '    echo ================================================================ >> "%LOG%"\n'
            '    echo PDFReader Update - Admin Permission Required >> "%LOG%"\n'
            '    echo ================================================================ >> "%LOG%"\n'
            '    echo. >> "%LOG%"\n'
            '    echo PDFReader needs administrator permission to update itself. >> "%LOG%"\n'
            '    echo The app is installed in a protected location. >> "%LOG%"\n'
            '    echo. >> "%LOG%"\n'
            '    echo A UAC prompt will appear. Please click Yes to continue. >> "%LOG%"\n'
            '    echo. >> "%LOG%"\n'
            '    :: Create a VBS script to request elevation\n'
            '    set VBS=%TEMP%\\_pdfreader_elevate_%TAG%.vbs\n'
            '    echo Set UAC = CreateObject^("Shell.Application"^) > "%VBS%"\n'
            '    echo UAC.ShellExecute "cmd.exe", "/c \\""%BATCH_DIR%\\_update_%TAG%.bat"\\"", "", "runas", 1 >> "%VBS%"\n'
            '    echo [%date% %time%] Elevated re-launch via VBS >> "%LOG%"\n'
            '    cscript //nologo "%VBS%"\n'
            '    del "%VBS%" >nul 2>&1\n'
            '    echo [%date% %time%] Elevation requested, exiting current instance... >> "%LOG%"\n'
            '    del "%~f0" >nul 2>&1\n'
            '    exit /b 0\n'
            ') else (\n'
            '    echo [%date% %time%] Running as admin but copy still failed. >> "%LOG%"\n'
            '    echo [%date% %time%] This may indicate a file-lock or disk issue. >> "%LOG%"\n'
            '    goto fail\n'
            ')\n'
            '\n'
            ':update_complete\n'
            'echo [%date% %time%] Unblocking EXE... >> "%LOG%"\n'
            'powershell -Command "Unblock-File -Path \'%CURRENT_EXE%\'" >>"%LOG%" 2>&1\n'
            '\n'
            'echo [%date% %time%] Launching new version... >> "%LOG%"\n'
            'start "" "%CURRENT_EXE%"\n'
            '\n'
            'echo [%date% %time%] Update successful, cleaning up... >> "%LOG%"\n'
            'rmdir /S /Q "%EXTRACT_DIR%" >>"%LOG%" 2>&1\n'
            'del "%TEMP%\\PDFReader-Updates\\%TAG%.zip" >>"%LOG%" 2>&1\n'
            'del "%~f0" >nul 2>&1\n'
            'exit /b 0\n'
            '\n'
            ':fail\n'
            'echo [%date% %time%] UPDATE FAILED >> "%LOG%"\n'
            'echo. >> "%LOG%"\n'
            'echo ================================================================ >> "%LOG%"\n'
            'echo                        UPDATE FAILED                            >> "%LOG%"\n'
            'echo ================================================================ >> "%LOG%"\n'
            'echo. >> "%LOG%"\n'
            'echo PDFReader could not complete the update. >> "%LOG%"\n'
            'if /i "%INSTALL_DIR%"=="%PROGRAMFILES%\\PDFReader by Sparsh" (\n'
            '    echo. >> "%LOG%"\n'
            '    echo The app is installed in a protected system directory. >> "%LOG%"\n'
            '    echo You may need to run the installer manually as Administrator. >> "%LOG%"\n'
            '    echo. >> "%LOG%"\n'
            '    echo Alternatively, download the latest version from: >> "%LOG%"\n'
            '    echo https://github.com/sparshsam/pdfreader-by-sparsh/releases >> "%LOG%"\n'
            ') >> "%LOG%"\n'
            'start "" notepad "%LOG%"\n'
            'echo. & echo. & echo UPDATE FAILED - see log above for details. & echo. & echo Press any key to exit. & pause >nul\n'
            'exit /b 1\n'
        )

        try:
            with open(bat_path, "w") as f:
                f.write(bat_content)
            subprocess.Popen(  # nosec B603, B607 — Windows self-update
                ["cmd.exe", "/c", str(bat_path)],
                creationflags=0x08000000,  # CREATE_NO_WINDOW
            )
            self._log_update("success=launched Windows ZIP updater")
        except Exception as exc:
            self._log_update(f"failure=could not launch update script: {exc}")
            QMessageBox.critical(
                self, "Update Error",
                "<h3>Update Could Not Start</h3>"
                "<p>PDFReader was unable to launch the update script.</p>"
                "<hr>"
                "<p><b>What happened:</b><br>"
                f"{exc}</p>"
                "<p><b>What you can do:</b><br>"
                "• Download the latest version manually from the GitHub releases page<br>"
                "• If installed in a protected folder (like Program Files), "
                "try running PDFReader as Administrator and checking for updates again.</p>"
                "<hr>"
                f"<p style='font-size:11px;color:#888;'>Update directory: {script_dir}</p>",
            )
            return

        QMessageBox.information(
            self,
            "Update Starting",
            "<h3>Update Download Complete</h3>"
            "<p>PDFReader will now close and update itself.</p>"
            "<p>It will reopen automatically in a moment.</p>"
            "<hr>"
            "<p style='font-size:12px;color:#888;'>"
            "If you see a UAC (User Account Control) prompt, click <b>Yes</b> "
            "to allow the update to complete.</p>",
        )
        QTimer.singleShot(500, self.close)

    # ------------------------------------------------------------------
    # Workspace Session Restoration
    # ------------------------------------------------------------------

    def _restore_session(self, force=False):
        if not self._auto_restore and not force:
            return
        session = self.settings.value("session", [])
        if not session:
            return
        if not force:
            reply = QMessageBox.question(
                self, "Restore Session",
                "You had documents open when you last closed PDFReader.\n"
                "Would you like to restore them?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply != QMessageBox.Yes:
                return
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
        # Close docs
        for tab_id, tab in self.tabs.items():
            if tab.document is not None:
                try:
                    tab.document.close()
                except Exception:
                    pass  # best-effort document close  # nosec B110
        self.tabs.clear()
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
                self.render_page()
                self.statusBar().showMessage(f"Opened: {r.filename} — page {r.page}", 5000)


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
    app.setOrganizationName("Sparsh")

    # ---- Single-instance IPC: route file opens to existing window ----
    pdf_paths = [a for a in sys.argv[1:] if Path(a).suffix.lower() == ".pdf"]
    if pdf_paths and _try_send_to_existing_instance(pdf_paths):
        # Paths routed to existing instance — exit this one
        sys.exit(0)

    ipc_server = QLocalServer()
    # Clean up any stale server name from a previous crash
    ipc_server.removeServer(IPC_SERVER_NAME)
    ipc_server.listen(IPC_SERVER_NAME)

    # Set app-level icon before window creation for taskbar/Wayland
    icon_path = Path(__file__).parent / "assets" / "pdfreader_by_sparsh.ico"
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
