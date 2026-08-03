"""Tests for channel-aware update gating (v1.2.7).

Covers the pure ``should_suppress_silent_notify`` helper, the presence of the
store-aware dialogs/helpers wired into main.py, and safe semantic-version
comparison for development/test version strings.
"""

import json

import main


def test_skip_suppresses_same_release():
    result = {"outcome": "update_available", "latest_tag": "v1.2.7"}
    assert main.should_suppress_silent_notify(result, "v1.2.7") is True


def test_newer_release_still_notifies():
    result = {"outcome": "update_available", "latest_tag": "v1.2.8"}
    assert main.should_suppress_silent_notify(result, "v1.2.7") is False


def test_no_skip_preference_notifies():
    result = {"outcome": "update_available", "latest_tag": "v1.2.7"}
    assert main.should_suppress_silent_notify(result, "") is False
    assert main.should_suppress_silent_notify(result, None) is False


def test_non_update_outcomes_never_suppressed():
    for outcome in ("already_latest", "network_error", "http_error", "json_error"):
        result = {"outcome": outcome, "latest_tag": "v1.2.7"}
        assert main.should_suppress_silent_notify(result, "v1.2.7") is False


def test_store_aware_pieces_exist():
    assert hasattr(main, "_SoftwareUpdatesDialog")
    assert hasattr(main.PdfReaderWindow, "_is_store")
    assert main.SETTINGS_UPDATE_SKIP_KEY == "updateSkipVersion"
    assert main.SETTINGS_UPDATE_LAST_CHECKED_KEY == "updateLastChecked"


# ---------------------------------------------------------------------------
# Semantic-version comparison safety (1.2.7-test vs 1.2.4 / 1.2.7 / 1.2.8)
# ---------------------------------------------------------------------------


def test_parse_version_strips_test_and_prerelease_suffixes():
    parse = main.PdfReaderWindow._parse_version
    assert parse("1.2.7-test") == (1, 2, 7)
    assert parse("1.2.7") == (1, 2, 7)
    assert parse("v1.2.7") == (1, 2, 7)
    assert parse("1.2.4") == (1, 2, 4)
    assert parse("v1.2.8-beta.1") == (1, 2, 8)


def test_parse_version_rejects_malformed():
    assert main.PdfReaderWindow._parse_version("not_a_version") is None
    assert main.PdfReaderWindow._parse_version("") is None


def _classify(tag, current):
    return main.PdfReaderWindow._classify_update_response(
        200, False, "", json.dumps({"tag_name": tag}), current
    )


def test_test_build_not_downgraded_by_older_release():
    """1.2.7-test must never report v1.2.4 as newer."""
    result = _classify("v1.2.4", "1.2.7-test")
    assert result["outcome"] == "already_latest"


def test_test_build_vs_same_base_release():
    result = _classify("v1.2.7", "1.2.7-test")
    assert result["outcome"] == "already_latest"


def test_newer_release_still_notifies_test_build():
    result = _classify("v1.2.8", "1.2.7-test")
    assert result["outcome"] == "update_available"


def test_malformed_remote_version_is_json_error():
    result = _classify("garbage", "1.2.7")
    assert result["outcome"] == "json_error"


def test_missing_remote_tag_is_json_error():
    result = main.PdfReaderWindow._classify_update_response(
        200, False, "", json.dumps({"draft": True}), "1.2.7"
    )
    assert result["outcome"] == "json_error"


def test_unparseable_current_version_falls_back_to_update_available():
    result = _classify("v1.2.8", "not_a_version")
    assert result["outcome"] == "update_available"
