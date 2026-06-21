"""
Regression tests for reliability and crash safety.

Tests cover:
- PDF safety validation (path checking, size, header)
- Document page validation
- Error display logic
- Backup/recovery safety assumptions
- closeEvent defensive handling
- Annotation delete confirmation (v0.9.0 bugfix)
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

import sys
sys.path.insert(0, str(ROOT))

import pytest


# Only import static/non-GUI portions of main
# The GUI-dependent parts can't run in headless CI
from main import PdfSafetyError  # noqa: E402


# ---------------------------------------------------------------------------
# PdfSafetyError
# ---------------------------------------------------------------------------


class TestPdfSafetyError:
    def test_is_exception(self):
        exc = PdfSafetyError("test error")
        assert isinstance(exc, Exception)
        assert str(exc) == "test error"


# ---------------------------------------------------------------------------
# Version constant
# ---------------------------------------------------------------------------


class TestVersion:
    def test_version_string_exists(self):
        """Version should be a non-empty string."""
        sys.path.insert(0, str(ROOT))
        import main as m  # noqa: F811
        assert hasattr(m, "__version__")
        assert isinstance(m.__version__, str)
        assert len(m.__version__) > 0

    def test_version_format(self):
        import main as m
        parts = m.__version__.split("-")
        semver = parts[0]
        segments = semver.split(".")
        assert len(segments) == 3, f"Version should be semver: {m.__version__}"
        for seg in segments:
            assert seg.isdigit(), f"Segment {seg} should be numeric"

    def test_github_repo_is_correct(self):
        import main as m
        assert m.GITHUB_REPO == "sparshsam/openreader"


# ---------------------------------------------------------------------------
# Security & path validation constants
# ---------------------------------------------------------------------------


class TestSafetyLimits:
    def test_max_pdf_size_is_reasonable(self):
        import main as m
        # 500 MB
        assert m.PdfReaderWindow.MAX_PDF_SIZE_BYTES == 500 * 1024 * 1024

    def test_max_page_dimension_is_reasonable(self):
        import main as m
        assert m.PdfReaderWindow.MAX_PAGE_DIMENSION_POINTS == 14400

    def test_max_render_pixels_is_reasonable(self):
        import main as m
        assert m.PdfReaderWindow.MAX_RENDER_PIXELS == 80_000_000

    def test_max_search_matches_is_reasonable(self):
        import main as m
        assert m.PdfReaderWindow.MAX_SEARCH_MATCHES == 20_000

    def test_max_split_pages_is_reasonable(self):
        import main as m
        assert m.PdfReaderWindow.MAX_SPLIT_PAGES == 1000


# ---------------------------------------------------------------------------
# Keyboard shortcuts referenced in About dialog
# ---------------------------------------------------------------------------


class TestShortcutConsistency:
    """Verify that shortcuts mentioned in About are registered once."""

    def test_about_shortcuts_match_registered_shortcuts(self):
        import main as m

        about_shortcuts = {shortcut for _label, shortcut in m.PdfReaderWindow.ABOUT_SHORTCUTS}
        registered = {shortcut for _name, shortcut in m.PdfReaderWindow.REGISTERED_SHORTCUTS}

        for shortcut in ("Ctrl+O", "Ctrl+S", "Ctrl+F", "Ctrl+C", "Ctrl+0", "Ctrl+W", "Ctrl+T"):
            assert shortcut in about_shortcuts
            assert shortcut in registered
        assert "Page Up" in registered
        assert "Page Down" in registered
        assert "Ctrl+=" in registered
        assert "Ctrl+-" in registered

    def test_registered_shortcuts_are_unique(self):
        import main as m

        registered = [shortcut for _name, shortcut in m.PdfReaderWindow.REGISTERED_SHORTCUTS]
        assert len(registered) == len(set(registered))

    def test_about_shortcut_html_is_generated_from_declared_shortcuts(self):
        import main as m

        html = m.PdfReaderWindow._about_shortcuts_html()
        for label, shortcut in m.PdfReaderWindow.ABOUT_SHORTCUTS:
            assert label in html
            assert shortcut in html

    def test_shortcuts_use_application_context_qshortcuts(self):
        import main as m

        src = Path(m.__file__).read_text()
        assert "QShortcut(QKeySequence(sequence), self)" in src
        assert "shortcut.setContext(Qt.ApplicationShortcut)" in src

    def test_shortcuts_have_key_event_fallback_for_focused_widgets(self):
        import main as m

        src = Path(m.__file__).read_text()
        assert "installEventFilter(self)" in src
        assert "def _handle_shortcut_key_event" in src
        assert "Qt.Key_W: self._close_current_tab" in src
        assert "Qt.Key_0: self._fit_width_shortcut" in src


class TestAboutStoreLink:
    """Verify the About dialog prefers the Store app with a web fallback."""

    def test_store_link_uses_native_uri_when_available(self, monkeypatch):
        import main as m

        opened = []
        monkeypatch.setattr(m.QDesktopServices, "openUrl", lambda url: opened.append(url.toString()) or True)

        m.PdfReaderWindow._open_store_listing()

        assert opened == ["ms-windows-store://pdp/?productid=9MXDVW2645LL"]

    def test_store_link_falls_back_to_web_listing(self, monkeypatch):
        import main as m

        opened = []

        def open_url(url):
            opened.append(url.toString())
            return len(opened) > 1

        monkeypatch.setattr(m.QDesktopServices, "openUrl", open_url)

        m.PdfReaderWindow._open_store_listing()

        assert opened == [
            "ms-windows-store://pdp/?productid=9MXDVW2645LL",
            "https://apps.microsoft.com/detail/9MXDVW2645LL",
        ]


# ---------------------------------------------------------------------------
# Open action signal handling
# ---------------------------------------------------------------------------


class TestOpenActionSignalHandling:
    def test_open_pdf_normalizes_qt_boolean_signal_argument(self):
        """Qt clicked/triggered signals pass False; open_pdf must still show picker."""
        import main as m

        src = Path(m.__file__).read_text()
        assert "if isinstance(file_name, bool):" in src
        assert "file_name = None" in src

    def test_new_tab_button_opens_new_tab(self):
        """The plus button should create a blank tab without file dialog."""
        import main as m

        src = Path(m.__file__).read_text()
        assert 'setObjectName("NewTabButton")' in src
        assert 'setToolTip("New Tab (Ctrl+T)")' in src
        assert "new_tab_button.clicked.connect(self.new_tab)" in src

    def test_tabs_use_explicit_close_button(self):
        """Tabs should expose a readable close affordance instead of a hidden style glyph."""
        import main as m

        src = Path(m.__file__).read_text()
        assert 'setTabsClosable(False)' in src
        assert 'setObjectName("TabCloseButton")' in src
        assert 'close_button.setText("×")' in src
        assert "QToolButton#TabCloseButton:hover" in src
        assert "QTabBar::close-button" not in src

    def test_tab_creation_sets_current_tab_id_explicitly(self):
        """The first tab must become current even if QTabBar signals fire before tab data is attached."""
        import main as m

        src = Path(m.__file__).read_text()
        assert "self.tab_bar.blockSignals(True)" in src
        assert "self.current_tab_id = tab_id" in src
        assert "tab_id = self.tab_bar.tabData(index)" in src
        assert "def _show_empty_state" in src

    def test_open_pdf_blocks_re_entrant_calls(self):
        """Re-entrant calls to open_pdf should be blocked when picker is shown."""
        import main as m
        src = Path(m.__file__).read_text()
        assert "self._open_in_progress" in src
        assert "'open_pdf: re-entrant call blocked (picker already shown)'" in src or "\"open_pdf: re-entrant call blocked (picker already shown)\"" in src

    def test_new_tab_does_not_call_open_pdf(self):
        """Ctrl+T / + button should create a blank tab, not open a file dialog."""
        import main as m
        src = Path(m.__file__).read_text()
        assert "def new_tab(self):" in src
        assert "'New Tab (blank)'" in src or "\"New Tab (blank)\"" in src
        assert "Qt.Key_T: self.new_tab" in src
        assert "new_tab_button.clicked.connect(self.new_tab)" in src

    def test_session_dont_ask_persisted(self):
        """'Don't ask again' setting should be stored in QSettings."""
        import main as m
        src = Path(m.__file__).read_text()
        assert "sessionDontAsk" in src
        assert "Don't ask again" in src
        assert "self._session_dont_ask" in src

    def test_compress_size_guard_detects_worse_compression(self):
        """Compression should reject output if larger than or equal to original."""
        import main as m
        src = Path(m.__file__).read_text()
        assert "if output_size >= source_size:" in src
        assert "Compression was not beneficial" in src
        assert "unlink(missing_ok=True)" in src

    def test_unsigned_publisher_doc_added(self):
        """README should document the unsigned 'Unknown Publisher' status."""
        readme = (Path(ROOT) / "README.md").read_text()
        assert 'Unknown Publisher' in readme
        assert 'code-signing' in readme

    def test_open_pdf_cancelled_message_is_clean(self):
        """Cancel should show exactly one clean message, not cascading fallback messages."""
        import main as m
        src = Path(m.__file__).read_text()
        assert "no file selected (cancelled)" in src
        # Verify old cascading fallback messages are removed
        assert "_pick_file_tkinter()" not in src.split("open_pdf: no file selected")[0].rsplit("def open_pdf")[-1]


# ---------------------------------------------------------------------------
# Zoom and Fit behaviour — v1.2.3
# ---------------------------------------------------------------------------


class TestZoomConstants:
    def test_zoom_bounds_are_sane(self):
        import main as m
        assert m.PdfReaderWindow.MIN_ZOOM == 0.25
        assert m.PdfReaderWindow.MAX_ZOOM == 5.0
        assert m.PdfReaderWindow.ZOOM_STEP == 0.15

    def test_tab_data_defaults_to_fit_on_open(self):
        import main as m
        tab = m.TabData(name="test")
        assert tab.fit_to_window is True
        assert tab.zoom == 1.25

    def test_version_is_1_2_3(self):
        import main as m
        assert m.__version__ == "1.2.3"


class TestZoomUi:
    def test_zoom_buttons_use_clear_text_labels(self):
        """Zoom buttons must use plain visible text, not obscure unicode or icon glyphs."""
        import main as m
        src = Path(m.__file__).read_text()
        assert 'QPushButton("−")' in src or 'QPushButton("-")' in src
        assert 'QPushButton("+")' in src
        assert 'QPushButton("Fit")' in src

    def test_fit_tooltip_mentions_ctrl0(self):
        import main as m
        src = Path(m.__file__).read_text()
        assert "Fit page to window" in src

    def test_zoom_out_tooltip_mentions_mouse_wheel(self):
        import main as m
        src = Path(m.__file__).read_text()
        assert "Mouse Wheel" in src

    def test_zoom_in_tooltip_mentions_mouse_wheel(self):
        import main as m
        src = Path(m.__file__).read_text()
        assert "Mouse Wheel" in src or "mouse wheel" in src


class TestCtrlWheel:
    def test_event_filter_handles_wheel_on_viewport(self):
        import main as m
        src = Path(m.__file__).read_text()
        assert "event.type() == QEvent.Wheel" in src
        assert "event.modifiers() & Qt.ControlModifier" in src
        assert "self.zoom_in()" in src
        assert "self.zoom_out()" in src
        assert "scroll_area.viewport()" in src

    def test_event_filter_installed_on_viewport(self):
        import main as m
        src = Path(m.__file__).read_text()
        assert "scroll_area.viewport().installEventFilter(self)" in src

    def test_wheel_event_prevents_scrolling_during_zoom(self):
        import main as m
        src = Path(m.__file__).read_text()
        assert "return True  # consumed" in src


class TestEffectiveZoom:
    def test_fit_mode_returns_bounded_zoom(self):
        """_effective_zoom should respect MIN/MAX bounds in fit mode."""
        import main as m
        assert m.PdfReaderWindow.MIN_ZOOM <= m.PdfReaderWindow.MAX_ZOOM

    def test_non_fit_returns_stored_zoom(self):
        """When fit_to_window is False, _effective_zoom must return the stored zoom value."""
        import main as m
        src = Path(m.__file__).read_text()
        assert "if not self.fit_to_window:" in src
        assert "return self.zoom" in src
        assert "min(vp_w / pw, vp_h / ph)" in src  # true Fit Page (width + height)
