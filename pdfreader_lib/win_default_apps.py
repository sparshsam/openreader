"""Windows default-app detection and Default-apps integration for OpenReader.

OpenReader registers ``.pdf`` through two distribution channels:

- **MSIX / Microsoft Store** — Windows creates an OS-generated
  (AppX-namespaced) ProgID for the declared ``windows.fileTypeAssociation`` at
  install time. That literal ProgID string is never matched; ownership is
  resolved by reading the ``AppUserModelId`` under ``<progid>\\Application``
  and comparing it to OpenReader's Application User Model ID (AUMID).
- **Legacy Inno installer** — writes the fixed ProgID ``OpenReaderPDF`` to the
  registry (see installer/setup.iss). Because the installer is admin-elevated
  (``PrivilegesRequired=admin``), its ``HKCR`` entries land in
  ``HKLM\\Software\\Classes``.

ProgID lookups therefore read both ``HKCU\\Software\\Classes`` and
``HKLM\\Software\\Classes`` — the two physical hives that ``HKCR`` merges — so
a per-user MSIX registration and an admin Inno registration are both seen.

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


def _hives():
    """The physical hives HKCR merges: per-user first, then machine-wide."""
    return (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE)


def _open_key(path: str, root=None):
    """Open a key; root defaults to HKEY_CURRENT_USER. Returns handle or None."""
    if not is_windows():
        return None
    if root is None:
        root = winreg.HKEY_CURRENT_USER
    try:
        return winreg.OpenKey(root, path)
    except OSError:
        return None


def _query_value(key, value_name: str):
    """Read a value off a handle, returning None on any failure."""
    try:
        value, _ = winreg.QueryValueEx(key, value_name)
        return value
    except OSError:
        return None


def _classes_subkey_value(progid: str, sub: str, value_name, root=None) -> str | None:
    """Read ``<progid>\\<sub>\\<value>`` from HKCU then HKLM (merged HKCR view).

    With ``root=None`` both hives are tried; ``value_name=None`` reads the
    key's default (unnamed) value.
    """
    if not is_windows() or not progid:
        return None
    subpath = rf"{CLASSES_KEY}\{progid}" + (f"\\{sub}" if sub else "")
    hives = _hives() if root is None else (root,)
    for hive in hives:
        key = _open_key(subpath, root=hive)
        if key is None:
            continue
        try:
            value = _query_value(key, value_name)
            if isinstance(value, str) and value:
                return value
        finally:
            winreg.CloseKey(key)
    return None


def _application_subkey_value(progid: str, value_name: str, root=None) -> str | None:
    """Best-effort read of ``<progid>\\Application\\<value_name>``."""
    return _classes_subkey_value(progid, "Application", value_name, root=root)


def _shell_command(progid: str) -> str | None:
    """The ProgID's ``shell\\open\\command`` default value, or None."""
    return _classes_subkey_value(progid, r"shell\open\command", None)


def _shell_command_points_at_openreader(progid: str) -> bool:
    """True when the registered open command invokes OpenReader.exe."""
    cmd = _shell_command(progid)
    return bool(cmd) and "openreader.exe" in cmd.lower()


def _progid_key_exists(progid: str) -> bool:
    """True when the ProgID exists in HKCU or HKLM classes."""
    for hive in _hives():
        if _open_key(rf"{CLASSES_KEY}\{progid}", root=hive) is not None:
            return True
    return False


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
    """Return ``OPENREADER`` / ``OTHER`` / None for a ProgID (best-effort).

    Ownership is resolved defensively, never by a single hardcoded string:

    - the Inno Setup ProgID, a ``shell\\open\\command`` that invokes
      ``OpenReader.exe``, or an ``AppUserModelId`` equal to OpenReader's AUMID
      → ``OPENREADER``
    - any other resolvable handler (a registered command or application
      identity) → ``OTHER``
    - nothing resolvable in the registry → None (unknown / unresolved)
    """
    if not is_windows() or not progid:
        return None
    if progid == INNO_PROGID:
        return OPENREADER
    if _shell_command_points_at_openreader(progid):
        return OPENREADER
    app_id = _application_subkey_value(progid, "AppUserModelId")
    if app_id == AUMID:
        return OPENREADER
    if app_id or _shell_command(progid) or _application_subkey_value(
        progid, "FriendlyAppName"
    ):
        return OTHER
    return None


def default_app_owner() -> tuple[bool, str | None]:
    """Return ``(is_openreader_default, progid)`` for the current ``.pdf`` handler."""
    progid = get_userchoice_progid()
    if not progid:
        return (False, None)
    return (resolve_progid_owner(progid) == OPENREADER, progid)


def _find_progid_with_aumid() -> str | None:
    """Scan HKCU then HKLM classes for a ProgID carrying OpenReader's AUMID."""
    if not is_windows():
        return None
    for hive in _hives():
        key = _open_key(CLASSES_KEY, root=hive)
        if key is None:
            continue
        try:
            index = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, index)
                except OSError:
                    break
                index += 1
                # Packaged ProgIDs are AppX-namespaced or embed the package name.
                if not (
                    subkey_name.startswith("AppX")
                    or PFN.lower() in subkey_name.lower()
                ):
                    continue
                app_id = _application_subkey_value(
                    subkey_name, "AppUserModelId", root=hive
                )
                if app_id == AUMID:
                    return subkey_name
        finally:
            winreg.CloseKey(key)
    return None


def association_registered() -> bool:
    """True when OpenReader's ``.pdf`` association exists in the registry.

    Checks both HKCU and HKLM (the hives HKCR merges): an admin Inno install
    registers ``OpenReaderPDF`` under HKLM, a per-user MSIX package under HKCU.
    """
    if not is_windows():
        return False
    if _progid_key_exists(INNO_PROGID):
        return True
    return _find_progid_with_aumid() is not None


def friendly_app_name(progid: str | None) -> str | None:
    """Best-effort display name for a ProgID, or None."""
    if not is_windows() or not progid:
        return None
    name = _application_subkey_value(progid, "FriendlyAppName")
    if name:
        return name
    return _classes_subkey_value(progid, "", None)


def open_default_apps_settings() -> bool:
    """Open the Windows Default Apps page. Never writes the default."""
    if not is_windows():
        return False
    try:
        os.startfile("ms-settings:defaultapps")  # type: ignore[attr-defined]
        return True
    except (OSError, AttributeError):
        return False
