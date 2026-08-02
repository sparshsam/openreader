"""Tests for channel-aware update gating (v1.2.7).

Covers the pure ``should_suppress_silent_notify`` helper and the presence of
the store-aware dialogs/helpers wired into main.py.
"""

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
