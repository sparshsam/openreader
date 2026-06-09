"""Service-level tests for pdfreader_lib modules.

Tests the extracted modules in isolation: no Qt dependency, no GUI.
PDF validation tests use real but minimal PDF data.
"""

import os
import tempfile
from pathlib import Path

import pytest

from pdfreader_lib.pdf_validator import (
    PdfSafetyError,
    validate_pdf_path,
    safe_open_pdf,
)
from pdfreader_lib.tab_state import TabData
from pdfreader_lib.theme_manager import (
    ThemeManager,
    DARK_STYLESHEET,
    THEME_AUTO,
    THEME_LIGHT,
    THEME_DARK,
)
from pdfreader_lib.pdf_tools import (
    parse_page_ranges,
    compress_pdf,
)
from pdfreader_lib.updater import (
    parse_version,
    is_packaged,
    select_update_apply_method,
    validate_download_metadata,
    WINDOWS_UPDATE_ASSET,
    MACOS_APPLE_SILICON_UPDATE_ASSET,
    MACOS_INTEL_UPDATE_ASSET,
)


# ===================================================================
# Fixtures
# ===================================================================

@pytest.fixture
def sample_pdf_path():
    """Create a minimal valid PDF for testing."""
    # Minimal PDF that starts with %PDF-
    content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(content)
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def non_pdf_path():
    """Create a non-PDF file with another extension."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"This is not a PDF.")
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def fake_pdf_path():
    """Create a file with .pdf suffix that isn't really a PDF."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"This is not a real PDF.")
        path = f.name
    yield path
    os.unlink(path)


# ===================================================================
# PdfSafetyError
# ===================================================================

class TestPdfSafetyError:
    def test_exception_is_exception(self):
        err = PdfSafetyError("test error")
        assert isinstance(err, Exception)
        assert str(err) == "test error"


# ===================================================================
# validate_pdf_path
# ===================================================================

class TestValidatePdfPath:
    def test_valid_pdf(self, sample_pdf_path):
        result = validate_pdf_path(sample_pdf_path)
        assert isinstance(result, Path)
        assert result.suffix == ".pdf"

    def test_nonexistent_path(self):
        with pytest.raises(PdfSafetyError, match="does not exist"):
            validate_pdf_path("/nonexistent/file.pdf")

    def test_not_a_pdf_extension(self, non_pdf_path):
        with pytest.raises(PdfSafetyError, match="Only .pdf files"):
            validate_pdf_path(non_pdf_path)

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            with pytest.raises(PdfSafetyError, match="empty"):
                validate_pdf_path(path)
        finally:
            os.unlink(path)

    def test_fake_pdf_content(self, fake_pdf_path):
        with pytest.raises(PdfSafetyError, match="does not look like a valid PDF"):
            validate_pdf_path(fake_pdf_path)

    def test_size_limit(self, sample_pdf_path):
        with pytest.raises(PdfSafetyError, match="safety limit"):
            validate_pdf_path(sample_pdf_path, max_size_bytes=1)

    def test_size_accept(self, sample_pdf_path):
        # Should pass with a generous limit
        result = validate_pdf_path(sample_pdf_path, max_size_bytes=10 * 1024 * 1024)
        assert result.exists()


# ===================================================================
# safe_open_pdf
# ===================================================================

class TestSafeOpenPdf:
    def test_opens_valid_pdf(self, sample_pdf_path):
        doc = safe_open_pdf(sample_pdf_path)
        assert doc is not None
        assert doc.page_count == 1
        doc.close()

    def test_rejects_fake_pdf(self, fake_pdf_path):
        with pytest.raises(PdfSafetyError):
            safe_open_pdf(fake_pdf_path)


# ===================================================================
# TabData
# ===================================================================

class TestTabData:
    def test_default_values(self):
        tab = TabData(name="Tab 1")
        assert tab.name == "Tab 1"
        assert tab.path is None
        assert tab.document is None
        assert tab.current_page == 0
        assert tab.zoom == 1.25
        assert tab.fit_to_window is True
        assert tab.search_text == ""
        assert tab.search_results == []
        assert tab.current_result_index == -1

    def test_custom_values(self):
        tab = TabData(name="Test", path="/tmp/test.pdf", current_page=5, zoom=2.0)
        assert tab.name == "Test"
        assert tab.path == "/tmp/test.pdf"
        assert tab.current_page == 5
        assert tab.zoom == 2.0


# ===================================================================
# ThemeManager
# ===================================================================

class TestThemeManager:
    def test_default_theme_is_auto(self):
        mgr = ThemeManager()
        assert mgr.theme == THEME_AUTO

    def test_set_theme(self):
        mgr = ThemeManager(THEME_DARK)
        assert mgr.theme == THEME_DARK
        mgr.theme = THEME_LIGHT
        assert mgr.theme == THEME_LIGHT

    def test_is_dark_explicit_light(self):
        mgr = ThemeManager(THEME_LIGHT)
        assert mgr.is_dark() is False

    def test_is_dark_explicit_dark(self):
        mgr = ThemeManager(THEME_DARK)
        assert mgr.is_dark() is True

    def test_stylesheet_not_empty(self):
        assert len(DARK_STYLESHEET) > 500
        assert "background-color: #1e1e2e" in DARK_STYLESHEET


# ===================================================================
# parse_page_ranges
# ===================================================================

class TestParsePageRanges:
    def test_single_page(self):
        assert parse_page_ranges("3", 10) == [2]

    def test_range(self):
        assert parse_page_ranges("1-3", 10) == [0, 1, 2]

    def test_combined(self):
        assert parse_page_ranges("1,3-5", 10) == [0, 2, 3, 4]

    def test_reversed_range(self):
        assert parse_page_ranges("5-3", 10) == [2, 3, 4]

    def test_out_of_range(self):
        with pytest.raises(ValueError, match="outside the valid range"):
            parse_page_ranges("50", 10)

    def test_no_valid_pages(self):
        with pytest.raises(ValueError, match="No valid pages"):
            parse_page_ranges("", 10)

    def test_deduplicates(self):
        assert parse_page_ranges("1,1,2", 10) == [0, 1]


# ===================================================================
# compress_pdf (integration-light)
# ===================================================================

class TestCompressPdf:
    def test_compress_rejects_bogus(self):
        """Verify compress_pdf raises PdfSafetyError on a non-existent file."""
        with pytest.raises(PdfSafetyError):
            compress_pdf("/nonexistent/file.pdf", "/tmp/out.pdf")


# ===================================================================
# Updater helpers
# ===================================================================

class TestParseVersion:
    def test_semver(self):
        assert parse_version("v1.2.3") == (1, 2, 3)

    def test_no_v_prefix(self):
        assert parse_version("2.0.1") == (2, 0, 1)

    def test_no_match(self):
        assert parse_version("not-a-version") is None

    def test_empty(self):
        assert parse_version("") is None


class TestSelectUpdateMethod:
    def test_windows_zip(self):
        method, diag = select_update_apply_method("Windows", WINDOWS_UPDATE_ASSET, Path("/tmp/x.zip"))
        assert method == "windows_zip"
        assert diag == ""

    def test_macos_zip(self):
        method, diag = select_update_apply_method("Darwin", MACOS_APPLE_SILICON_UPDATE_ASSET, Path("/tmp/x.zip"))
        assert method == "macos_zip"
        assert diag == ""

    def test_macos_intel_zip(self):
        method, diag = select_update_apply_method("Darwin", MACOS_INTEL_UPDATE_ASSET, Path("/tmp/x.zip"))
        assert method == "macos_zip"

    def test_unsupported(self):
        method, diag = select_update_apply_method("Linux", "some-file.tar.gz", Path("/tmp/x.tar.gz"))
        assert method is None
        assert "Unsupported" in diag


class TestValidateDownloadMetadata:
    def test_missing_asset_name(self):
        msg = validate_download_metadata(None, "v1.0.0")
        assert "missing" in msg.lower()

    def test_missing_tag(self):
        msg = validate_download_metadata("asset.zip", None)
        assert "missing" in msg.lower()

    def test_both_present(self):
        msg = validate_download_metadata("asset.zip", "v1.0.0")
        assert msg == ""


class TestIsPackaged:
    def test_runs_unfrozen(self):
        assert is_packaged() is False
