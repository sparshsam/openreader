"""Regression checks for updater release-asset metadata flow."""
import json

from pathlib import Path
from unittest.mock import patch

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from main import (  # noqa: E402
    MACOS_APPLE_SILICON_UPDATE_ASSET,
    MACOS_INTEL_UPDATE_ASSET,
    WINDOWS_INSTALLER_ASSET,
    WINDOWS_PORTABLE_ASSET,
    WINDOWS_UPDATE_ASSET,
    PdfReaderWindow,
)


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def assert_true(value, label):
    if not value:
        raise AssertionError(label)


def canonical_assets():
    return [
        {
            "name": WINDOWS_UPDATE_ASSET,
            "browser_download_url": f"https://example.test/{WINDOWS_UPDATE_ASSET}",
        },
        {
            "name": WINDOWS_PORTABLE_ASSET,
            "browser_download_url": f"https://example.test/{WINDOWS_PORTABLE_ASSET}",
        },
        {
            "name": MACOS_APPLE_SILICON_UPDATE_ASSET,
            "browser_download_url": f"https://example.test/{MACOS_APPLE_SILICON_UPDATE_ASSET}",
        },
        {
            "name": MACOS_INTEL_UPDATE_ASSET,
            "browser_download_url": f"https://example.test/{MACOS_INTEL_UPDATE_ASSET}",
        },
    ]


def test_platform_asset_selection():
    assets = canonical_assets()

    with patch("platform.system", return_value="Windows"):
        _, asset_name = PdfReaderWindow._get_platform_asset(None, assets)
        assert_equal(asset_name, WINDOWS_UPDATE_ASSET, "Windows asset")

    with patch("platform.system", return_value="Darwin"), patch(
        "platform.machine", return_value="arm64"
    ):
        _, asset_name = PdfReaderWindow._get_platform_asset(None, assets)
        assert_equal(asset_name, MACOS_APPLE_SILICON_UPDATE_ASSET, "Apple Silicon asset")

    with patch("platform.system", return_value="Darwin"), patch(
        "platform.machine", return_value="x86_64"
    ):
        _, asset_name = PdfReaderWindow._get_platform_asset(None, assets)
        assert_equal(asset_name, MACOS_INTEL_UPDATE_ASSET, "Intel macOS asset")


def test_windows_download_filename_and_route():
    temp_dir = Path("C:/Temp/PDFReader-Updates")
    dest = temp_dir / WINDOWS_UPDATE_ASSET
    assert_equal(dest.name, WINDOWS_UPDATE_ASSET, "Windows download filename")
    assert_true("update_None" not in str(dest), "Windows destination must not contain update_None")

    method, diagnostic = PdfReaderWindow._select_update_apply_method(
        "Windows", WINDOWS_UPDATE_ASSET, dest
    )
    assert_equal(method, "windows_installer", "Windows installer route")
    assert_equal(diagnostic, "", "Windows installer diagnostic")


def test_windows_portable_zip_route_remains_explicit():
    temp_dir = Path("C:/Temp/PDFReader-Updates")
    dest = temp_dir / WINDOWS_PORTABLE_ASSET

    method, diagnostic = PdfReaderWindow._select_update_apply_method(
        "Windows", WINDOWS_PORTABLE_ASSET, dest
    )
    assert_equal(method, "windows_zip", "Windows portable ZIP route")
    assert_equal(diagnostic, "", "Windows portable ZIP diagnostic")


def test_missing_metadata_fails_loudly():
    asset_error = PdfReaderWindow._validate_download_metadata(None, "v0.3.2")
    assert_true(
        "could not determine the release asset name" in asset_error,
        "missing asset metadata diagnostic",
    )

    tag_error = PdfReaderWindow._validate_download_metadata(WINDOWS_UPDATE_ASSET, None)
    assert_true(
        "could not determine the release tag" in tag_error,
        "missing tag metadata diagnostic",
    )


def test_windows_wrong_asset_does_not_route_to_zip_installer():
    method, diagnostic = PdfReaderWindow._select_update_apply_method(
        "Windows", MACOS_APPLE_SILICON_UPDATE_ASSET, Path("C:/Temp/PDFReader-Updates/bad.zip")
    )
    assert_equal(method, None, "wrong Windows asset route")
    assert_true("Unsupported update package" in diagnostic, "wrong Windows asset diagnostic")




# --- Update check classification tests (v0.3.4) ---

_MAKE_RELEASE = lambda tag: json.dumps({
    "tag_name": tag,
    "html_url": "https://github.com/sparshsam/pdfreader-by-sparsh/releases/tag/" + tag,
    "body": "Test release notes.",
    "assets": [
        {"name": WINDOWS_INSTALLER_ASSET, "browser_download_url": "https://example.test/setup.exe"},
        {"name": WINDOWS_PORTABLE_ASSET, "browser_download_url": "https://example.test/pkg.zip"},
        {"name": "PDFReader-by-Sparsh-macOS-Apple-Silicon.zip", "browser_download_url": "https://example.test/mac-arm.zip"},
        {"name": "PDFReader-by-Sparsh-macOS-Intel.zip", "browser_download_url": "https://example.test/mac-intel.zip"},
    ],
})


def test_classify_already_latest():
    body = _MAKE_RELEASE("v0.3.3")
    r = PdfReaderWindow._classify_update_response(200, False, "", body, "0.3.3")
    assert_equal(r["outcome"], "already_latest", "already_latest outcome")
    assert_true("up to date" in r["message"], "already_latest message")
    assert_equal(r["latest_tag"], "v0.3.3", "already_latest tag")
    assert_equal(r["latest_version"], (0, 3, 3), "already_latest parsed version")


def test_classify_update_available():
    body = _MAKE_RELEASE("v0.3.4")
    r = PdfReaderWindow._classify_update_response(200, False, "", body, "0.3.3")
    assert_equal(r["outcome"], "update_available", "update_available outcome")
    assert_true("Update available" in r["message"], "update_available message")
    assert_equal(r["latest_tag"], "v0.3.4", "update_available tag")
    assert_equal(r["latest_version"], (0, 3, 4), "update_available parsed version")


def test_classify_already_latest_no_downgrade():
    body = _MAKE_RELEASE("v0.3.2")
    r = PdfReaderWindow._classify_update_response(200, False, "", body, "0.3.3")
    assert_equal(r["outcome"], "already_latest", "no-downgrade outcome")
    assert_true("up to date" in r["message"], "no-downgrade message")
    assert_equal(r["latest_tag"], "v0.3.2", "no-downgrade tag")


def test_classify_network_error():
    r = PdfReaderWindow._classify_update_response(None, True, "Connection refused", "", "0.3.3")
    assert_equal(r["outcome"], "network_error", "network_error outcome")
    assert_true("check your internet connection" in r["message"], "network_error message")


def test_classify_http_403():
    body = json.dumps({"message": "API rate limit exceeded"})
    r = PdfReaderWindow._classify_update_response(403, True, "Forbidden", body, "0.3.3")
    assert_equal(r["outcome"], "http_error", "HTTP 403 outcome")
    assert_true("rate limited" in r["message"].lower(), "HTTP 403 rate limit message")


def test_classify_http_404():
    r = PdfReaderWindow._classify_update_response(404, True, "Not Found", "", "0.3.3")
    assert_equal(r["outcome"], "http_error", "HTTP 404 outcome")
    assert_true("not found" in r["message"].lower(), "HTTP 404 not found message")


def test_classify_http_429():
    r = PdfReaderWindow._classify_update_response(429, True, "Too Many Requests", "", "0.3.3")
    assert_equal(r["outcome"], "http_error", "HTTP 429 outcome")
    assert_true("rate limited" in r["message"].lower(), "HTTP 429 rate limit message")


def test_classify_http_500():
    r = PdfReaderWindow._classify_update_response(500, True, "Internal Server Error", "", "0.3.3")
    assert_equal(r["outcome"], "http_error", "HTTP 500 outcome")
    assert_true("HTTP 500" in r["message"], "HTTP 500 status in message")


def test_classify_invalid_json():
    r = PdfReaderWindow._classify_update_response(200, False, "", "not json at all", "0.3.3")
    assert_equal(r["outcome"], "json_error", "invalid JSON outcome")
    assert_true("unexpected response" in r["message"], "invalid JSON message")


def test_classify_missing_tag():
    body = json.dumps({"assets": []})
    r = PdfReaderWindow._classify_update_response(200, False, "", body, "0.3.3")
    assert_equal(r["outcome"], "json_error", "missing tag outcome")
    assert_true("metadata missing" in r["message"], "missing tag message")


def test_classify_unparseable_tag():
    body = _MAKE_RELEASE("latest")
    r = PdfReaderWindow._classify_update_response(200, False, "", body, "0.3.3")
    assert_equal(r["outcome"], "json_error", "unparseable tag outcome")
    assert_true("could not parse" in r["message"], "unparseable tag message")
    assert_equal(r["latest_tag"], "latest", "unparseable tag stored")


if __name__ == "__main__":
    test_platform_asset_selection()
    test_windows_download_filename_and_route()
    test_windows_portable_zip_route_remains_explicit()
    test_missing_metadata_fails_loudly()
    test_windows_wrong_asset_does_not_route_to_zip_installer()

    test_classify_already_latest()
    test_classify_update_available()
    test_classify_already_latest_no_downgrade()
    test_classify_network_error()
    test_classify_http_403()
    test_classify_http_404()
    test_classify_http_429()
    test_classify_http_500()
    test_classify_invalid_json()
    test_classify_missing_tag()
    test_classify_unparseable_tag()
    print("All regression checks passed (both asset flow and update check classification).")
