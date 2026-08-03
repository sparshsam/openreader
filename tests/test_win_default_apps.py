"""Tests for pdfreader_lib.win_default_apps (Windows default-app detection).

The registry is faked with an in-memory HKCU + HKLM tree so no real registry
is touched. On non-Windows without a patch, every function must return a
neutral value.
"""

import sys

import pytest

from pdfreader_lib import win_default_apps as wda


class _Handle:
    """Opaque registry key handle."""

    def __init__(self, root, path):
        self.root = root
        self.path = path


class FakeWinreg:
    """In-memory HKCU + HKLM registry: {hive: {path: {value_name: value}}}."""

    HKEY_CURRENT_USER = "HKCU"
    HKEY_LOCAL_MACHINE = "HKLM"

    def __init__(self):
        self._trees = {self.HKEY_CURRENT_USER: {}, self.HKEY_LOCAL_MACHINE: {}}

    def _tree(self, root):
        return self._trees.setdefault(root, {})

    def set_value(self, path, name, value, root=None):
        self._tree(root or self.HKEY_CURRENT_USER).setdefault(path, {})[name] = value

    def set_key(self, path, root=None):
        self._tree(root or self.HKEY_CURRENT_USER).setdefault(path, {})

    # -- winreg API used by the module -------------------------------
    def OpenKey(self, root, path):
        tree = self._tree(root)
        # Registry semantics: opening an ancestor of an existing key works.
        if path in tree:
            return _Handle(root, path)
        prefix = path + "\\" if path else ""
        if any(key.startswith(prefix) for key in tree):
            return _Handle(root, path)
        raise FileNotFoundError(path)

    def QueryValueEx(self, handle, name):
        node = self._tree(handle.root).get(handle.path, {})
        if name not in node:
            raise FileNotFoundError(name)
        return (node[name], None)

    def EnumKey(self, handle, index):
        tree = self._tree(handle.root)
        prefix = handle.path + "\\" if handle.path else ""
        subkeys = set()
        for key in tree:
            if key.startswith(prefix):
                rest = key[len(prefix):]
                if rest:
                    subkeys.add(rest.split("\\")[0])
        ordered = sorted(subkeys)
        if index >= len(ordered):
            raise OSError("no more keys")
        return ordered[index]

    def CloseKey(self, handle):
        pass


@pytest.fixture
def fake_windows(monkeypatch):
    fake = FakeWinreg()
    monkeypatch.setattr(wda, "winreg", fake)
    monkeypatch.setattr(sys, "platform", "win32")
    return fake


# ---------------------------------------------------------------------------
# Non-Windows neutrality
# ---------------------------------------------------------------------------


def test_non_windows_returns_neutral():
    assert wda.is_windows() is False
    assert wda.get_userchoice_progid() is None
    assert wda.resolve_progid_owner("OpenReaderPDF") is None
    assert wda.default_app_owner() == (False, None)
    assert wda.association_registered() is False
    assert wda.friendly_app_name("Acrobat.Document.DC") is None
    assert wda.open_default_apps_settings() is False


# ---------------------------------------------------------------------------
# Inno installer channel
# ---------------------------------------------------------------------------


def test_inno_progid_detected_as_default(fake_windows):
    fake_windows.set_value(wda.USERCHOICE_KEY, "ProgId", wda.INNO_PROGID)
    fake_windows.set_key(rf"{wda.CLASSES_KEY}\{wda.INNO_PROGID}")
    assert wda.default_app_owner() == (True, wda.INNO_PROGID)
    assert wda.resolve_progid_owner(wda.INNO_PROGID) == wda.OPENREADER
    assert wda.association_registered() is True


def test_inno_progid_registered_under_hklm_still_detected(fake_windows):
    """Admin Inno installs write HKCR entries to HKLM; registration must still resolve."""
    fake_windows.set_value(wda.USERCHOICE_KEY, "ProgId", wda.INNO_PROGID)
    fake_windows.set_key(
        rf"{wda.CLASSES_KEY}\{wda.INNO_PROGID}",
        root=fake_windows.HKEY_LOCAL_MACHINE,
    )
    assert wda.default_app_owner() == (True, wda.INNO_PROGID)
    assert wda.association_registered() is True


def test_inno_progid_resolved_via_shell_command(fake_windows):
    """Ownership is defensible via the registered open command, not just the name."""
    progid = "OpenReaderPDF.Generated"  # hypothetical generated identifier
    fake_windows.set_value(
        rf"{wda.CLASSES_KEY}\{progid}\shell\open\command",
        None,
        '"C:\\Program Files\\OpenReader\\OpenReader.exe" "%1"',
    )
    assert wda.resolve_progid_owner(progid) == wda.OPENREADER


# ---------------------------------------------------------------------------
# MSIX / AppX channel
# ---------------------------------------------------------------------------


def test_appx_progid_resolved_via_aumid(fake_windows):
    progid = "AppXsomepkgopenreader"
    fake_windows.set_value(wda.USERCHOICE_KEY, "ProgId", progid)
    fake_windows.set_value(
        rf"{wda.CLASSES_KEY}\{progid}\Application", "AppUserModelId", wda.AUMID
    )
    assert wda.resolve_progid_owner(progid) == wda.OPENREADER
    assert wda.default_app_owner() == (True, progid)
    assert wda.association_registered() is True


def test_appx_scan_finds_our_aumid_under_hklm(fake_windows):
    """Packaged registration may land in either hive; both are scanned."""
    fake_windows.set_value(
        rf"{wda.CLASSES_KEY}\AppXours\Application",
        "AppUserModelId",
        wda.AUMID,
        root=fake_windows.HKEY_LOCAL_MACHINE,
    )
    fake_windows.set_value(
        rf"{wda.CLASSES_KEY}\AppXothers\Application",
        "AppUserModelId",
        "OtherApp!X",
        root=fake_windows.HKEY_LOCAL_MACHINE,
    )
    assert wda.association_registered() is True


# ---------------------------------------------------------------------------
# Other / unknown / missing handlers
# ---------------------------------------------------------------------------


def test_other_app_is_default(fake_windows):
    progid = "Acrobat.Document.DC"
    fake_windows.set_value(wda.USERCHOICE_KEY, "ProgId", progid)
    fake_windows.set_value(
        rf"{wda.CLASSES_KEY}\{progid}\Application",
        "AppUserModelId",
        "Acrobat!DC",
    )
    assert wda.default_app_owner() == (False, progid)
    assert wda.resolve_progid_owner(progid) == wda.OTHER


def test_other_app_resolved_via_shell_command(fake_windows):
    progid = "Acrobat.Document.DC"
    fake_windows.set_value(
        rf"{wda.CLASSES_KEY}\{progid}\shell\open\command",
        None,
        '"C:\\Program Files (x86)\\Adobe\\Acrobat Reader DC\\Reader\\AcroRd32.exe" "%1"',
    )
    assert wda.resolve_progid_owner(progid) == wda.OTHER


def test_unresolvable_progid_is_unknown(fake_windows):
    progid = "Some.Opaque.ProgId"
    fake_windows.set_value(wda.USERCHOICE_KEY, "ProgId", progid)
    assert wda.default_app_owner() == (False, progid)
    assert wda.resolve_progid_owner(progid) is None


def test_missing_userchoice_reports_no_default(fake_windows):
    assert wda.default_app_owner() == (False, None)


def test_no_association_registered(fake_windows):
    assert wda.association_registered() is False


# ---------------------------------------------------------------------------
# Friendly names and opening Default Apps
# ---------------------------------------------------------------------------


def test_friendly_app_name_from_application_subkey(fake_windows):
    progid = "Acrobat.Document.DC"
    fake_windows.set_value(
        rf"{wda.CLASSES_KEY}\{progid}\Application", "FriendlyAppName", "Acrobat Reader"
    )
    assert wda.friendly_app_name(progid) == "Acrobat Reader"


def test_friendly_app_name_falls_back_to_default_value(fake_windows):
    progid = wda.INNO_PROGID
    fake_windows.set_value(rf"{wda.CLASSES_KEY}\{progid}", None, "PDF Document")
    assert wda.friendly_app_name(progid) == "PDF Document"


def test_open_default_apps_settings_on_windows(fake_windows, monkeypatch):
    calls = []

    def fake_startfile(target):
        calls.append(target)

    monkeypatch.setattr(wda.os, "startfile", fake_startfile, raising=False)
    assert wda.open_default_apps_settings() is True
    assert calls == ["ms-settings:defaultapps"]


def test_open_default_apps_settings_failure(fake_windows, monkeypatch):
    def boom(_):
        raise OSError("no shell")

    monkeypatch.setattr(wda.os, "startfile", boom, raising=False)
    assert wda.open_default_apps_settings() is False
