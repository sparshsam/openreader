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

    def test_update_asset_names_are_canonical(self):
        import main as m
        assert m.WINDOWS_UPDATE_ASSET == "PDFReader-by-Sparsh-Windows.zip"
        assert m.MACOS_APPLE_SILICON_UPDATE_ASSET == "PDFReader-by-Sparsh-macOS-Apple-Silicon.zip"
        assert m.MACOS_INTEL_UPDATE_ASSET == "PDFReader-by-Sparsh-macOS-Intel.zip"

    def test_github_repo_is_correct(self):
        import main as m
        assert m.GITHUB_REPO == "sparshsam/pdfreader-by-sparsh"


# ---------------------------------------------------------------------------
# Release asset name consistency
# ---------------------------------------------------------------------------


class TestReleaseAssetConsistency:
    def test_setup_exe_not_mistaken_for_updater_asset(self):
        """The Setup.exe should not match any canonical update asset name."""
        import main as m
        setup_name = "PDFReader-by-Sparsh-Setup.exe"
        windows_asset = m.WINDOWS_UPDATE_ASSET
        assert setup_name != windows_asset
        # The updater should NOT select Setup.exe
        assert m.WINDOWS_UPDATE_ASSET == "PDFReader-by-Sparsh-Windows.zip"

    def test_asset_names_are_distinct(self):
        import main as m
        names = {m.WINDOWS_UPDATE_ASSET, m.MACOS_APPLE_SILICON_UPDATE_ASSET, m.MACOS_INTEL_UPDATE_ASSET}
        assert len(names) == 3, "Update asset names must be distinct"


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
    """Verify that shortcuts mentioned in the About dialog exist in the code."""

    def test_ctrl_o_exists(self):
        import main as m
        src = Path(m.__file__).read_text()
        assert 'QKeySequence.Open' in src or '"Ctrl+O"' in src

    def test_ctrl_s_exists(self):
        import main as m
        src = Path(m.__file__).read_text()
        assert 'QKeySequence.Save' in src

    def test_ctrl_f_exists(self):
        import main as m
        src = Path(m.__file__).read_text()
        assert 'QKeySequence.Find' in src

    def test_ctrl_c_exists(self):
        import main as m
        src = Path(m.__file__).read_text()
        assert 'QKeySequence.Copy' in src

    def test_page_up_exists(self):
        import main as m
        src = Path(m.__file__).read_text()
        assert 'Key_PageUp' in src

    def test_page_down_exists(self):
        import main as m
        src = Path(m.__file__).read_text()
        assert 'Key_PageDown' in src

    def test_ctrl_w_exists(self):
        import main as m
        src = Path(m.__file__).read_text()
        assert '"Ctrl+W"' in src

    def test_ctrl_t_exists(self):
        import main as m
        src = Path(m.__file__).read_text()
        assert '"Ctrl+T"' in src

    def test_ctrl_0_exists(self):
        import main as m
        src = Path(m.__file__).read_text()
        assert '"Ctrl+0"' in src or 'Ctrl+0' in src


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

    def test_new_tab_button_opens_pdf_flow(self):
        """The plus button should use the same picker flow as other open actions."""
        import main as m

        src = Path(m.__file__).read_text()
        assert 'setObjectName("NewTabButton")' in src
        assert 'setToolTip("Open another PDF")' in src
        assert "new_tab_button.clicked.connect(self.open_pdf)" in src

    def test_tabs_use_explicit_close_button(self):
        """Tabs should expose a readable close affordance instead of a hidden style glyph."""
        import main as m

        src = Path(m.__file__).read_text()
        assert 'setTabsClosable(False)' in src
        assert 'setObjectName("TabCloseButton")' in src
        assert 'close_button.setText("×")' in src
        assert "QToolButton#TabCloseButton:hover" in src
        assert "QTabBar::close-button" not in src
