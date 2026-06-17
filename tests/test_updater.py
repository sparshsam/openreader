"""
Regression tests for the update check system (mocked, no network).

Tests cover:
- Version parsing
- Update response classification (already_latest, update_available, network_error, etc.)

Note: MSIX/App Installer distribution replaces the old self-update download/apply pipeline,
so platform asset selection, download metadata validation, and update method selection
tests have been removed. Update detection still works (Help → Check for Updates opens the
releases page in a browser).
"""

import json
import platform
import sys
from pathlib import Path

import pytest


# We patch sys.modules before importing main to avoid PySide6 import failures in CI
# by importing only the static methods we need via importlib.
import importlib.util
import types


# ---------------------------------------------------------------------------
# Fixtures: mock module with just the static methods we need
# ---------------------------------------------------------------------------

@pytest.fixture
def tmpzip(tmp_path):
    """Return a path to a non-existent .zip file under tmp_path."""
    return str(tmp_path / "test.zip")


@pytest.fixture(scope="session")
def updater():
    """Load only the updator-related static methods from main.py."""
    spec = importlib.util.spec_from_file_location(
        "pdfreader_main", str(Path(__file__).parent.parent / "main.py")
    )
    mod = importlib.util.module_from_spec(spec)
    # Provide stubs for external deps so the module can be parsed
    _stub = types.ModuleType("fitz")
    _stub.Document = object
    sys.modules["fitz"] = _stub
    _stub2 = types.ModuleType("PySide6")
    sys.modules["PySide6"] = _stub2
    _stub3 = types.ModuleType("PySide6.QtCore")
    sys.modules["PySide6.QtCore"] = _stub3
    sys.modules["PySide6.QtGui"] = types.ModuleType("PySide6.QtGui")
    sys.modules["PySide6.QtWidgets"] = types.ModuleType("PySide6.QtWidgets")
    sys.modules["PySide6.QtNetwork"] = types.ModuleType("PySide6.QtNetwork")
    try:
        spec.loader.exec_module(mod)
    except ImportError:
        pytest.skip("PySide6 not available in this environment")
    return mod.PdfReaderWindow


# ---------------------------------------------------------------------------
# Version Parsing
# ---------------------------------------------------------------------------


class TestVersionParsing:
    def test_parse_semver_tag(self, updater):
        assert updater._parse_version("v0.3.1") == (0, 3, 1)

    def test_parse_no_prefix(self, updater):
        assert updater._parse_version("0.3.1") == (0, 3, 1)

    def test_parse_dev_suffix(self, updater):
        assert updater._parse_version("0.8.0-dev") == (0, 8, 0)

    def test_parse_malformed(self, updater):
        assert updater._parse_version("not_a_version") is None

    def test_parse_empty(self, updater):
        assert updater._parse_version("") is None

    def test_parse_prerelease(self, updater):
        assert updater._parse_version("v0.4.0-rc1") == (0, 4, 0)


# ---------------------------------------------------------------------------
# Update Response Classification
# ---------------------------------------------------------------------------


class TestUpdateClassification:
    @staticmethod
    def _classify(updater, http_status=None, network_error=False,
                  network_error_string="", response_body="", current_version="0.8.0"):
        return updater._classify_update_response(
            http_status, network_error, network_error_string,
            response_body, current_version,
        )

    def test_already_latest(self, updater):
        result = self._classify(
            updater,
            http_status=200,
            response_body=json.dumps({"tag_name": "v0.8.0"}),
            current_version="0.8.0",
        )
        assert result["outcome"] == "already_latest"
        assert "up to date" in result["message"].lower()

    def test_update_available(self, updater):
        result = self._classify(
            updater,
            http_status=200,
            response_body=json.dumps({"tag_name": "v0.9.0"}),
            current_version="0.8.0",
        )
        assert result["outcome"] == "update_available"
        assert "0.9.0" in result["message"]

    def test_network_error(self, updater):
        result = self._classify(
            updater,
            http_status=None,
            network_error=True,
            network_error_string="Connection refused",
        )
        assert result["outcome"] == "network_error"
        assert "connection" in result["message"].lower()

    def test_http_403(self, updater):
        result = self._classify(
            updater, http_status=403, response_body="{}"
        )
        assert result["outcome"] == "http_error"
        assert "rate limited" in result["message"].lower()

    def test_http_404(self, updater):
        result = self._classify(
            updater, http_status=404, response_body="{}"
        )
        assert result["outcome"] == "http_error"
        assert "not found" in result["message"].lower()

    def test_http_429(self, updater):
        result = self._classify(
            updater, http_status=429, response_body="{}"
        )
        assert result["outcome"] == "http_error"
        assert "rate limited" in result["message"].lower()

    def test_http_500(self, updater):
        result = self._classify(
            updater, http_status=500, response_body="{}"
        )
        assert result["outcome"] == "http_error"
        assert "500" in result["message"]

    def test_json_decode_error(self, updater):
        result = self._classify(
            updater, http_status=200, response_body="not json at all"
        )
        assert result["outcome"] == "json_error"

    def test_missing_tag_in_response(self, updater):
        result = self._classify(
            updater,
            http_status=200,
            response_body=json.dumps({"no_tag_here": True}),
        )
        assert result["outcome"] == "json_error"

    def test_dev_version_no_current(self, updater):
        """-dev versions without a current parsed version should still detect updates."""
        result = self._classify(
            updater,
            http_status=200,
            response_body=json.dumps({"tag_name": "v0.9.0"}),
            current_version="0.9.0-dev",
        )
        # 0.9.0-dev -> (0, 9, 0), latest is (0, 9, 0), so already_latest
        assert result["outcome"] == "already_latest"

    def test_downgrade_protection(self, updater):
        """If remote tag is lower than current, report already_latest."""
        result = self._classify(
            updater,
            http_status=200,
            response_body=json.dumps({"tag_name": "v0.7.0"}),
            current_version="0.8.0",
        )
        assert result["outcome"] == "already_latest"

    def test_unparseable_current(self, updater):
        """If curVersion can't be parsed, treat as update available."""
        result = self._classify(
            updater,
            http_status=200,
            response_body=json.dumps({"tag_name": "v0.9.0"}),
            current_version="not_a_version",
        )
        assert result["outcome"] == "update_available"


# ---------------------------------------------------------------------------
# Platform Asset Selection
# ---------------------------------------------------------------------------
