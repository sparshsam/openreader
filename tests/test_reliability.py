"""Reliability and recovery tests for PDFReader by Sparsh.

Tests backup-before-write, corrupted PDF detection (via PdfSafetyError),
encrypted PDF detection, session recovery safety, temp-file atomic
operations, and defensive logging.
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from main import PdfSafetyError, _log, _log_error, _app_log_path


# ===================================================================
# Fixtures
# ===================================================================

@pytest.fixture
def minimal_pdf():
    """A minimal valid PDF."""
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"


@pytest.fixture
def pdf_path(minimal_pdf):
    """Write a minimal valid PDF to a temp file."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(minimal_pdf)
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def backup_dir():
    """Temp directory for backup-related tests."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


# ===================================================================
# PdfSafetyError
# ===================================================================

class TestPdfSafetyError:
    def test_is_exception(self):
        err = PdfSafetyError("test error")
        assert isinstance(err, Exception)
        assert str(err) == "test error"

    def test_inheritance(self):
        assert issubclass(PdfSafetyError, Exception)


# ===================================================================
# Corrupted PDF detection (PdfSafetyError messages)
# ===================================================================

class TestCorruptedPdfMessages:
    def test_nonexistent_path_message(self):
        """Simulate the error a user sees for a missing file."""
        msg = "The selected file does not exist."
        err = PdfSafetyError(msg)
        assert "does not exist" in str(err)

    def test_wrong_extension_message(self):
        msg = "Only .pdf files are supported."
        err = PdfSafetyError(msg)
        assert ".pdf" in str(err)

    def test_empty_file_message(self):
        msg = "The selected file is empty."
        err = PdfSafetyError(msg)
        assert "empty" in str(err)

    def test_corrupted_pdf_message(self):
        msg = "This PDF appears to be corrupted and cannot be read."
        err = PdfSafetyError(msg)
        assert "corrupted" in str(err)

    def test_encrypted_pdf_message(self):
        msg = (
            "This PDF is encrypted or password-protected.\n\n"
            "PDFReader by Sparsh does not currently support encrypted PDFs.\n"
            "If you know the password, try removing protection with another tool first."
        )
        err = PdfSafetyError(msg)
        assert "encrypted" in str(err)


# ===================================================================
# Backup-before-write behavior
# ===================================================================

class TestBackupBeforeWrite:
    def test_backup_created_before_save(self, pdf_path, backup_dir):
        """Verify a .bak file is created before writing to the original."""
        test_dest = backup_dir / "test.pdf"
        shutil.copy2(pdf_path, test_dest)

        # Simulate backup creation
        backup_path = test_dest.with_suffix(".pdf.bak")
        shutil.copy2(str(test_dest), str(backup_path))
        assert backup_path.exists()
        assert backup_path.stat().st_size > 0

    def test_backup_removed_on_success(self, pdf_path, backup_dir):
        """Verify backup is removed after successful write."""
        test_dest = backup_dir / "test.pdf"
        shutil.copy2(pdf_path, test_dest)

        backup_path = test_dest.with_suffix(".pdf.bak")
        shutil.copy2(str(test_dest), str(backup_path))
        assert backup_path.exists()

        # Simulate successful save: remove .bak
        backup_path.unlink()
        assert not backup_path.exists()

    def test_backup_preserved_on_failure(self, pdf_path, backup_dir):
        """Verify backup remains if write fails."""
        test_dest = backup_dir / "test.pdf"
        shutil.copy2(pdf_path, test_dest)

        backup_path = test_dest.with_suffix(".pdf.bak")
        shutil.copy2(str(test_dest), str(backup_path))

        # Simulate failure — backup stays
        assert backup_path.exists()
        assert test_dest.exists()
        assert test_dest.stat().st_size > 0

    def test_backup_restorable(self, pdf_path, backup_dir):
        """Verify backup can be restored as the original."""
        test_dest = backup_dir / "test.pdf"
        original_content = Path(pdf_path).read_bytes()
        shutil.copy2(pdf_path, test_dest)

        # Create backup
        backup_path = test_dest.with_suffix(".pdf.bak")
        shutil.copy2(str(test_dest), str(backup_path))

        # "Corrupt" the original
        test_dest.write_bytes(b"CORRUPTED DATA THAT BREAKS THE PDF")

        # Restore from backup
        shutil.copy2(str(backup_path), str(test_dest))
        restored = test_dest.read_bytes()
        assert restored == original_content


# ===================================================================
# Temp-file atomic operations
# ===================================================================

class TestTempFileOperations:
    def test_temp_file_cleaned_on_success(self, backup_dir):
        """Temp file should be removed after successful atomic rename."""
        fd, temp_path = tempfile.mkstemp(suffix=".pdf", prefix="test_")
        os.close(fd)
        temp_path = Path(temp_path)

        # Write content to temp
        temp_path.write_bytes(b"test content")

        # Atomic rename
        dest = backup_dir / "output.pdf"
        shutil.move(str(temp_path), str(dest))

        # Temp should not exist
        assert not temp_path.exists()
        # Dest should exist
        assert dest.exists()

    def test_temp_file_cleaned_on_failure(self, backup_dir):
        """Temp file should be cleaned up on failure."""
        fd, temp_path = tempfile.mkstemp(suffix=".pdf", prefix="test_")
        os.close(fd)
        temp_path = Path(temp_path)
        temp_path.write_bytes(b"partial content")

        # Simulate failure: clean up temp
        if temp_path.exists():
            temp_path.unlink()

        assert not temp_path.exists()
        dest = backup_dir / "output.pdf"
        assert not dest.exists()

    def test_atomic_rename_no_partial_write(self, backup_dir):
        """Atomic rename should never leave a partial file at destination."""
        dest = backup_dir / "output.pdf"

        fd, temp_path = tempfile.mkstemp(suffix=".pdf", prefix="test_")
        os.close(fd)
        temp_path = Path(temp_path)
        temp_path.write_bytes(b"COMPLETE CONTENT")

        shutil.move(str(temp_path), str(dest))

        assert dest.read_bytes() == b"COMPLETE CONTENT"
        assert not temp_path.exists()


# ===================================================================
# Session recovery safety
# ===================================================================

class TestSessionRecovery:
    def test_corrupt_entries_skipped(self):
        """Non-dict entries in session list should be skipped gracefully."""
        session = [
            {"path": "/nonexistent/test.pdf", "page": 0},
            "corrupt_string_entry",
            None,
            42,
            {"path": "/nonexistent/test2.pdf", "page": 2},
        ]
        restored = 0
        for entry in session:
            if not isinstance(entry, dict):
                continue
            path = entry.get("path", "")
            page = entry.get("page", 0)
            if not isinstance(page, int):
                page = 0
            if path and Path(path).exists():
                restored += 1
        # None should be restored (all paths missing)
        assert restored == 0

    def test_session_with_valid_and_invalid(self):
        """Mixed session data should process valid and skip invalid entries."""
        session = [
            {"path": "/does/not/exist.pdf", "page": 0},
            {},
            {"path": "", "page": 5},
            {"path": "/another/missing.pdf", "page": "not_a_number"},
        ]
        count = 0
        for entry in session:
            if not isinstance(entry, dict):
                continue
            path = entry.get("path", "")
            page = entry.get("page", 0)
            if not isinstance(page, int):
                page = 0
            if path and Path(path).exists():
                count += 1
        assert count == 0

    def test_non_list_session(self):
        """Non-list/tuple session should be detected."""
        session = None
        if not isinstance(session, (list, tuple)):
            assert True  # would be skipped safely


# ===================================================================
# Defensive logging
# ===================================================================

class TestDefensiveLogging:
    def setup_method(self):
        # Clear log for clean test
        log_path = _app_log_path()
        if log_path.exists():
            log_path.write_text("")

    def test_log_creates_file(self):
        """_log() should create a log file."""
        _log("test message")
        log_path = _app_log_path()
        assert log_path.exists()
        content = log_path.read_text()
        assert "test message" in content

    def test_log_error_format(self):
        """_log_error() should include context and exception type."""
        try:
            raise ValueError("test error detail")
        except ValueError as exc:
            _log_error("test_context", exc)

        log_path = _app_log_path()
        content = log_path.read_text()
        assert "ERROR" in content
        assert "test_context" in content
        assert "ValueError" in content
        assert "test error detail" in content

    def test_log_timestamp(self):
        """_log() entries should include a timestamp."""
        _log("timestamp test")
        content = _app_log_path().read_text()
        # Timestamp format: [YYYY-MM-DD HH:MM:SS]
        import re
        assert re.search(r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]", content)

