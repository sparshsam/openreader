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
from PySide6.QtCore import QByteArray, QPoint, QRect, QSettings, QSize, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QImage, QKeySequence, QPainter, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QInputDialog,
    QScrollArea,
    QSpinBox,
    QStatusBar,
    QStyle,
    QTabBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)


__version__ = "0.1.9-dev"
GITHUB_REPO = "sparshsam/pdfreader-by-sparsh"
RECENT_FILES_MAX = 10
SETTINGS_RECENT_KEY = "recentFiles"


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

DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QMainWindow::separator {
    background-color: #313244;
}
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    padding: 4px 12px;
    border-radius: 4px;
    min-height: 22px;
}
QPushButton:hover {
    background-color: #45475a;
}
QPushButton:pressed {
    background-color: #585b70;
}
QPushButton:checked {
    background-color: #89b4fa;
    color: #1e1e2e;
    border-color: #89b4fa;
}
QPushButton:disabled {
    background-color: #313244;
    color: #585b70;
    border-color: #313244;
}
QLineEdit {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    padding: 4px 6px;
    border-radius: 4px;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
}
QLineEdit:focus {
    border-color: #89b4fa;
}
QSpinBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    padding: 4px;
    border-radius: 4px;
}
QSpinBox:focus {
    border-color: #89b4fa;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #45475a;
    border: none;
    width: 18px;
}
QLabel {
    color: #cdd6f4;
    background-color: transparent;
}
QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #313244;
}
QScrollArea {
    background-color: #1e1e2e;
    border: none;
}
QToolBar {
    background-color: #181825;
    border: none;
    border-bottom: 1px solid #313244;
    spacing: 4px;
    padding: 2px 4px;
}
QToolBar QToolButton {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 4px 6px;
    color: #cdd6f4;
}
QToolBar QToolButton:hover {
    background-color: #313244;
}
QToolBar QToolButton:pressed {
    background-color: #45475a;
}
QToolBar QToolButton:disabled {
    color: #585b70;
}
QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    padding: 6px 18px;
    border: none;
    border-right: 1px solid #313244;
    min-height: 24px;
}
QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #89b4fa;
    border-bottom: 2px solid #89b4fa;
}
QTabBar::tab:hover:!selected {
    background-color: #313244;
    color: #cdd6f4;
}
QTabBar::close-button {
    image: none;
    background-color: transparent;
    border: none;
    padding: 2px;
    margin: 2px;
    color: #a6adc8;
}
QTabBar::close-button:hover {
    background-color: #f38ba8;
    border-radius: 3px;
    color: #1e1e2e;
}
QMenuBar {
    background-color: #181825;
    color: #cdd6f4;
    border-bottom: 1px solid #313244;
    padding: 2px;
}
QMenuBar::item {
    padding: 4px 10px;
    background-color: transparent;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background-color: #313244;
}
QMenu {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #45475a;
    padding: 4px;
}
QMenu::item {
    padding: 6px 28px 6px 20px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #45475a;
}
QMenu::item:disabled {
    color: #585b70;
}
QMenu::separator {
    height: 1px;
    background-color: #313244;
    margin: 4px 8px;
}
QProgressDialog {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #45475a;
}
QMessageBox {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QMessageBox QLabel {
    color: #cdd6f4;
}
QMessageBox QPushButton {
    min-width: 80px;
}
QInputDialog {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QScrollBar:horizontal {
    background-color: #181825;
    height: 10px;
    border: none;
}
QScrollBar::handle:horizontal {
    background-color: #45475a;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #585b70;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QScrollBar:vertical {
    background-color: #181825;
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #585b70;
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

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.drag_start = None
        self.drag_current = None
        self.setMouseTracking(True)

    def clear_drag_selection(self):
        self.drag_start = None
        self.drag_current = None
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.pixmap() is not None:
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

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.APP_NAME)
        self.resize(1000, 800)

        self.settings = QSettings("Sparsh", "PDFReader by Sparsh")

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

        # ---- Update system ----
        self._update_nam = QNetworkAccessManager(self)
        self._update_nam.finished.connect(self._on_update_check_reply)
        self._download_nam = QNetworkAccessManager(self)
        self._download_nam.finished.connect(self._on_download_finished)
        self._update_progress = None
        self._update_latest_tag = None
        self._update_asset_name = None
        self._update_download_path = None

        self._build_ui()
        self._build_actions()
        self._build_menus()
        self._apply_theme()
        self._update_controls()
        self._update_recent_menu()

        # Listen for system theme changes
        QApplication.styleHints().colorSchemeChanged.connect(self._on_system_theme_change)

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget(self)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Tab bar
        self.tab_bar = QTabBar()
        self.tab_bar.setTabsClosable(True)
        self.tab_bar.setMovable(True)
        self.tab_bar.setExpanding(False)
        self.tab_bar.setDocumentMode(True)
        self.tab_bar.setDrawBase(False)
        self.tab_bar.setUsesScrollButtons(True)
        self.tab_bar.tabBarDoubleClicked.connect(self._on_tab_double_click)
        self.tab_bar.tabCloseRequested.connect(self._on_tab_close_requested)
        self.tab_bar.currentChanged.connect(self._on_tab_switch)
        root.addWidget(self.tab_bar)

        # Controls bar
        controls_widget = QWidget()
        controls_widget.setContentsMargins(8, 6, 8, 6)
        controls = QHBoxLayout(controls_widget)
        controls.setSpacing(6)
        controls.setContentsMargins(0, 0, 0, 0)

        self.open_button = QPushButton("Open")
        self.prev_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(1)
        self.page_spin.setFixedWidth(80)
        self.page_count_label = QLabel("/ 0")

        self.zoom_out_button = QPushButton("Zoom \u2212")
        self.zoom_in_button = QPushButton("Zoom +")
        self.fit_button = QPushButton("Fit Width")
        self.fit_button.setCheckable(True)
        self.fit_button.setChecked(True)
        self.copy_button = QPushButton("Copy")
        self.merge_button = QPushButton("Merge")
        self.split_button = QPushButton("Split")
        self.compress_button = QPushButton("Compress")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search text")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(180)
        self.search_prev_button = QPushButton("Prev Match")
        self.search_next_button = QPushButton("Next Match")
        self.search_count_label = QLabel("0 matches")

        controls.addWidget(self.open_button)
        controls.addSpacing(8)
        controls.addWidget(self.prev_button)
        controls.addWidget(self.next_button)
        controls.addWidget(QLabel("Page"))
        controls.addWidget(self.page_spin)
        controls.addWidget(self.page_count_label)
        controls.addSpacing(8)
        controls.addWidget(self.zoom_out_button)
        controls.addWidget(self.zoom_in_button)
        controls.addWidget(self.fit_button)
        controls.addWidget(self.copy_button)
        controls.addSpacing(8)
        controls.addWidget(self.merge_button)
        controls.addWidget(self.split_button)
        controls.addWidget(self.compress_button)
        controls.addSpacing(8)
        controls.addWidget(self.search_input, 1)
        controls.addWidget(self.search_prev_button)
        controls.addWidget(self.search_next_button)
        controls.addWidget(self.search_count_label)
        root.addWidget(controls_widget)

        # Page content
        self.page_label = PdfPageLabel("Open a PDF to begin")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setBackgroundRole(self.page_label.backgroundRole())
        self.page_label.selection_finished.connect(self.select_text_in_rect)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.page_label)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidgetResizable(False)
        root.addWidget(self.scroll_area, 1)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar(self))

        # Signal connections
        self.open_button.clicked.connect(self.open_pdf)
        self.prev_button.clicked.connect(self.previous_page)
        self.next_button.clicked.connect(self.next_page)
        self.page_spin.valueChanged.connect(self.jump_to_page)
        self.zoom_out_button.clicked.connect(self.zoom_out)
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.fit_button.toggled.connect(self._on_fit_toggled)
        self.copy_button.clicked.connect(self.copy_selected_text)
        self.merge_button.clicked.connect(self.merge_pdfs)
        self.split_button.clicked.connect(self.split_pdf)
        self.compress_button.clicked.connect(self.compress_pdf)
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
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_pdf)
        toolbar.addAction(open_action)

        toolbar.addSeparator()
        prev_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowBack), "Previous Page", self)
        prev_action.setShortcut(QKeySequence(Qt.Key_PageUp))
        prev_action.triggered.connect(self.previous_page)
        toolbar.addAction(prev_action)

        next_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowForward), "Next Page", self)
        next_action.setShortcut(QKeySequence(Qt.Key_PageDown))
        next_action.triggered.connect(self.next_page)
        toolbar.addAction(next_action)

        toolbar.addSeparator()
        zoom_in_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowUp), "Zoom In", self)
        zoom_in_action.setShortcuts([QKeySequence.ZoomIn, QKeySequence("Ctrl+=")])
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)

        zoom_out_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowDown), "Zoom Out", self)
        zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)

        toolbar.addSeparator()
        copy_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "Copy Selected Text", self)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self.copy_selected_text)
        toolbar.addAction(copy_action)
        self.copy_action = copy_action

        toolbar.addSeparator()
        merge_action = QAction("Merge", self)
        merge_action.triggered.connect(self.merge_pdfs)
        toolbar.addAction(merge_action)

        split_action = QAction("Split", self)
        split_action.triggered.connect(self.split_pdf)
        toolbar.addAction(split_action)

        compress_action = QAction("Compress", self)
        compress_action.triggered.connect(self.compress_pdf)
        toolbar.addAction(compress_action)

        toolbar.addSeparator()
        self.update_action = QAction("Check for Updates", self)
        self.update_action.triggered.connect(self.check_for_updates)
        toolbar.addAction(self.update_action)

        find_action = QAction("Find", self)
        find_action.setShortcut(QKeySequence.Find)
        find_action.triggered.connect(self.focus_search)
        self.addAction(find_action)

        # Close Tab
        close_tab_action = QAction("Close Tab", self)
        close_tab_action.setShortcut(QKeySequence("Ctrl+W"))
        close_tab_action.triggered.connect(self._close_current_tab)
        self.addAction(close_tab_action)

        # New Tab
        new_tab_action = QAction("New Tab", self)
        new_tab_action.setShortcut(QKeySequence("Ctrl+T"))
        new_tab_action.triggered.connect(self.open_pdf)
        self.addAction(new_tab_action)

        for action in (
            open_action,
            prev_action,
            next_action,
            zoom_in_action,
            zoom_out_action,
            copy_action,
            merge_action,
            split_action,
            compress_action,
        ):
            self.addAction(action)

    def _build_menus(self):
        """File / View / Tools / Help menu bar."""
        menubar = self.menuBar()

        # ── File ──
        file_menu = menubar.addMenu("File")

        file_open = QAction("Open PDF", self)
        file_open.setShortcut(QKeySequence.Open)
        file_open.triggered.connect(self.open_pdf)
        file_menu.addAction(file_open)

        file_menu.addSeparator()

        self._recent_menu = QMenu("Open Recent", self)
        file_menu.addMenu(self._recent_menu)

        file_menu.addSeparator()

        close_tab = QAction("Close Tab", self)
        close_tab.setShortcut(QKeySequence("Ctrl+W"))
        close_tab.triggered.connect(self._close_current_tab)
        file_menu.addAction(close_tab)

        close_all = QAction("Close All Tabs", self)
        close_all.setShortcut(QKeySequence("Ctrl+Shift+W"))
        close_all.triggered.connect(self._close_all_tabs)
        file_menu.addAction(close_all)

        file_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

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

        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcuts([QKeySequence.ZoomIn, QKeySequence("Ctrl+=")])
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)

        fit_action = QAction("Fit Width", self, checkable=True)
        fit_action.setChecked(True)
        fit_action.triggered.connect(self._on_fit_toggled)
        view_menu.addAction(fit_action)
        self._fit_menu_action = fit_action

        # ── Tools ──
        tools_menu = menubar.addMenu("Tools")
        tools_menu.addAction("Merge PDFs", self.merge_pdfs)
        tools_menu.addAction("Split PDF", self.split_pdf)
        tools_menu.addAction("Compress PDF", self.compress_pdf)

        # ── Help ──
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("Check for Updates", self.check_for_updates)
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
        # Auto: check system
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
        if self._dark_mode:
            self.setStyleSheet(DARK_STYLESHEET)
        else:
            self.setStyleSheet("")

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
            # Truncate long names
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
        """Double-clicking a tab opens a new PDF."""
        self.open_pdf()

    def _on_tab_switch(self, index: int):
        """Save old tab state, restore new tab state."""
        if index < 0 or index >= self.tab_bar.count():
            return
        new_tab_id = self.tab_bar.tabData(index)
        if new_tab_id is None or new_tab_id == self.current_tab_id:
            return

        # Save old
        self._save_current_state()
        self._save_current_tab_controls()

        # Restore new
        self._restore_state(new_tab_id)
        self._restore_current_tab_controls()
        self.clear_text_selection(render=False)
        self.render_page()
        self._update_controls()

    def _save_current_tab_controls(self):
        """Save UI controls state that isn't in TabData (fit_button checkstate)."""
        if self.current_tab_id is not None and self.current_tab_id in self.tabs:
            pass  # fit_to_window is already saved via _save_current_state

    def _restore_current_tab_controls(self):
        """Restore UI controls from current tab state."""
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
            self.search_count_label.setText("0 matches")

    def _create_tab(self, tab_data: TabData) -> int:
        """Register a tab and add it to the tab bar."""
        tab_id = id(tab_data)
        self.tabs[tab_id] = tab_data
        idx = self.tab_bar.addTab(tab_data.name)
        self.tab_bar.setTabData(idx, tab_id)
        self.tab_bar.setCurrentIndex(idx)
        return tab_id

    def _on_tab_close_requested(self, index: int):
        """Bridge: tab bar close button clicked → resolve tab_id."""
        tab_id = self.tab_bar.tabData(index)
        if tab_id is not None:
            self._close_tab(tab_id)

    def _close_current_tab(self):
        if self.current_tab_id is not None:
            self._close_tab(self.current_tab_id)

    def _close_tab(self, tab_id: int):
        """Close a single tab by its integer ID."""
        if tab_id not in self.tabs:
            return

        tab = self.tabs[tab_id]
        was_current = tab_id == self.current_tab_id

        # Close the document
        if tab.document is not None:
            tab.document.close()

        # Remove from tab bar — this may fire currentChanged and switch tabs
        for i in range(self.tab_bar.count()):
            if self.tab_bar.tabData(i) == tab_id:
                self.tab_bar.removeTab(i)
                break

        del self.tabs[tab_id]

        if not self.tabs:
            # Last tab closed — clear all state
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
            self.page_label.setText("Open a PDF to begin")
            self.page_label.setPixmap(QPixmap())
            self.page_label.adjustSize()
            self._update_controls()
            return

        # If the closed tab was the current one, the tab bar's currentChanged
        # should have already selected a new tab via _on_tab_switch.
        # But guard against the case where removeTab did NOT trigger a switch.
        if was_current and self.current_tab_id is not None and self.current_tab_id not in self.tabs:
            # Fallback: pick the first available
            fallback_id = next(iter(self.tabs.keys()))
            self._restore_state(fallback_id)
            self._restore_current_tab_controls()
            self.clear_text_selection(render=False)
            self.render_page()
            self._update_controls()

    def _close_all_tabs(self):
        """Close all open tabs."""
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
        self.page_label.setText("Open a PDF to begin")
        self.page_label.setPixmap(QPixmap())
        self.page_label.adjustSize()
        self._update_controls()

    # ------------------------------------------------------------------
    # PDF File Operations
    # ------------------------------------------------------------------

    def open_pdf(self, file_name: str | None = None):
        """Open a PDF — if no path given, show file dialog."""
        if file_name is None:
            start_dir = self.settings.value("lastFolder", str(Path.home()))
            file_name, _ = QFileDialog.getOpenFileName(
                self,
                "Open PDF",
                start_dir,
                "PDF Files (*.pdf)",
            )
        if not file_name:
            return

        tab_data = TabData(name=Path(file_name).name)
        self._create_tab(tab_data)
        self.load_pdf(file_name)

    def load_pdf(self, file_name):
        """Load a PDF into the *current* tab."""
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
        self.search_count_label.setText("0 matches")

        self.page_spin.blockSignals(True)
        self.page_spin.setMaximum(self.document.page_count)
        self.page_spin.setValue(1)
        self.page_spin.blockSignals(False)
        self.page_count_label.setText(f"/ {self.document.page_count}")

        self.settings.setValue("lastFolder", str(Path(file_name).parent))
        self._add_recent_file(str(Path(file_name).resolve()))

        # Update tab name
        name = Path(file_name).name
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
        if self.document is None:
            self.page_label.setText("Open a PDF to begin")
            self.page_label.adjustSize()
            return

        try:
            page = self.document.load_page(self.current_page)
            zoom = self._effective_zoom(page)
            self.current_render_zoom = zoom
            self._validate_render_size(page, zoom)
            matrix = fitz.Matrix(zoom, zoom)
            highlight_rects = self._active_highlight_rects()
            pixmap = page.get_pixmap(matrix=matrix, alpha=False, annots=True)
            image = QImage(
                pixmap.samples,
                pixmap.width,
                pixmap.height,
                pixmap.stride,
                QImage.Format_RGB888,
            ).copy()
            if highlight_rects:
                self._paint_highlights(image, page, highlight_rects, zoom)
            if self.selected_rects:
                self._paint_selection(image, page, self.selected_rects, zoom)
        except Exception as exc:
            self._show_error("Render Error", "Unable to render this page.", exc)
            return

        self.page_label.setPixmap(QPixmap.fromImage(image))
        self.page_label.adjustSize()
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(self.current_page + 1)
        self.page_spin.blockSignals(False)
        self._update_controls()

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
        # Kept for backward compat — routes to _on_fit_toggled
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
            self.search_count_label.setText("0 matches")
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
            self.search_count_label.setText("0 matches")
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
            self.search_count_label.setText(f"{len(self.search_results)} matches")

    def _search_count_text(self):
        if self.current_result_index < 0:
            return f"{len(self.search_results)} matches"
        return f"{self.current_result_index + 1} of {len(self.search_results)}"

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
        for page_index in range(self.document.page_count):
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

        self.prev_button.setEnabled(can_go_previous)
        self.next_button.setEnabled(can_go_next)
        self.page_spin.setEnabled(has_document)
        self.zoom_in_button.setEnabled(has_document)
        self.zoom_out_button.setEnabled(has_document)
        self.fit_button.setEnabled(has_document)
        self.copy_button.setEnabled(has_document and bool(self.selected_text))
        self.split_button.setEnabled(has_document)
        self.compress_button.setEnabled(has_document)
        self.merge_button.setEnabled(True)
        if hasattr(self, "copy_action"):
            self.copy_action.setEnabled(has_document and bool(self.selected_text))
        self.search_input.setEnabled(has_document)
        self.search_prev_button.setEnabled(has_document and has_matches)
        self.search_next_button.setEnabled(has_document and has_matches)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.fit_to_window and self.document is not None:
            self.render_page()

    def _show_about(self):
        QMessageBox.about(
            self,
            f"About {self.APP_NAME}",
            f"<h3>{self.APP_NAME}</h3>"
            f"<p>Version {__version__}</p>"
            f"<p>Built with Python, PySide6, and PyMuPDF.</p>"
            f"<p>Local-first. Private. No cloud uploads.</p>"
        )

    # ------------------------------------------------------------------
    # Auto-update system
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_version(tag):
        """Parse a version tag like 'v0.1.3' into a comparable tuple."""
        match = re.search(r"(\d+)\.(\d+)\.(\d+)", tag)
        if not match:
            return None
        return tuple(int(x) for x in match.groups())

    @staticmethod
    def _is_packaged():
        """Return True if running from a PyInstaller bundle."""
        return getattr(sys, "frozen", False)

    def _get_platform_asset(self, assets):
        """Pick the right download asset for the current platform."""
        system = platform.system()
        if system == "Windows":
            for a in assets:
                name = a.get("name", "")
                if name.endswith(".zip"):
                    return a["browser_download_url"], a["name"]
        elif system == "Darwin":
            is_arm = platform.machine() in ("arm64", "aarch64")
            for a in assets:
                name = a.get("name", "")
                if is_arm and "Apple-Silicon" in name and name.endswith(".zip"):
                    return a["browser_download_url"], a["name"]
            for a in assets:
                name = a.get("name", "")
                if "macOS" in name and name.endswith(".zip"):
                    return a["browser_download_url"], a["name"]
        return None, None

    def check_for_updates(self):
        """Check GitHub for a newer release. Called from the UI."""
        if self._update_progress is not None:
            return  # already in progress

        self.update_action.setEnabled(False)
        self.statusBar().showMessage("Checking for updates...")

        url = QUrl(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.UserAgentHeader, "PDFReader-by-Sparsh/1.0")
        request.setTransferTimeout(15000)
        self._update_nam.get(request)

    def _on_update_check_reply(self, reply):
        """Handle the GitHub API response for the update check."""
        self.update_action.setEnabled(True)

        if reply.error() != QNetworkReply.NoError:
            self.statusBar().showMessage("Could not check for updates — check your internet connection", 5000)
            reply.deleteLater()
            return

        try:
            data = json.loads(bytes(reply.readAll()).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.statusBar().showMessage("Update check failed — unexpected response", 5000)
            reply.deleteLater()
            return
        finally:
            reply.deleteLater()

        latest_tag = data.get("tag_name", "")
        latest_version = self._parse_version(latest_tag)
        current_version = self._parse_version(__version__)

        if latest_version is None or current_version is None:
            QMessageBox.information(
                self,
                "Update Check",
                f"Current version: {__version__}\nLatest release: {latest_tag}\n\nCould not compare versions.",
            )
            return

        assets = data.get("assets", [])
        asset_url, asset_name = self._get_platform_asset(assets)

        if latest_version <= current_version:
            QMessageBox.information(
                self,
                "Up to Date",
                f"You're running {__version__}, which is the latest version.",
            )
            self.statusBar().showMessage(f"PDFReader is up to date (v{__version__})", 5000)
            return

        # An update is available
        release_url = data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases")
        release_notes = (data.get("body") or "")[:500]

        msg = (
            f"<h3>Update Available</h3>"
            f"<p><b>v{'.'.join(str(x) for x in current_version)}</b> → <b>{latest_tag}</b></p>"
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
            # No platform binary — open the releases page
            import webbrowser
            webbrowser.open(release_url)
            self.statusBar().showMessage(
                "No installer for your platform. Opening releases page.", 5000
            )

    def _start_download(self, asset_url, asset_name, latest_tag):
        """Download the update asset with progress feedback."""
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
        request.setTransferTimeout(300000)  # 5 min
        reply = self._download_nam.get(request)
        reply.downloadProgress.connect(self._on_download_progress)

    def _on_download_progress(self, received, total):
        """Update the progress dialog during download."""
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
        """Cancel an in-progress download."""
        self._download_nam.finished.disconnect(self._on_download_finished)
        self._download_nam = QNetworkAccessManager(self)
        self._download_nam.finished.connect(self._on_download_finished)
        self._update_progress = None
        self._update_latest_tag = None
        self._update_asset_name = None
        self.update_action.setEnabled(True)
        self.statusBar().showMessage("Download cancelled", 3000)

    def _on_download_finished(self, reply):
        """Save the downloaded file and start the install."""
        self.update_action.setEnabled(True)

        # Snapshot before closing progress (closing emits canceled -> _cancel_download -> nulls these)
        asset_name = self._update_asset_name
        latest_tag = self._update_latest_tag

        if self._update_progress is not None:
            self._update_progress.close()
            self._update_progress = None

        if reply.error() != QNetworkReply.NoError:
            QMessageBox.critical(
                self,
                "Download Failed",
                f"Could not download the update:\n{reply.errorString()}",
            )
            reply.deleteLater()
            return

        # Save to a temp location
        try:
            temp_dir = Path(tempfile.gettempdir()) / "PDFReader-Updates"
            temp_dir.mkdir(parents=True, exist_ok=True)
            # Use the original asset name (GitHub CDN redirects strip it)
            file_name = asset_name or f"update_{latest_tag}"
            dest = temp_dir / file_name
            data = reply.readAll()
            with open(dest, "wb") as f:
                f.write(bytes(data))
            self._update_download_path = dest
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Download Failed",
                f"Could not save the downloaded file:\n{exc}",
            )
            reply.deleteLater()
            return
        finally:
            reply.deleteLater()

        self._apply_update(latest_tag, asset_name)

    def _apply_update(self, tag="latest", asset_name=""):
        """Seamlessly replace the running app and restart."""
        dest = self._update_download_path
        if dest is None or not dest.exists():
            QMessageBox.critical(self, "Update Error", "Update file not found.")
            return

        system = platform.system()
        tag = tag or "latest"

        if system == "Windows" and dest.suffix.lower() == ".exe":
            self._apply_update_windows(dest, tag)
        elif system == "Windows" and dest.suffix.lower() == ".zip":
            self._apply_update_windows_zip(dest, tag)
        elif system == "Darwin" and dest.suffix.lower() == ".zip":
            self._apply_update_macos(dest, tag)
        else:
            QMessageBox.information(
                self,
                "Update Downloaded",
                f"The update has been saved to:\n\n{dest}\n\nPlease install it manually.",
            )
            return

    def _apply_update_windows(self, dest, tag):
        """Replace the running exe in-place via a background batch updater."""
        current_exe = Path(sys.executable)
        if not current_exe.exists():
            QMessageBox.critical(self, "Update Error", "Could not locate the app executable.")
            return

        bat_path = current_exe.parent / f"_update_{tag}.bat"
        # Use a helper script in the same directory to avoid PATH issues
        bat_content = (
            "@echo off\n"
            "title=PDFReader Updater\n"
            "echo Updating PDFReader by Sparsh...\n"
            "\n"
            ":wait\n"
            f'tasklist /FI "PID eq {os.getpid()}" 2>nul | find "{os.getpid()}" >nul\n'
            "if not errorlevel 1 (\n"
            "    timeout /t 1 /nobreak >nul\n"
            "    goto wait\n"
            ")\n"
            "\n"
            "rem Extra buffer for Defender / cleanup\n"
            "timeout /t 2 /nobreak >nul\n"
            "\n"
            ":retry\n"
            f'copy /Y /V "{dest}" "{current_exe}" >nul\n'
            "if errorlevel 1 (\n"
            "    timeout /t 1 /nobreak >nul\n"
            "    goto retry\n"
            ")\n"
            "\n"
            f'powershell -Command "Unblock-File -Path \'{current_exe}\'" >nul 2>&1\n'
            f'start "" /D "{current_exe.parent}" "{current_exe}"\n'
            f'del "{dest}" >nul 2>&1\n'
            'del "%~f0" >nul 2>&1\n'
        )

        try:
            with open(bat_path, "w") as f:
                f.write(bat_content)
            subprocess.Popen(  # nosec B603, B607 — intentional self-update, hardcoded args
                ["cmd.exe", "/c", str(bat_path)],
                creationflags=0x08000000,  # CREATE_NO_WINDOW
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Update Error",
                f"Could not launch the update script.\n\n{exc}",
            )
            return

        QMessageBox.information(
            self,
            "Update Starting",
            "PDFReader will now close and update itself."
            " It will reopen automatically in a moment.",
        )
        QTimer.singleShot(500, self.close)

    def _apply_update_windows_zip(self, dest, tag):
        """Replace the running app via ZIP extract + batch updater (onedir mode)."""
        current_exe = Path(sys.executable)
        app_dir = current_exe.parent
        if not app_dir.exists():
            QMessageBox.critical(self, "Update Error", "Could not locate the app directory.")
            return

        # Extract ZIP to a temp folder
        extract_dir = dest.parent / f"extracted_{tag}"
        try:
            if extract_dir.exists():
                import shutil
                shutil.rmtree(extract_dir)
            with zipfile.ZipFile(str(dest), "r") as zf:
                zf.extractall(str(extract_dir))
        except Exception as exc:
            QMessageBox.critical(
                self, "Update Error",
                f"Could not extract the update.\n\n{exc}",
            )
            return

        bat_path = app_dir / f"_update_{tag}.bat"
        bat_content = (
            "@echo off\n"
            "title=PDFReader Updater\n"
            "echo Updating PDFReader by Sparsh...\n"
            "\n"
            ":wait\n"
            f'tasklist /FI "PID eq {os.getpid()}" 2>nul | find "{os.getpid()}" >nul\n'
            "if not errorlevel 1 (\n"
            "    timeout /t 1 /nobreak >nul\n"
            "    goto wait\n"
            ")\n"
            "\n"
            f'xcopy /E /I /Y "{extract_dir}\\_internal" "{app_dir}\\_internal" >nul\n'
            "if errorlevel 1 (\n"
            "    exit /b 1\n"
            ")\n"
            "\n"
            f'copy /Y /V "{extract_dir}\\PDFReader by Sparsh.exe" "{current_exe}" >nul\n'
            "if errorlevel 1 (\n"
            "    exit /b 1\n"
            ")\n"
            "\n"
            f'powershell -Command "Unblock-File -Path \'{current_exe}\'" >nul 2>&1\n'
            f'start "" "{current_exe}"\n'
            f'rmdir /S /Q "{extract_dir}" >nul 2>&1\n'
            f'del "{dest}" >nul 2>&1\n'
            "del \"%~f0\" >nul 2>&1\n"
        )

        try:
            with open(bat_path, "w") as f:
                f.write(bat_content)
            subprocess.Popen(  # nosec
                ["cmd.exe", "/c", str(bat_path)],
                creationflags=0x08000000,
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Update Error",
                f"Could not launch the update script.\n\n{exc}",
            )
            return

        QMessageBox.information(
            self,
            "Update Starting",
            "PDFReader will now close and update itself."
            " It will reopen automatically in a moment.",
        )
        QTimer.singleShot(500, self.close)

    def _apply_update_macos(self, dest, tag):
        """Replace the running .app bundle in-place via a shell updater (onedir ZIP)."""
        current_exe = Path(sys.executable)
        # Find the .app bundle
        app_bundle = None
        for parent in current_exe.parents:
            if parent.suffix == ".app":
                app_bundle = parent
                break

        if app_bundle is None:
            QMessageBox.critical(
                self, "Update Error",
                "Could not locate the current application bundle.",
            )
            return

        # Extract the new .app from the downloaded zip
        extract_dir = dest.parent / f"extracted_{tag}"
        try:
            if extract_dir.exists():
                import shutil
                shutil.rmtree(extract_dir)
            with zipfile.ZipFile(str(dest), "r") as zf:
                zf.extractall(str(extract_dir))
            new_apps = list(extract_dir.rglob("*.app"))
            if not new_apps:
                raise Exception("No .app bundle found in the downloaded update.")
            new_app = new_apps[0]
        except Exception as exc:
            QMessageBox.critical(
                self, "Update Error",
                f"Could not extract the update.\n\n{exc}",
            )
            return

        # Shell script lives next to the app bundle (not in extract_dir which gets cleaned)
        script_path = app_bundle.parent / f"_update_{tag}.sh"
        new_app_str = str(new_app)
        app_bundle_str = str(app_bundle)
        extract_str = str(extract_dir)
        dest_str = str(dest)

        script_content = (
            "#!/bin/bash\n"
            "set -e\n"
            "\n"
            "# PDFReader macOS updater\n"
            f"MY_PID={os.getpid()}\n"
            "\n"
            "# Wait for this process to fully exit\n"
            'while kill -0 "$MY_PID" 2>/dev/null; do\n'
            "    sleep 1\n"
            "done\n"
            "\n"
            "# Extra buffer for macOS to release file handles\n"
            "sleep 2\n"
            "\n"
            "# Remove old app bundle\n"
            f'rm -rf "{app_bundle_str}"\n'
            "\n"
            "# Copy new app with retry\n"
            "RETRIES=0\n"
            f'until ditto "{new_app_str}" "{app_bundle_str}" 2>/dev/null || [ $RETRIES -ge 3 ]; do\n'
            "    RETRIES=$((RETRIES + 1))\n"
            "    sleep 1\n"
            "done\n"
            "\n"
            "# Clear quarantine attributes to avoid Gatekeeper issues\n"
            f'xattr -cr "{app_bundle_str}" 2>/dev/null || true\n'
            "\n"
            "# Clean up\n"
            f'rm -rf "{extract_str}"\n'
            f'rm -f "{dest_str}"\n'
            'rm -f "$0"\n'
            "\n"
            "# Launch new version\n"
            f'open "{app_bundle_str}"\n'
        )
        try:
            with open(script_path, "w") as f:
                f.write(script_content)
            os.chmod(script_path, 0o700)
            subprocess.Popen(["/bin/bash", str(script_path)])  # nosec B603 — intentional self-update
        except Exception as exc:
            QMessageBox.critical(
                self, "Update Error",
                f"Could not launch the update script.\n\n{exc}",
            )
            return

        QMessageBox.information(
            self,
            "Update Starting",
            "PDFReader will now close and update itself."
            " It will reopen automatically in a moment.",
        )
        QTimer.singleShot(500, self.close)

    def closeEvent(self, event):
        # Save all open tab states before closing
        self._save_current_state()
        for tab_id, tab in self.tabs.items():
            if tab.document is not None:
                tab.document.close()
        self.tabs.clear()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(PdfReaderWindow.APP_NAME)
    app.setOrganizationName("Sparsh")
    window = PdfReaderWindow()
    window.show()
    if len(sys.argv) > 1:
        initial_path = sys.argv[1]
        QTimer.singleShot(0, lambda: window.load_pdf(initial_path))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
