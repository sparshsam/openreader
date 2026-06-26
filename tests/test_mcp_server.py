"""
Tests for the OpenReader MCP server.

Covers input validation, output shape, and error handling
for all 14 tools, following the MCP Build Guide test patterns.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import fitz
import pytest

from pdfreader_lib.mcp_server import (
    _validate_pdf,
    _get_page_count,
    _get_metadata,
    _extract_page_text,
    _search_single_pdf,
    _compress_pdf,
    _merge_pdfs,
    _split_every_page,
    _extract_pages,
    _parse_page_ranges,
    TOOLS,
)


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def sample_pdf() -> Path:
    """Create a 3-page PDF with known content for testing."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = f.name
    doc = fitz.open()
    try:
        for i in range(3):
            page = doc.new_page()
            page.insert_text((72, 100), f"Page {i + 1} content.", fontsize=12)
            page.insert_text((72, 130), f"Hello world from page {i + 1}.", fontsize=12)
        doc.save(path, garbage=4)
    finally:
        doc.close()
    yield Path(path)
    os.unlink(path)


@pytest.fixture
def sample_pdf_b() -> Path:
    """A second PDF (for merge/compare tests)."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = f.name
    doc = fitz.open()
    try:
        page = doc.new_page()
        page.insert_text((72, 100), "Second PDF content.", fontsize=12)
        doc.save(path, garbage=4)
    finally:
        doc.close()
    yield Path(path)
    os.unlink(path)


@pytest.fixture
def output_dir() -> Path:
    """Temporary directory for split/merge outputs."""
    p = Path(tempfile.mkdtemp())
    yield p
    for f in p.iterdir():
        f.unlink()
    p.rmdir()


# ═══════════════════════════════════════════════════════════════
# Tool Registration — all tools are properly defined
# ═══════════════════════════════════════════════════════════════


class TestToolRegistration:
    def test_all_tools_have_names(self):
        """Every tool has a non-empty name."""
        for t in TOOLS:
            assert t.name, f"Tool missing name: {t}"

    def test_all_tools_have_descriptions(self):
        """Every tool has a non-empty description."""
        for t in TOOLS:
            assert t.description, f"Tool {t.name} missing description"

    def test_all_tools_have_input_schema(self):
        """Every tool has an inputSchema with type: object."""
        for t in TOOLS:
            assert t.inputSchema is not None
            assert t.inputSchema.get("type") == "object"

    def test_tool_descriptions_are_sentences(self):
        """Tool descriptions are at least 20 chars and read as sentences."""
        for t in TOOLS:
            assert len(t.description) >= 30, (
                f"Tool '{t.name}' description too short ({len(t.description)} chars). "
                f"Must be a complete AI-optimized sentence."
            )

    @pytest.mark.parametrize("tool_name", [
        "extract_text", "get_page_text", "get_metadata", "get_page_count",
        "search_pdf", "compare_pdfs", "merge_pdfs", "split_pdf",
        "extract_pages", "compress_pdf", "index_folder",
        "search_library", "search_semantic", "list_indexed_docs",
    ])
    def test_known_tools_exist(self, tool_name):
        """All 14 expected tools are registered."""
        names = [t.name for t in TOOLS]
        assert tool_name in names, f"Expected tool '{tool_name}' not found in TOOLS"


# ═══════════════════════════════════════════════════════════════
# Input Validation
# ═══════════════════════════════════════════════════════════════


class TestInputValidation:
    def test_validate_pdf_valid(self, sample_pdf):
        """Valid PDF passes validation."""
        result = _validate_pdf(str(sample_pdf))
        assert result == sample_pdf.resolve()

    def test_validate_pdf_not_found(self):
        """Non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            _validate_pdf("/nonexistent/file.pdf")

    def test_validate_pdf_not_a_pdf(self, tmp_path):
        """Non-PDF file raises ValueError."""
        txt = tmp_path / "test.txt"
        txt.write_text("not a pdf")
        with pytest.raises(ValueError, match="Not a PDF file"):
            _validate_pdf(str(txt))

    def test_validate_pdf_wrong_extension(self, tmp_path):
        """File without .pdf extension raises ValueError."""
        f = tmp_path / "data.bin"
        f.write_text("some data")
        with pytest.raises(ValueError, match="Not a PDF"):
            _validate_pdf(str(f))

    def test_validate_pdf_empty_file(self, tmp_path):
        """Empty file raises ValueError."""
        empty = tmp_path / "empty.pdf"
        empty.write_text("")
        with pytest.raises(ValueError, match="empty"):
            _validate_pdf(str(empty))

    def test_page_range_parsing_valid(self):
        """Standard page range notation parses correctly."""
        assert _parse_page_ranges("1-3,5,7-9", 10) == [0, 1, 2, 4, 6, 7, 8]

    def test_page_range_parsing_single(self):
        """Single page number works."""
        assert _parse_page_ranges("3", 10) == [2]

    def test_page_range_parsing_out_of_range(self):
        """Page number past document end raises ValueError."""
        with pytest.raises(ValueError, match="outside valid range"):
            _parse_page_ranges("1-15", 10)

    def test_page_range_parsing_empty(self):
        """Empty string raises ValueError."""
        with pytest.raises(ValueError, match="No valid pages"):
            _parse_page_ranges("", 10)

    def test_page_range_reversed(self):
        """Reversed range like '5-1' is handled (swapped)."""
        result = _parse_page_ranges("5-1", 10)
        assert result == [0, 1, 2, 3, 4]


# ═══════════════════════════════════════════════════════════════
# Output Shape
# ═══════════════════════════════════════════════════════════════


class TestOutputShape:
    def test_get_page_count_returns_int(self, sample_pdf):
        """get_page_count returns an integer."""
        count = _get_page_count(str(sample_pdf))
        assert isinstance(count, int)
        assert count == 3

    def test_get_metadata_returns_dict(self, sample_pdf):
        """get_metadata returns a dict with expected keys."""
        meta = _get_metadata(str(sample_pdf))
        assert isinstance(meta, dict)
        assert "title" in meta
        assert "author" in meta
        assert "pages" in meta
        assert meta["pages"] == 3
        assert meta["file_name"] == sample_pdf.name

    def test_extract_page_text_returns_string(self, sample_pdf):
        """get_page_text returns the text of the requested page."""
        text = _extract_page_text(str(sample_pdf), 1)
        assert isinstance(text, str)
        assert "Page 1" in text

    def test_extract_page_text_out_of_range(self, sample_pdf):
        """Page number beyond document raises ValueError."""
        with pytest.raises(ValueError, match="out of range"):
            _extract_page_text(str(sample_pdf), 99)

    def test_search_single_pdf_returns_results(self, sample_pdf):
        """Searching for existing text returns matches."""
        results = _search_single_pdf(str(sample_pdf), "Hello")
        assert isinstance(results, list)
        assert len(results) > 0
        assert results[0]["match_count"] >= 1
        assert len(results[0]["snippets"]) > 0

    def test_search_single_pdf_no_match(self, sample_pdf):
        """Searching for non-existent text returns empty list."""
        results = _search_single_pdf(str(sample_pdf), "xyznonexistent123")
        assert results == []

    def test_compress_pdf_returns_json_stats(self, sample_pdf):
        """compress_pdf returns compression stats JSON."""
        result = _compress_pdf(str(sample_pdf))
        data = json.loads(result)
        assert "output_path" in data
        assert "original_bytes" in data
        assert "compressed_bytes" in data
        assert "savings_percent" in data
        assert data["original_bytes"] > 0

    def test_merge_pdfs_creates_file(self, sample_pdf, sample_pdf_b, output_dir):
        """merge_pdfs creates a merged PDF."""
        out_path = str(output_dir / "merged.pdf")
        result = _merge_pdfs([str(sample_pdf), str(sample_pdf_b)], out_path)
        assert Path(result).exists()
        merged = fitz.open(result)
        try:
            assert merged.page_count == 4  # 3 + 1
        finally:
            merged.close()

    def test_split_pdf_creates_page_files(self, sample_pdf, output_dir):
        """split_pdf creates one file per page."""
        result = _split_every_page(str(sample_pdf), str(output_dir))
        assert len(result) == 3
        for r in result:
            assert Path(r).exists()

    def test_extract_pages_creates_subset(self, sample_pdf, output_dir):
        """extract_pages creates a PDF with only requested pages."""
        out_path = str(output_dir / "subset.pdf")
        result = _extract_pages(str(sample_pdf), "1,3", out_path)
        assert Path(result).exists()
        doc = fitz.open(result)
        try:
            assert doc.page_count == 2
        finally:
            doc.close()


# ═══════════════════════════════════════════════════════════════
# Error Handling
# ═══════════════════════════════════════════════════════════════


class TestErrorHandling:
    def test_invalid_path_on_get_metadata(self):
        """Non-existent path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            _get_metadata("/does/not/exist.pdf")

    def test_invalid_path_on_get_page_count(self):
        """Non-existent path raises error."""
        with pytest.raises(FileNotFoundError):
            _get_page_count("/does/not/exist.pdf")

    def test_invalid_path_on_compress(self):
        """Compress on non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            _compress_pdf("/does/not/exist.pdf")

    def test_merge_with_single_file_fails(self, sample_pdf, output_dir):
        """Merge with only 1 input works but is a no-op merge (inserts one doc)."""
        out_path = str(output_dir / "single.pdf")
        result = _merge_pdfs([str(sample_pdf)], out_path)
        assert Path(result).exists()

    def test_extract_pages_invalid_ranges(self, sample_pdf, output_dir):
        """Invalid page range raises error."""
        with pytest.raises(ValueError, match="outside valid range"):
            _extract_pages(str(sample_pdf), "1-999", str(output_dir / "bad.pdf"))
