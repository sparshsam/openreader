# PDFReader by Sparsh — library modules
"""Library modules for PDFReader by Sparsh."""

from pdfreader_lib.pdf_validator import PdfSafetyError, validate_pdf_path, validate_document_pages, safe_open_pdf
from pdfreader_lib.tab_state import TabData
from pdfreader_lib.theme_manager import DARK_STYLESHEET, ThemeManager, THEME_AUTO, THEME_LIGHT, THEME_DARK
from pdfreader_lib.pdf_tools import merge_pdfs, split_every_page, extract_pages, parse_page_ranges, compress_pdf
from pdfreader_lib.updater import PdfUpdater, GITHUB_REPO, WINDOWS_UPDATE_ASSET, MACOS_APPLE_SILICON_UPDATE_ASSET, MACOS_INTEL_UPDATE_ASSET, parse_version

__all__ = [
    "PdfSafetyError",
    "validate_pdf_path",
    "validate_document_pages",
    "safe_open_pdf",
    "TabData",
    "DARK_STYLESHEET",
    "ThemeManager",
    "THEME_AUTO",
    "THEME_LIGHT",
    "THEME_DARK",
    "merge_pdfs",
    "split_every_page",
    "extract_pages",
    "parse_page_ranges",
    "compress_pdf",
    "PdfUpdater",
    "GITHUB_REPO",
    "WINDOWS_UPDATE_ASSET",
    "MACOS_APPLE_SILICON_UPDATE_ASSET",
    "MACOS_INTEL_UPDATE_ASSET",
    "parse_version",
]
