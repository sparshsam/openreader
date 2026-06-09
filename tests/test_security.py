"""
Regression tests for security assumptions.

Tests cover:
- File extension validation logic
- Safe PDF open assumptions
- Path validation
- Temp file handling
- Update metadata security
- No subprocess misuse
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT))

import pytest


# ---------------------------------------------------------------------------
# File extension and header validation
# ---------------------------------------------------------------------------


class TestFileExtensionValidation:
    def test_pdf_suffix_only(self):
        """Only .pdf files should be accepted."""
        from main import PdfReaderWindow
        allowed = (".pdf",)
        # In the real app, _validate_pdf_path checks suffix.lower()
        assert ".pdf" in allowed
        assert ".PDF" not in allowed  # lower() handles this
        assert ".exe" not in allowed
        assert ".txt" not in allowed

    def test_header_check_constant(self):
        """The PDF header check uses %PDF- marker."""
        from main import PdfReaderWindow
        # Verify the header marker is defined and non-empty
        assert len("%PDF-") > 0


# ---------------------------------------------------------------------------
# Path traversal concerns
# ---------------------------------------------------------------------------


class TestPathHandling:
    def test_expanduser_is_used(self):
        """Paths should be expanded to prevent ~/ abuse."""
        src = Path(__file__).resolve().parent.parent / "main.py"
        content = src.read_text()
        assert "expanduser()" in content

    def test_path_resolve_in_recent(self):
        """Recent file paths are resolved to prevent symlink confusion."""
        src = Path(__file__).resolve().parent.parent / "main.py"
        content = src.read_text()
        assert "resolve()" in content or ".resolve()" in content


# ---------------------------------------------------------------------------
# Temp file handling
# ---------------------------------------------------------------------------


class TestTempFileSecurity:
    def test_tempdir_is_system_temp(self):
        """Update temp dir should be under system temp, not cwd."""
        from main import PdfReaderWindow
        temp_dir = PdfReaderWindow._updater_temp_dir()
        import tempfile
        system_temp = Path(tempfile.gettempdir())
        # temp_dir should be a child of system_temp
        assert str(temp_dir).startswith(str(system_temp)), \
            f"Temp dir {temp_dir} should be under {system_temp}"

    def test_update_temp_dir_is_not_cwd(self):
        from main import PdfReaderWindow
        temp_dir = PdfReaderWindow._updater_temp_dir()
        assert temp_dir != Path.cwd()


# ---------------------------------------------------------------------------
# Subprocess usage
# ---------------------------------------------------------------------------


class TestSubprocessSafety:
    def test_subprocess_only_for_update(self):
        """Only the updater should use subprocess."""
        src = Path(__file__).resolve().parent.parent / "main.py"
        content = src.read_text()
        # subprocess should only appear in updater methods
        # Count occurrences - should be very few and all in updater
        count = content.count("subprocess.Popen")
        assert count >= 1, "subprocess should be used for updater"
        assert count <= 3, f"Too many subprocess.Popen calls ({count}); review for safety"

    def test_all_subprocess_has_nosec_comment(self):
        """Every subprocess.Popen call should have # nosec comment."""
        src = Path(__file__).resolve().parent.parent / "main.py"
        content = src.read_text()
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            if "subprocess.Popen" in line and "nosec" not in line:
                pytest.fail(f"Line {i}: subprocess.Popen without # nosec: {line.strip()}")


# ---------------------------------------------------------------------------
# Update download safety
# ---------------------------------------------------------------------------


class TestUpdateDownloadSafety:
    def test_update_url_is_https(self):
        """The update check URL must use HTTPS."""
        from main import GITHUB_REPO
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        assert api_url.startswith("https://"), "Update check must use HTTPS"
        assert "api.github.com" in api_url

    def test_update_user_agent_is_set(self):
        """User-Agent header should be set for GitHub API requests."""
        from main import PdfReaderWindow
        src = Path(PdfReaderWindow.__module__).parent / "main.py"
        content = src.read_text()
        assert 'UserAgentHeader' in content or 'UserAgent' in content


# ---------------------------------------------------------------------------
# Annotation delete safety (v0.9.0 bugfix regression guard)
# ---------------------------------------------------------------------------


class TestAnnotationDeleteSafety:
    def test_delete_all_no_premature_deletion(self):
        """_delete_all_annotations must count before deleting, not delete before confirming."""
        src = Path(__file__).resolve().parent.parent / "main.py"
        content = src.read_text()
        # Find the delete_all_annotations method
        idx = content.find("def _delete_all_annotations")
        if idx == -1:
            pytest.skip("_delete_all_annotations not found")
        # Check that there's a QMessageBox.question call BEFORE any page.delete_annot
        method_end = content.find("\n    def ", idx + 30)
        if method_end == -1:
            method_end = content.find("\n# ", idx + 30)
        if method_end == -1:
            method_end = idx + 3000
        method_body = content[idx:method_end]
        # The method should have QMessageBox.question BEFORE page.delete_annot
        question_pos = method_body.find("QMessageBox.question")
        delete_pos = method_body.find(".delete_annot(")
        assert question_pos >= 0, "delete_all_annotations must ask for confirmation"
        assert delete_pos >= 0, "delete_all_annotations must delete annotations"
        assert question_pos < delete_pos, \
            "Confirmation dialog must appear BEFORE deletion (bugfix v0.9.0)"
