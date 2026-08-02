"""Windows default-app detection and Default-apps integration for OpenReader.

OpenReader registers ``.pdf`` through two distribution channels:

- **MSIX / Microsoft Store** — Windows creates an OS-generated
  (AppX-namespaced) ProgID for the declared ``windows.fileTypeAssociation`` at
  install time. That literal ProgID string is never matched; ownership is
  resolved by reading the ``AppUserModelId`` under
  ``HKCU\\Software\\Classes\\<progid>\\Application`` and comparing it to
  OpenReader's Application User Model ID (AUMID).
- **Legacy Inno installer** — writes the fixed ProgID ``OpenReaderPDF``
  directly to the registry (see installer/setup.iss).

Windows remains the final authority on defaults. This module only *reads* the
``UserChoice`` registry value and opens the Default Apps settings page; it
never writes the hash-protected ``UserChoice`` value, so OpenReader cannot
silently take over the PDF default.

Every function is defensive: on non-Windows platforms (macOS, WSL dev) or when
the registry cannot be read, it returns a neutral value rather than raising.
"""

import os
import sys

try:
    import winreg
except ImportError:  # pragma: no cover - non-Windows
    winreg = None

PFN = "SparshSam.OpenReader_yh0byntbzd2qw"
APPLICATION_ID = "OpenReader"
AUMID = f"{PFN}!{APPLICATION_ID}"

INNO_PROGID = "OpenReaderPDF"

USERCHOICE_KEY = (
    r"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pdf\UserChoice"
)
CLASSES_KEY = r"Software\Classes"

# resolve_progid_owner() outcomes
OPENREADER = "openreader"
OTHER = "other"


def is_windows() -> bool:
    """True when running on Windows with a usable registry module."""
    return winreg is not None and sys.platform.startswith("win")


def _open_key(path: str):
    """Open a key under HKCU\\Software\\Classes-ish path; return handle or None."""
    if not is_windows():
        return None
    try:
        return winreg.OpenKey(winreg.HKEY_CURRENT_USER, path)
    except OSError:
        return None


def _query_value(key, value_name: str):
    """Read a value off a handle, returning None on any failure."""
    try:
        value, _ = winreg.QueryValueEx(key, value_name)
        return value
    except OSError:
        return None


def _application_subkey_value(progid: str, value_name: str) -> str | None:
    """Best-effort read of <progid>\\Application\\<value_name>."""
    key = _open_key(rf"{CLASSES_KEY}\{progid}\Application")
    if key is None:
        return None
    try:
        value = _query_value(key, value_name)
        return value if isinstance(value, str) else None
    finally:
        winreg.CloseKey(key)


def get_userchoice_progid() -> str | None:
    """The ProgID Windows currently maps ``.pdf`` to, or None."""
    key = _open_key(USERCHOICE_KEY)
    if key is None:
        return None
    try:
        value = _query_value(key, "ProgId")
        return value if isinstance(value, str) else None
    finally:
        winreg.CloseKey(key)


def resolve_progid_owner(progid: str | None) -> str | None:
    """Return ``OPENREADER`` / ``OTHER`` / None for a ProgID (best-effort)."""
    if not is_windows() or not progid:
        return None
    if progid == INNO_PROGID:
        return OPENREADER
    app_id = _application_subkey_value(progid, "AppUserModelId")
    if app_id == AUMID:
        return OPENREADER
    if app_id:
        return OTHER
    return None


def default_app_owner() -> tuple[bool, str | None]:
    """Return ``(is_openreader_default, progid)`` for the current ``.pdf`` handler."""
    progid = get_userchoice_progid()
    if not progid:
        return (False, None)
    return (resolve_progid_owner(progid) == OPENREADER, progid)


def _find_progid_with_aumid() -> str | None:
    """Scan HKCU\\Software\\Classes for a ProgID carrying OpenReader's AUMID."""
    key = _open_key(CLASSES_KEY)
    if key is None:
        return None
    try:
        index = 0
        while True:
            try:
                subkey_name = winreg.EnumKey(key, index)
            except OSError:
                break
            index += 1
            if not subkey_name.startswith("AppX"):
                continue
            app_id = _application_subkey_value(subkey_name, "AppUserModelId")
            if app_id == AUMID:
                return subkey_name
    finally:
        winreg.CloseKey(key)
    return None


def association_registered() -> bool:
    """True when OpenReader's ``.pdf`` association exists in the registry."""
    if not is_windows():
        return False
    if _open_key(rf"{CLASSES_KEY}\{INNO_PROGID}") is not None:
        return True
    return _find_progid_with_aumid() is not None


def friendly_app_name(progid: str | None) -> str | None:
    """Best-effort display name for a ProgID, or None."""
    if not is_windows() or not progid:
        return None
    name = _application_subkey_value(progid, "FriendlyAppName")
    if name:
        return name
    key = _open_key(rf"{CLASSES_KEY}\{progid}")
    if key is None:
        return None
    try:
        value = _query_value(key, None)
        return value if isinstance(value, str) else None
    finally:
        winreg.CloseKey(key)


def open_default_apps_settings() -> bool:
    """Open the Windows Default Apps page. Never writes the default."""
    if not is_windows():
        return False
    try:
        os.startfile("ms-settings:defaultapps")  # type: ignore[attr-defined]
        return True
    except (OSError, AttributeError):
        return False
