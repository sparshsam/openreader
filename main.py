"""PDFReader by Sparsh — Main window and application entry point.

This module defines the ``PdfReaderWindow`` (QMainWindow), the
``PdfPageLabel`` widget, and three internal dialog classes
(``_LibraryDialog``, ``_LibrarySearchResultsDialog``, ``_CompareDialog``).

Architecture-heavy logic — updater, PDF validation, PDF tools, theme
management, and the ``TabData`` container — lives in ``pdfreader_lib/``
so it can be tested and maintained independently.
"""

import json
import os
import platform
import re
import subprocess  # nosec B404 — needed for self-update mechanism
import sys
import tempfile
import zipfile
from collections import OrderedDict
from pathlib import Path

import fitz
from PySide6.QtCore import QByteArray, QPoint, QRect, QSettings, QSize, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QImage, QKeySequence, QPainter, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
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
    QSpinBox,
    QSplitter,
    QStatusBar,
    QStyle,
    QTabBar,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from pdfreader_lib import (
    PdfSafetyError,
    validate_pdf_path,
    validate_document_pages,
    safe_open_pdf,
    TabData,
    DARK_STYLESHEET,
    ThemeManager,
    THEME_AUTO,
    THEME_LIGHT,
    THEME_DARK,
    PdfUpdater,
    GITHUB_REPO,
    WINDOWS_UPDATE_ASSET,
    MACOS_APPLE_SILICON_UPDATE_ASSET,
    MACOS_INTEL_UPDATE_ASSET,
    merge_pdfs as pdf_merge,
    split_every_page,
    extract_pages,
    parse_page_ranges,
    compress_pdf as pdf_compress,
)

# Optional modules (graceful if missing)
try:
    from pdfreader_lib import search_index as lib_idx
    from pdfreader_lib import comparison as pdf_compare
    HAS_LIB_MODULES = True
except ImportError:
    HAS_LIB_MODULES = False


__version__ = "0.4.0-dev"
RECENT_FILES_MAX = 10
SETTINGS_RECENT_KEY = "***"


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------


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
    THEME_AUTO = THEME_AUTO
    THEME_LIGHT = THEME_LIGHT
    THEME_DARK = THEME_DARK

    # Annotation colors
    ANNOT_HIGHLIGHT = (1.0, 0.882, 0.235)      # yellow
    ANNOT_UNDERLINE = (0.075, 0.533, 0.867)    # blue
    ANNOT_STRIKEOUT = (0.953, 0.318, 0.302)    # red

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

        # ---- Theme ----
        theme_value = self.settings.value("theme", THEME_AUTO, int)
        self._theme_manager = ThemeManager(theme_value)
        self._dark_mode = self._theme_manager.is_dark()

        # ---- Recent files ----
        self._recent_files = self._load_recent_files()

        # ---- Workspace session ----
        self._auto_restore = self.settings.value("autoRestore", True, bool)
        self._session_data: list[dict] | None = None

        # ---- Update system ----
        self._updater = PdfUpdater(self)
        self._updater.set_version(__version__)

        self._build_ui()
        self._build_actions()
        self._build_menus()
        self._apply_theme()
        self._update_controls()
        self._update_recent_menu()

        # Listen for system theme changes
        QApplication.styleHints().colorSchemeChanged.connect(self._on_system_theme_change)

        # Restore workspace if available
        QTimer.singleShot(100, self._restore_session)

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
        controls.setSpacing(4)
        controls.setContentsMargins(0, 0, 0, 0)

        self.open_button = QPushButton("Open")
        self.prev_button = QPushButton("Prev")
        self.next_button = QPushButton("Next")
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(1)
        self.page_spin.setFixedWidth(70)
        self.page_count_label = QLabel("/ 0")

        self.zoom_out_button = QPushButton("\u2212")
        self.zoom_out_button.setFixedWidth(30)
        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setFixedWidth(30)
        self.fit_button = QPushButton("Fit")
        self.fit_button.setCheckable(True)
        self.fit_button.setChecked(True)
        self.fit_button.setFixedWidth(40)
        self.copy_button = QPushButton("Copy")

        controls.addWidget(self.open_button)
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
        controls.addSpacing(8)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search in document\u2026")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedWidth(200)
        self.semantic_cb = QCheckBox("Semantic")
        self.semantic_cb.setToolTip("Search indexed PDF library instead of the current document")
        self.semantic_cb.setVisible(HAS_LIB_MODULES)
        self.search_prev_button = QPushButton("\u25b2")
        self.search_prev_button.setFixedWidth(30)
        self.search_prev_button.setToolTip("Previous match")
        self.search_next_button = QPushButton("\u25bc")
        self.search_next_button.setFixedWidth(30)
        self.search_next_button.setToolTip("Next match")
        self.search_count_label = QLabel("0")
        self.search_count_label.setFixedWidth(30)

        controls.addWidget(self.search_input)
        controls.addWidget(self.semantic_cb)
        controls.addWidget(self.search_prev_button)
        controls.addWidget(self.search_next_button)
        controls.addWidget(self.search_count_label)
        controls.addSpacing(8)

        # PDF tool buttons
        self.merge_button = QPushButton("Merge")
        self.split_button = QPushButton("Split")
        self.compress_button = QPushButton("Compress")
        self.compare_button = QPushButton("Compare")
        self.compare_button.setEnabled(HAS_LIB_MODULES)
        self.library_button = QPushButton("Library")
        self.library_button.setEnabled(HAS_LIB_MODULES)

        controls.addWidget(self.merge_button)
        controls.addWidget(self.split_button)
        controls.addWidget(self.compress_button)
        controls.addWidget(self.compare_button)
        controls.addWidget(self.library_button)

        controls.addStretch()
        root.addWidget(controls_widget)

        # PDF view area
        self.scroll_area = QScrollArea()
        self.page_label = PdfPageLabel()
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setWordWrap(False)
        self.page_label.setText("Open a PDF to begin")
        self.page_label.setMinimumSize(400, 400)
        self.scroll_area.setWidget(self.page_label)
        self.scroll_area.setWidgetResizable(False)
        root.addWidget(self.scroll_area, 1)

        # Status bar
        self.statusBar().showMessage("Ready")

        # Connect signals
        self.open_button.clicked.connect(self.open_pdf)
        self.prev_button.clicked.connect(self.previous_page)
        self.next_button.clicked.connect(self.next_page)
        self.page_spin.valueChanged.connect(self.jump_to_page)
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_out_button.clicked.connect(self.zoom_out)
        self.fit_button.toggled.connect(self._on_fit_toggled)
        self.copy_button.clicked.connect(self.copy_selected_text)
        self.highlight_button.clicked.connect(self.highlight_selection)
        self.underline_button.clicked.connect(self.underline_selection)
        self.strike_button.clicked.connect(self.strikeout_selection)
        self.sticky_button.toggled.connect(self._toggle_sticky_note_mode)
        self.merge_button.clicked.connect(self.merge_pdfs)
        self.split_button.clicked.connect(self.split_pdf)
        self.compress_button.clicked.connect(self.compress_pdf)
        self.compare_button.clicked.connect(self._open_compare_dialog)
        self.library_button.clicked.connect(self._open_library_dialog)
        self.search_input.textChanged.connect(self._search_text_changed)
        self.search_prev_button.clicked.connect(self.previous_search_result)
        self.search_next_button.clicked.connect(self.next_search_result)
        self.page_label.selection_finished.connect(self.select_text_in_rect)
        self.page_label.sticky_note_requested.connect(self._place_sticky_note)

        self.setCentralWidget(central)

    def _build_actions(self):
        # File
        self._open_action = QAction("&Open PDF\u2026", self)
        self._open_action.setShortcut(QKeySequence.Open)
        self._open_action.triggered.connect(self.open_pdf)

        self._close_action = QAction("&Close Tab", self)
        self._close_action.setShortcut(QKeySequence("Ctrl+W"))
        self._close_action.triggered.connect(self._close_current_tab)

        self._close_all_action = QAction("C&lose All Tabs", self)
        self._close_all_action.setShortcut(QKeySequence("Ctrl+Shift+W"))
        self._close_all_action.triggered.connect(self._close_all_tabs)

        self._exit_action = QAction("E&xit", self)
        self._exit_action.setShortcut(QKeySequence.Quit)
        self._exit_action.triggered.connect(self.close)

        # Edit
        self.copy_action = QAction("&Copy", self)
        self.copy_action.setShortcut(QKeySequence.Copy)
        self.copy_action.triggered.connect(self.copy_selected_text)

        # View
        self._zoom_in_action = QAction("Zoom &In", self)
        self._zoom_in_action.setShortcut(QKeySequence.ZoomIn)
        self._zoom_in_action.triggered.connect(self.zoom_in)

        self._zoom_out_action = QAction("Zoom &Out", self)
        self._zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        self._zoom_out_action.triggered.connect(self.zoom_out)

        self._fit_action = QAction("&Fit to Window", self)
        self._fit_action.setCheckable(True)
        self._fit_action.setChecked(True)
        self._fit_action.setShortcut(QKeySequence("Ctrl+0"))
        self._fit_action.triggered.connect(self.set_fit_to_window)
        self._fit_menu_action = self._fit_action

        # Annotations
        self._highlight_action = QAction("&Highlight", self)
        self._highlight_action.setShortcut(QKeySequence("Ctrl+H"))
        self._highlight_action.triggered.connect(self.highlight_selection)

        self._underline_action = QAction("&Underline", self)
        self._underline_action.setShortcut(QKeySequence("Ctrl+U"))
        self._underline_action.triggered.connect(self.underline_selection)

        self._strike_action = QAction("&Strikethrough", self)
        self._strike_action.setShortcut(QKeySequence("Ctrl+K"))
        self._strike_action.triggered.connect(self.strikeout_selection)

        self._delete_annotations_action = QAction("&Delete All Annotations on Page", self)
        self._delete_annotations_action.triggered.connect(self._delete_page_annotations)

        self._delete_all_annotations_action = QAction("Delete All Annotations in &Document", self)
        self._delete_all_annotations_action.triggered.connect(self._delete_all_annotations)

        self._save_annotations_action = QAction("&Save Annotations (Ctrl+S alternative)", self)
        self._save_annotations_action.setShortcut(QKeySequence("Ctrl+S"))
        self._save_annotations_action.triggered.connect(self._save_document_annotations)

        self._save_doc_action = QAction("Save &Document Copy\u2026", self)
        self._save_doc_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self._save_doc_action.triggered.connect(self._save_document)

        # Search
        self._search_action = QAction("&Find\u2026", self)
        self._search_action.setShortcut(QKeySequence.Find)
        self._search_action.triggered.connect(self.focus_search)

        # Navigation
        self._next_page_action = QAction("&Next Page", self)
        self._next_page_action.setShortcut(QKeySequence("Right"))
        self._next_page_action.triggered.connect(self.next_page)

        self._prev_page_action = QAction("&Previous Page", self)
        self._prev_page_action.setShortcut(QKeySequence("Left"))
        self._prev_page_action.triggered.connect(self.previous_page)

        # Theme
        self.theme_auto_action = QAction("&Auto", self)
        self.theme_auto_action.setCheckable(True)
        self.theme_auto_action.setChecked(True)
        self.theme_auto_action.triggered.connect(lambda: self.set_theme(THEME_AUTO))

        self.theme_light_action = QAction("&Light", self)
        self.theme_light_action.setCheckable(True)
        self.theme_light_action.triggered.connect(lambda: self.set_theme(THEME_LIGHT))

        self.theme_dark_action = QAction("&Dark", self)
        self.theme_dark_action.setCheckable(True)
        self.theme_dark_action.triggered.connect(lambda: self.set_theme(THEME_DARK))

        # Update
        self.update_action = QAction("Check for &Updates\u2026", self)
        self.update_action.triggered.connect(lambda: self._updater.check_for_updates(self.update_action))

        # Help
        self._about_action = QAction("&About PDFReader by Sparsh", self)
        self._about_action.triggered.connect(self._show_about)

    def _build_menus(self):
        menu_bar = self.menuBar()
        # File
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self._open_action)
        self._recent_menu = file_menu.addMenu("Open &Recent")
        self._recent_menu.setToolTipsVisible(True)
        file_menu.addSeparator()
        file_menu.addAction(self._close_action)
        file_menu.addAction(self._close_all_action)
        file_menu.addSeparator()
        file_menu.addAction(self._save_annotations_action)
        file_menu.addAction(self._save_doc_action)
        file_menu.addSeparator()
        file_menu.addAction(self._exit_action)

        # Edit
        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(self.copy_action)

        # View
        view_menu = menu_bar.addMenu("&View")
        view_menu.addAction(self._zoom_in_action)
        view_menu.addAction(self._zoom_out_action)
        view_menu.addAction(self._fit_action)
        view_menu.addSeparator()
        view_menu.addAction(self._prev_page_action)
        view_menu.addAction(self._next_page_action)
        view_menu.addSeparator()
        view_menu.addAction(self._search_action)
        view_menu.addSeparator()

        theme_menu = view_menu.addMenu("&Theme")
        theme_menu.addAction(self.theme_auto_action)
        theme_menu.addAction(self.theme_light_action)
        theme_menu.addAction(self.theme_dark_action)

        # Annotations
        annot_menu = menu_bar.addMenu("&Annotations")
        annot_menu.addAction(self._highlight_action)
        annot_menu.addAction(self._underline_action)
        annot_menu.addAction(self._strike_action)
        annot_menu.addSeparator()
        annot_menu.addAction(self._delete_annotations_action)
        annot_menu.addAction(self._delete_all_annotations_action)

        # Tools
        tools_menu = menu_bar.addMenu("&Tools")
        tools_menu.addAction("&Merge PDFs\u2026", self.merge_pdfs)
        tools_menu.addAction("&Split PDF\u2026", self.split_pdf)
        tools_menu.addAction("&Compress PDF\u2026", self.compress_pdf)
        tools_menu.addAction("&Compare PDFs\u2026", self._open_compare_dialog)
        tools_menu.addAction("&Library\u2026", self._open_library_dialog)
        tools_menu.addSeparator()
        tools_menu.addAction(self.update_action)

        # Help
        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction(self._about_action)

    # ------------------------------------------------------------------
    # Theme / Dark Mode
    # ------------------------------------------------------------------

    def _compute_dark_mode(self) -> bool:
        return self._theme_manager.is_dark()

    def _on_system_theme_change(self, scheme):
        if self._theme_manager.theme == THEME_AUTO:
            self._dark_mode = scheme == Qt.ColorScheme.Dark
            self._apply_theme()

    def _sync_theme_menu_checks(self):
        t = self._theme_manager.theme
        self.theme_auto_action.setChecked(t == THEME_AUTO)
        self.theme_light_action.setChecked(t == THEME_LIGHT)
        self.theme_dark_action.setChecked(t == THEME_DARK)

    def set_theme(self, theme):
        self._theme_manager.theme = theme
        self.settings.setValue("theme", theme)
        self._sync_theme_menu_checks()
        self._dark_mode = self._theme_manager.is_dark()
        self._apply_theme()

    def _apply_theme(self):
        self._theme_manager.apply(self)

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
        tab_id = id(tab_data)
        self.tabs[tab_id] = tab_data
        idx = self.tab_bar.addTab(tab_data.name)
        self.tab_bar.setTabData(idx, tab_id)
        self.tab_bar.setCurrentIndex(idx)
        return tab_id

    def _on_tab_close_requested(self, index: int):
        tab_id = self.tab_bar.tabData(index)
        if tab_id is not None:
            self._close_tab(tab_id)

    def _close_current_tab(self):
        if self.current_tab_id is not None:
            self._close_tab(self.current_tab_id)

    def _close_tab(self, tab_id: int):
        if tab_id not in self.tabs:
            return
        tab = self.tabs[tab_id]
        was_current = tab_id == self.current_tab_id
        if tab.document is not None:
            tab.document.close()
        for i in range(self.tab_bar.count()):
            if self.tab_bar.tabData(i) == tab_id:
                self.tab_bar.removeTab(i)
                break
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
            self.page_label.setText("Open a PDF to begin")
            self.page_label.setPixmap(QPixmap())
            self.page_label.adjustSize()
            self._update_controls()
            return

        if was_current and self.current_tab_id is not None and self.current_tab_id not in self.tabs:
            fallback_id = next(iter(self.tabs.keys()))
            self._restore_state(fallback_id)
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
        self.page_label.setText("Open a PDF to begin")
        self.page_label.setPixmap(QPixmap())
        self.page_label.adjustSize()
        self._update_controls()

    # ------------------------------------------------------------------
    # PDF File Operations
    # ------------------------------------------------------------------

    def open_pdf(self, file_name: str | None = None):
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
            self.settings.setValue("lastFolder", str(Path(file_name).parent))

        self.load_pdf(file_name)

    def load_pdf(self, file_name):
        try:
            document = safe_open_pdf(
                file_name,
                max_size_bytes=self.MAX_PDF_SIZE_BYTES,
                max_page_dimension=self.MAX_PAGE_DIMENSION_POINTS,
            )
        except PdfSafetyError as exc:
            QMessageBox.critical(self, "Cannot Open PDF", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(
                self, "Cannot Open PDF",
                "The file could not be processed safely.\n\n"
                f"Exception: {exc.__class__.__name__}: {exc}"
            )
            return

        # Close existing document if any
        if self.document is not None:
            self.document.close()

        tab = TabData(name=self._next_tab_name())
        tab.document = document
        tab.path = str(Path(file_name).resolve())
        tab.current_page = 0
        tab.zoom = 1.25
        tab.fit_to_window = True

        self._create_tab(tab)
        self._restore_state(id(tab))
        self._restore_current_tab_controls()
        self.render_page()
        self._update_controls()
        self._add_recent_file(tab.path)
        page_count = document.page_count
        self.page_spin.blockSignals(True)
        self.page_spin.setMaximum(page_count)
        self.page_spin.blockSignals(False)
        self.page_count_label.setText(f"/ {page_count}")
        self.setWindowTitle(f"{Path(file_name).name} - {self.APP_NAME}")
        self.statusBar().showMessage(f"Opened {Path(file_name).name} ({page_count} pages)", 5000)

    def _safe_open_pdf(self, file_name):
        """Convenience wrapper for the module-level safe_open_pdf."""
        return safe_open_pdf(
            file_name,
            max_size_bytes=self.MAX_PDF_SIZE_BYTES,
            max_page_dimension=self.MAX_PAGE_DIMENSION_POINTS,
        )

    def _show_error(self, title, public_message, exception):
        detail = str(exception) if isinstance(exception, PdfSafetyError) else "The file could not be processed safely."
        QMessageBox.critical(self, title, f"{public_message}\n\n{detail}")

    def close_document(self):
        if self.document is not None:
            self.document.close()
        self.document = None

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render_page(self):
        if self.document is None:
            return
        if self.current_page < 0 or self.current_page >= self.document.page_count:
            return
        page = self.document.load_page(self.current_page)
        zoom = self._effective_zoom(page)
        self.current_render_zoom = zoom
        try:
            self._validate_render_size(page, zoom)
        except PdfSafetyError as exc:
            self.statusBar().showMessage(str(exc), 5000)
            return
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        image = QImage(
            pix.samples,
            pix.width,
            pix.height,
            pix.stride,
            QImage.Format_RGB888,
        )
        image = self._paint_highlights(image, page, self._active_highlight_rects(), zoom)
        if self.selected_rects and not self.search_results:
            image = self._paint_selection(image, page, self.selected_rects, zoom)
        self.page_label.setPixmap(QPixmap.fromImage(image))
        self.page_label.resize(image.width(), image.height())
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(self.current_page + 1)
        self.page_spin.blockSignals(False)
        self.setWindowTitle(
            f"{Path(self.current_path).name if self.current_path else 'PDFReader'} - "
            f"Page {self.current_page + 1}/{self.document.page_count} - {self.APP_NAME}"
        )

    def _effective_zoom(self, page):
        if not self.fit_to_window:
            return self.zoom
        available = self.scroll_area.viewport().size()
        margin = 20
        fit_w = (available.width() - margin) / page.rect.width
        fit_h = (available.height() - margin) / page.rect.height
        return min(fit_w, fit_h, 2.0)

    def _validate_render_size(self, page, zoom):
        width = int(page.rect.width * zoom)
        height = int(page.rect.height * zoom)
        total_pixels = width * height
        if total_pixels > self.MAX_RENDER_PIXELS:
            raise PdfSafetyError(
                f"Cannot render at this zoom level — the image would be "
                f"{width}×{height} pixels ({total_pixels / 1_000_000:.0f} MP), "
                f"which exceeds the {self.MAX_RENDER_PIXELS / 1_000_000:.0f} MP limit."
            )

    def _active_highlight_rects(self):
        if self.search_results:
            result = self.search_results[self.current_result_index]
            if result["page"] == self.current_page:
                return result["rects"]
            return []
        return []

    def _paint_highlights(self, image, page, rects, zoom):
        if not rects:
            return image
        highlight = QColor(255, 230, 0, 80)
        painter = QPainter(image)
        painter.setPen(Qt.NoPen)
        painter.setBrush(highlight)
        for rect in rects:
            r = rect * zoom
            painter.drawRect(int(r.x0), int(r.y0), int(r.width), int(r.height))
        painter.end()
        return image

    def _paint_selection(self, image, page, rects, zoom):
        painter = QPainter(image)
        painter.setPen(QColor(37, 99, 235))
        painter.setBrush(QColor(37, 99, 235, 60))
        for rect in rects:
            r = rect * zoom
            painter.drawRect(int(r.x0), int(r.y0), int(r.width), int(r.height))
        painter.end()
        return image

    def select_text_in_rect(self, widget_rect):
        if self.document is None:
            return
        page = self.document.load_page(self.current_page)
        page_rect = self._widget_rect_to_page_rect(widget_rect, page)
        words = self._words_in_rect(page, page_rect)
        if words:
            self.selected_text = self._text_from_words(words)
            self.selected_rects = [w[:4] for w in words]
        else:
            self.selected_text = ""
            self.selected_rects = [fitz.Rect(*page_rect)]
        self._update_controls()
        self.render_page()

    def _widget_rect_to_page_rect(self, widget_rect, page):
        zoom = self.current_render_zoom
        if zoom <= 0:
            zoom = 1.0
        x0 = widget_rect.x() / zoom
        y0 = widget_rect.y() / zoom
        x1 = (widget_rect.x() + widget_rect.width()) / zoom
        y1 = (widget_rect.y() + widget_rect.height()) / zoom
        return fitz.Rect(x0, y0, x1, y1)

    def _words_in_rect(self, page, selection):
        words = page.get_text("words")
        return [w for w in words if fitz.Rect(w[:4]).intersects(selection)]

    def _ocr_words_in_rect(self, page, selection):
        tp = self._get_ocr_textpage(page)
        if tp is None:
            return []
        words = tp.extractWORDS()
        return [w for w in words if fitz.Rect(w[:4]).intersects(selection)]

    def _get_ocr_textpage(self, page):
        page_index = page.number
        if page_index in self.ocr_text_pages:
            return self.ocr_text_pages[page_index]
        if len(self.ocr_text_pages) >= self.MAX_OCR_CACHE_PAGES:
            self.ocr_text_pages.popitem(last=False)
        try:
            tp = page.get_textpage_ocr(flags=3, language="eng")
            self.ocr_text_pages[page_index] = tp
            return tp
        except Exception:
            if not self.ocr_warning_shown:
                QMessageBox.information(
                    self, "OCR Unavailable",
                    "OCR text extraction is not available or failed. "
                    "Operations will use regular text extraction instead."
                )
                self.ocr_warning_shown = True
            return None

    def _text_from_words(self, words):
        if not words:
            return ""
        blocks = []
        current_line = words[0][3]
        line_words = [words[0][4]]
        for w in words[1:]:
            if abs(w[3] - current_line) > 3:
                blocks.append(" ".join(line_words))
                line_words = [w[4]]
                current_line = w[3]
            else:
                line_words.append(w[4])
        blocks.append(" ".join(line_words))
        return "\n".join(blocks)

    # ------------------------------------------------------------------
    # Copy / Selection
    # ------------------------------------------------------------------

    def copy_selected_text(self):
        if self.selected_text:
            clip = QApplication.clipboard()
            clip.setText(self.selected_text)
            self.statusBar().showMessage("Copied to clipboard", 3000)

    def clear_text_selection(self, render=True):
        self.selected_text = ""
        self.selected_rects = []
        if render:
            self.render_page()

    # ------------------------------------------------------------------
    # Annotations
    # ------------------------------------------------------------------

    def _selected_quads(self):
        page = self.document.load_page(self.current_page)
        quad_list = []
        for a_rect in self.selected_rects:
            quad = fitz.Quad(a_rect)
            quad_list.append(quad)
        return quad_list

    def _apply_text_annotation(self, annot_method, color, name):
        if not self.selected_text or self.document is None:
            return
        page = self.document.load_page(self.current_page)
        quads = self._selected_quads()
        annot = annot_method(quads)
        if annot:
            annot.set_colors({"stroke": color})
            annot.set_opacity(0.6)
            annot.update()
            self.clear_text_selection(render=False)
            self.render_page()
            self.statusBar().showMessage(f"{name} added", 3000)

    def highlight_selection(self):
        self._apply_text_annotation(
            lambda q: self.document[self.current_page].add_highlight_annot(q),
            self.ANNOT_HIGHLIGHT, "Highlight"
        )

    def underline_selection(self):
        self._apply_text_annotation(
            lambda q: self.document[self.current_page].add_underline_annot(q),
            self.ANNOT_UNDERLINE, "Underline"
        )

    def strikeout_selection(self):
        self._apply_text_annotation(
            lambda q: self.document[self.current_page].add_strikeout_annot(q),
            self.ANNOT_STRIKEOUT, "Strikethrough"
        )

    def _toggle_sticky_note_mode(self, checked):
        if checked:
            self.page_label.set_annotation_mode("sticky_note")
        else:
            self.page_label.clear_annotation_mode()

    def _place_sticky_note(self, widget_pos: QPoint):
        if self.document is None:
            return
        page = self.document.load_page(self.current_page)
        zoom = self.current_render_zoom
        page_x = widget_pos.x() / zoom
        page_y = widget_pos.y() / zoom

        text, ok = QInputDialog.getMultiLineText(
            self, "Sticky Note", "Enter note text:"
        )
        if not ok or not text.strip():
            return

        annot = page.add_text_annot((page_x, page_y), text.strip(), icon="Note")
        if annot:
            annot.update()
            self.statusBar().showMessage("Sticky note placed", 3000)
        self.render_page()
        self.sticky_button.setChecked(False)
        self.page_label.clear_annotation_mode()

    def _delete_page_annotations(self):
        if self.document is None:
            return
        page = self.document.load_page(self.current_page)
        annots = list(page.annots())
        if not annots:
            QMessageBox.information(self, "No Annotations",
                                    "There are no annotations on this page.")
            return
        reply = QMessageBox.question(
            self, "Delete Annotations",
            f"Delete all {len(annots)} annotations on this page?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        for annot in annots:
            page.delete_annot(annot)
        self.render_page()
        self.statusBar().showMessage("Page annotations deleted", 3000)

    def _delete_all_annotations(self):
        if self.document is None:
            return
        total = 0
        for page_index in range(self.document.page_count):
            page = self.document.load_page(page_index)
            annots = list(page.annots())
            for annot in annots:
                page.delete_annot(annot)
            total += len(annots)
        if total == 0:
            QMessageBox.information(self, "No Annotations",
                                    "There are no annotations in this document.")
            return
        self.render_page()
        self.statusBar().showMessage(f"Deleted {total} annotations across all pages", 5000)

    def _toggle_annotations_visible(self, visible):
        if self.document is None:
            return
        for page_index in range(self.document.page_count):
            page = self.document.load_page(page_index)
            annots = list(page.annots())
            for annot in annots:
                annot.set_flags(annot.flags & ~fitz.PDF_ANNOT_IS_HIDDEN if visible
                                else annot.flags | fitz.PDF_ANNOT_IS_HIDDEN)
                annot.update()
        self.render_page()

    def _save_document_annotations(self):
        if self.document is None:
            return
        try:
            self.document.save(
                self.document.name,
                incremental=True,
                encryption=fitz.PDF_ENCRYPT_KEEP,
            )
            self.statusBar().showMessage("Annotations saved", 3000)
        except Exception as exc:
            QMessageBox.critical(
                self, "Save Error",
                f"Could not save annotations incrementally.\n\n{exc}"
            )

    def _save_document(self):
        if self.document is None:
            return
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Document Copy",
            str(Path(self.current_path).with_name(f"{Path(self.current_path).stem}_copy.pdf")),
            "PDF Files (*.pdf)",
        )
        if not output_path:
            return
        if not output_path.lower().endswith(".pdf"):
            output_path += ".pdf"
        try:
            self.document.save(
                output_path,
                garbage=4,
                deflate=True,
                use_objstms=1,
            )
            self.statusBar().showMessage(f"Saved: {output_path}", 5000)
        except Exception as exc:
            QMessageBox.critical(
                self, "Save Error",
                f"Could not save the document.\n\n{exc}"
            )

    # ------------------------------------------------------------------
    # Page Navigation
    # ------------------------------------------------------------------

    def previous_page(self):
        if self.document is not None and self.current_page > 0:
            self.current_page -= 1
            self.clear_text_selection(render=False)
            self.render_page()
            self._update_controls()

    def next_page(self):
        if self.document is not None and self.current_page < self.document.page_count - 1:
            self.current_page += 1
            self.clear_text_selection(render=False)
            self.render_page()
            self._update_controls()

    def jump_to_page(self, page_number):
        if self.document is not None:
            self.current_page = max(0, min(page_number - 1, self.document.page_count - 1))
            self.clear_text_selection(render=False)
            self.render_page()

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------

    def zoom_in(self):
        if self.fit_to_window:
            self.fit_to_window = False
            self.fit_button.setChecked(False)
        self.zoom = min(self.zoom + self.ZOOM_STEP, self.MAX_ZOOM)
        self.render_page()

    def zoom_out(self):
        if self.fit_to_window:
            self.fit_to_window = False
            self.fit_button.setChecked(False)
        self.zoom = max(self.zoom - self.ZOOM_STEP, self.MIN_ZOOM)
        self.render_page()

    def _on_fit_toggled(self, checked):
        self.set_fit_to_window(checked)

    def set_fit_to_window(self, checked):
        self.fit_to_window = checked
        if self.fit_button.isChecked() != checked:
            self.fit_button.blockSignals(True)
            self.fit_button.setChecked(checked)
            self.fit_button.blockSignals(False)
        if hasattr(self, "_fit_menu_action"):
            self._fit_menu_action.setChecked(checked)
        if self.document is not None:
            self.render_page()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def focus_search(self):
        self.search_input.setFocus()
        self.search_input.selectAll()

    def _search_text_changed(self):
        if not self.search_input.text().strip():
            self.clear_text_selection(render=False)
        self.search_results = []
        self.current_result_index = -1
        self.search_count_label.setText("0")
        if self.document is not None:
            self.render_page()

    def next_search_result(self):
        if not self.search_results:
            return
        self.current_result_index = (self.current_result_index + 1) % len(self.search_results)
        self._sync_search_result_to_page()

    def previous_search_result(self):
        if not self.search_results:
            return
        self.current_result_index = (self.current_result_index - 1) % len(self.search_results)
        self._sync_search_result_to_page()

    def _sync_search_result_to_page(self):
        result = self.search_results[self.current_result_index]
        self.current_page = result["page"]
        self.clear_text_selection(render=False)
        self.search_count_label.setText(self._search_count_text())
        self.render_page()

    def _search_count_text(self):
        return f"{self.current_result_index + 1}/{len(self.search_results)}"

    # ------------------------------------------------------------------
    # PDF Tools (Merge / Split / Compress)
    # ------------------------------------------------------------------

    def merge_pdfs(self):
        start_dir = self.settings.value("lastFolder", str(Path.home()))
        file_names, _ = QFileDialog.getOpenFileNames(
            self, "Select PDFs to Merge", start_dir, "PDF Files (*.pdf)",
        )
        if not file_names:
            return
        if len(file_names) < 2:
            QMessageBox.information(self, "Merge PDFs", "Select at least two PDFs to merge.")
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self, "Save Merged PDF",
            str(Path(file_names[0]).with_name("merged.pdf")),
            "PDF Files (*.pdf)",
        )
        if not output_path:
            return
        if not output_path.lower().endswith(".pdf"):
            output_path += ".pdf"

        try:
            pdf_merge(file_names, output_path)
        except Exception as exc:
            self._show_error("Merge Failed", "Could not merge the selected PDFs.", exc)
            return

        QMessageBox.information(self, "Merge Complete", f"Saved merged PDF:\n\n{output_path}")
        self.statusBar().showMessage("Merged PDFs successfully", 5000)

    def split_pdf(self):
        if self.document is None or self.current_path is None:
            QMessageBox.information(self, "Split PDF", "Open a PDF before using Split.")
            return

        mode, ok = QInputDialog.getItem(
            self, "Split PDF",
            "Choose how to split this PDF:",
            ["Every page into separate PDFs", "Extract page range to one PDF"],
            0, False,
        )
        if not ok:
            return

        output_dir = QFileDialog.getExistingDirectory(
            self, "Choose Output Folder",
            str(Path(self.current_path).parent),
        )
        if not output_dir:
            return

        try:
            if mode == "Every page into separate PDFs":
                saved_paths = split_every_page(
                    self.document, self.current_path,
                    Path(output_dir), self.MAX_SPLIT_PAGES,
                )
                message = f"Saved {len(saved_paths)} PDFs to:\n\n{output_dir}"
            else:
                pages_text, ok = QInputDialog.getText(
                    self, "Extract Pages",
                    "Pages to extract, for example 1-3,5:",
                )
                if not ok or not pages_text.strip():
                    return
                pages = parse_page_ranges(pages_text, self.document.page_count)
                saved_path = extract_pages(
                    self.document, self.current_path, Path(output_dir), pages,
                )
                message = f"Saved extracted pages:\n\n{saved_path}"
        except Exception as exc:
            self._show_error("Split Failed", "Could not split this PDF.", exc)
            return

        QMessageBox.information(self, "Split Complete", message)
        self.statusBar().showMessage("Split PDF successfully", 5000)

    def compress_pdf(self):
        if self.current_path is None:
            QMessageBox.information(self, "Compress PDF", "Open a PDF before using Compress.")
            return

        input_path = Path(self.current_path)
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Save Compressed PDF",
            str(input_path.with_name(f"{input_path.stem}_compressed.pdf")),
            "PDF Files (*.pdf)",
        )
        if not output_path:
            return
        if not output_path.lower().endswith(".pdf"):
            output_path += ".pdf"

        try:
            original_size, output_size = pdf_compress(self.current_path, output_path)
        except Exception as exc:
            self._show_error("Compression Failed", "Could not compress this PDF.", exc)
            return

        saved = original_size - output_size
        if original_size > 0:
            percent = saved / original_size * 100
            detail = (f"Original: {original_size:,} bytes\n"
                      f"Compressed: {output_size:,} bytes\n"
                      f"Saved: {saved:,} bytes ({percent:.1f}%)")
        else:
            detail = f"Compressed: {output_size:,} bytes"
        QMessageBox.information(self, "Compression Complete",
                                f"Saved compressed PDF:\n\n{output_path}\n\n{detail}")
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
        self.split_button.setEnabled(has_document)
        self.compress_button.setEnabled(has_document)
        self.compare_button.setEnabled(HAS_LIB_MODULES)
        self.library_button.setEnabled(HAS_LIB_MODULES)
        self.merge_button.setEnabled(True)
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
        self._save_current_state()
        # Save workspace session
        session = []
        for tab_id, tab in self.tabs.items():
            if tab.path and Path(tab.path).exists():
                session.append({"path": tab.path, "page": tab.current_page})
        self.settings.setValue("session", session)
        # Close docs
        for tab_id, tab in self.tabs.items():
            if tab.document is not None:
                tab.document.close()
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
        dlg.exec()


# ---------------------------------------------------------------------------
# Library Dialog
# ---------------------------------------------------------------------------


class _LibraryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDF Library")
        self.resize(600, 500)
        self._parent = parent

        layout = QVBoxLayout(self)

        # Folder management
        folder_group = QGroupBox("Folders")
        folder_layout = QVBoxLayout(folder_group)
        self.folder_list = QListWidget()
        self.add_folder_btn = QPushButton("Add Folder\u2026")
        self.remove_folder_btn = QPushButton("Remove Folder")
        self.reindex_btn = QPushButton("Re-index All")
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.add_folder_btn)
        btn_row.addWidget(self.remove_folder_btn)
        btn_row.addWidget(self.reindex_btn)
        btn_row.addStretch()
        folder_layout.addWidget(self.folder_list)
        folder_layout.addLayout(btn_row)
        layout.addWidget(folder_group)

        # Search
        search_group = QGroupBox("Search")
        search_layout = QVBoxLayout(search_group)
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search across all indexed PDFs\u2026")
        self.search_btn = QPushButton("Search")
        search_row.addWidget(self.search_input)
        search_row.addWidget(self.search_btn)
        search_layout.addLayout(search_row)
        layout.addWidget(search_group)

        self.add_folder_btn.clicked.connect(self._add_folder)
        self.remove_folder_btn.clicked.connect(self._remove_folder)
        self.reindex_btn.clicked.connect(self._reindex)
        self.search_btn.clicked.connect(self._do_search)
        self.search_input.returnPressed.connect(self._do_search)

        self._refresh_folder_list()

    def _refresh_folder_list(self):
        self.folder_list.clear()
        try:
            folders = lib_idx.get_watched_folders()
            for folder in folders:
                self.folder_list.addItem(str(folder))
        except Exception:
            pass

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select PDF Folder")
        if folder:
            try:
                lib_idx.add_watched_folder(folder)
                self._refresh_folder_list()
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Could not add folder:\n{exc}")

    def _remove_folder(self):
        item = self.folder_list.currentItem()
        if item:
            try:
                lib_idx.remove_watched_folder(item.text())
                self._refresh_folder_list()
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Could not remove folder:\n{exc}")

    def _reindex(self):
        try:
            self.reindex_btn.setEnabled(False)
            self.reindex_btn.setText("Indexing\u2026")
            QApplication.processEvents()
            lib_idx.reindex_all()
            QMessageBox.information(self, "Re-index", "Library re-indexed successfully.")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Re-index failed:\n{exc}")
        finally:
            self.reindex_btn.setText("Re-index All")
            self.reindex_btn.setEnabled(True)

    def _reindex_folder(self, folder):
        try:
            lib_idx.reindex_folder(folder)
        except Exception:
            pass

    def _do_search(self):
        query = self.search_input.text().strip()
        if not query:
            return
        try:
            idx = lib_idx.get_tfidf()
            results = idx.search(query, max_results=50)
            if results:
                dlg = _LibrarySearchResultsDialog(results, self._parent or self)
                dlg.exec()
            else:
                QMessageBox.information(self, "No Results", "No matching documents found.")
        except Exception as exc:
            QMessageBox.critical(self, "Search Error", f"Search failed:\n{exc}")

    def _open_result(self, item):
        data = item.data(Qt.UserRole)
        if data:
            # Open the PDF if possible
            pdf_path = data.get("path", "")
            if pdf_path:
                try:
                    parent = self._parent or self.parent()
                    if hasattr(parent, "open_pdf"):
                        parent.open_pdf(pdf_path)
                        self.accept()
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# Library Search Results Dialog
# ---------------------------------------------------------------------------


class _LibrarySearchResultsDialog(QDialog):
    def __init__(self, results: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search Results")
        self.resize(600, 400)

        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        for r in results:
            text = f"{r.get('title', 'Untitled')} — page {r.get('page', 0) + 1}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, r)
            self.list_widget.addItem(item)
        self.list_widget.itemDoubleClicked.connect(self._select)
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        open_btn = QPushButton("Open")
        close_btn = QPushButton("Close")
        btn_layout.addWidget(open_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        open_btn.clicked.connect(self._select)
        close_btn.clicked.connect(self.reject)

    def _select(self):
        item = self.list_widget.currentItem()
        if item:
            data = item.data(Qt.UserRole)
            if data:
                pdf_path = data.get("path", "")
                if pdf_path:
                    parent = self.parent()
                    if hasattr(parent, "open_pdf"):
                        parent.open_pdf(pdf_path)
                        self.accept()


# ---------------------------------------------------------------------------
# Compare Dialog
# ---------------------------------------------------------------------------


class _CompareDialog(QDialog):
    def __init__(self, path_a, path_b, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDF Comparison")
        self.resize(900, 600)
        self._current_diff_page = 0
        self._diff_result = None

        layout = QVBoxLayout(self)

        # Summary label
        self.summary_label = QLabel("Comparing\u2026")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        # Diff panels
        splitter = QSplitter(Qt.Horizontal)
        self.panel_a = QTextEdit()
        self.panel_b = QTextEdit()
        self.panel_a.setReadOnly(True)
        self.panel_b.setReadOnly(True)
        splitter.addWidget(self.panel_a)
        splitter.addWidget(self.panel_b)
        layout.addWidget(splitter, 1)

        self._run(path_a, path_b)

    def _run(self, path_a, path_b):
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
        prev_btn = QPushButton("\u2190 Prev")
        next_btn = QPushButton("Next \u2192")
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
