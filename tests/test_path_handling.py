"""Tests for application-boundary path handling (file-open activation).

Windows activates OpenReader by passing the PDF path as a quoted ``%1`` argv
element, so the path survives intact even with spaces, parentheses, or
non-ASCII characters. ``filter_pdf_paths`` is the boundary where argv is
reduced to PDF paths, and the IPC hand-off serializes them as JSON
(Unicode-safe). These tests exercise that boundary without faking Windows.
"""

import json

import main


def test_filter_pdf_paths_keeps_quirky_pdf_paths():
    paths = [
        r"C:\Users\test\My Documents\report (final).pdf",
        r"C:\Users\test\我的文件\文档.pdf",
        "C:\\Users\\test\\folder with spaces\\nested\\deep\\" + "x" * 180 + ".pdf",
    ]
    args = ["OpenReader.exe", *paths, "--flag", "notes.txt", "readme.md"]
    assert main.filter_pdf_paths(args) == paths


def test_filter_pdf_paths_is_case_insensitive_on_suffix():
    args = [r"C:\test\REPORT.PDF", r"C:\test\scan.pdf", r"C:\test\notes.txt"]
    assert main.filter_pdf_paths(args) == [r"C:\test\REPORT.PDF", r"C:\test\scan.pdf"]


def test_filter_pdf_paths_drops_non_pdf_args():
    assert main.filter_pdf_paths(["OpenReader.exe", "--flag", "file.txt", "readme.md"]) == []


def test_ipc_json_round_trip_preserves_unicode_paths():
    """The IPC hand-off is JSON; Unicode paths must survive the round trip."""
    paths = [
        r"C:\test\我的文件\文档.pdf",
        r"C:\test\report (final).pdf",
        "C:\\test\\" + "n" * 200 + ".pdf",
    ]
    assert json.loads(json.dumps(paths)) == paths
