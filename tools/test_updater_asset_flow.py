"""Regression checks for updater release-asset metadata flow."""

from pathlib import Path
from unittest.mock import patch

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from main import (  # noqa: E402
    MACOS_APPLE_SILICON_UPDATE_ASSET,
    MACOS_INTEL_UPDATE_ASSET,
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
    assert_equal(method, "windows_zip", "Windows ZIP route")
    assert_equal(diagnostic, "", "Windows ZIP diagnostic")


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


if __name__ == "__main__":
    test_platform_asset_selection()
    test_windows_download_filename_and_route()
    test_missing_metadata_fails_loudly()
    test_windows_wrong_asset_does_not_route_to_zip_installer()
    print("Updater asset flow regression checks passed.")
