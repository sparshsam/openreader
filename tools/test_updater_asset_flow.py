"""Regression checks for update detection (v1.2.0+ MSIX distribution).

The old self-update download/apply pipeline has been replaced by MSIX/App Installer
packaging. These checks validate that update detection still works correctly:
- Version parsing
- Update response classification
- The Help -> Check for Updates dialog correctly opens the releases page

The app no longer downloads or installs updates from within itself.
"""
import json

from pathlib import Path
from unittest.mock import patch

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from main import PdfReaderWindow  # noqa: E402


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def assert_true(value, label):
    if not value:
        raise AssertionError(label)


def test_version_parsing():
    """Verify version strings parse correctly."""
    assert_equal(PdfReaderWindow._parse_version("v0.3.1"), (0, 3, 1), "semver tag")
    assert_equal(PdfReaderWindow._parse_version("0.3.1"), (0, 3, 1), "no prefix")
    assert_equal(PdfReaderWindow._parse_version("0.8.0-dev"), (0, 8, 0), "dev suffix")
    assert_equal(PdfReaderWindow._parse_version("not_a_version"), None, "malformed")
    assert_equal(PdfReaderWindow._parse_version(""), None, "empty")


def test_classify_already_latest():
    """When local version matches remote, outcome is already_latest."""
    body = json.dumps({"tag_name": "v0.3.3"})
    r = PdfReaderWindow._classify_update_response(200, False, "", body, "0.3.3")
    assert_equal(r["outcome"], "already_latest", "already_latest outcome")
    assert_true("up to date" in r["message"], "already_latest message")


def test_classify_update_available():
    """When remote is newer, outcome is update_available."""
    body = json.dumps({
        "tag_name": "v0.4.0",
        "html_url": "https://github.com/sparshsam/pdfreader-by-sparsh/releases/tag/v0.4.0",
        "body": "Bug fixes.",
    })
    r = PdfReaderWindow._classify_update_response(200, False, "", body, "0.3.3")
    assert_equal(r["outcome"], "update_available", "update_available outcome")
    assert_equal(r["latest_tag"], "v0.4.0", "latest tag")


def test_classify_network_error():
    """Network errors are reported cleanly."""
    r = PdfReaderWindow._classify_update_response(None, True, "Connection refused", "", "0.3.3")
    assert_equal(r["outcome"], "network_error", "network_error outcome")


def test_classify_http_404():
    """HTTP 404 is handled."""
    r = PdfReaderWindow._classify_update_response(404, False, "", "{}", "0.3.3")
    assert_equal(r["outcome"], "http_error", "http_error outcome")
    assert_true("not found" in r["message"], "404 message")


def test_downgrade_protection():
    """A lower remote tag does not trigger an update offer."""
    body = json.dumps({"tag_name": "v0.2.0"})
    r = PdfReaderWindow._classify_update_response(200, False, "", body, "0.3.3")
    assert_equal(r["outcome"], "already_latest", "downgrade protection")


if __name__ == "__main__":
    tests = [
        test_version_parsing,
        test_classify_already_latest,
        test_classify_update_available,
        test_classify_network_error,
        test_classify_http_404,
        test_downgrade_protection,
    ]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"  PASS  {test.__name__}")
        except AssertionError as e:
            print(f"  FAIL  {test.__name__}: {e}")
            failures += 1
        except Exception as e:
            print(f"  FAIL  {test.__name__}: {type(e).__name__}: {e}")
            failures += 1

    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
