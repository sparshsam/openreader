"""Install-source detection for OpenReader.

Determines how the running copy of OpenReader was installed so update
behaviour can match the channel:

    SOURCE        — running from source (``python main.py``)
    STORE_MSIX    — a packaged MSIX install; by product decision all MSIX
                    installs (Microsoft Store or sideloaded) are treated as
                    Store-managed
    SETUP_EXE     — the legacy Inno Setup install (defaults to Program Files)
    PORTABLE_ZIP  — a user-placed PyInstaller onedir outside Program Files

Packaged execution is detected through the Windows package API
(``GetCurrentPackageFamilyName``) — the process-level AppX identity — rather
than by assuming a filename. The ``C:\\Program Files\\WindowsApps\\`` path is
kept only as a fallback for environments where the API is unavailable.
Store and sideloaded MSIX packages are not distinguished at runtime; both are
reported as STORE_MSIX.
"""

import ctypes
import sys
from pathlib import Path

SOURCE = "source"
STORE_MSIX = "store_msix"
SETUP_EXE = "setup_exe"
PORTABLE_ZIP = "portable_zip"

PFN = "SparshSam.OpenReader_yh0byntbzd2qw"

WINDOWSAPPS_MARKER = "\\windowsapps\\"


def _package_family_name() -> str | None:
    """Return the current process's AppX package family name, or None.

    ``GetCurrentPackageFamilyName`` returns ``ERROR_INSUFFICIENT_BUFFER`` (122)
    on the sizing call and ``APPMODEL_ERROR_NO_PACKAGE`` (15700) when the
    process is not running from a package — both handled as "no package".
    """
    if not sys.platform.startswith("win"):
        return None
    try:
        get_pfn = ctypes.windll.kernel32.GetCurrentPackageFamilyName
        length = ctypes.c_uint32(0)
        # First call sizes the buffer; returns ERROR_INSUFFICIENT_BUFFER (122).
        hr = get_pfn(ctypes.byref(length), None)
        if hr != 122 or length.value == 0:
            return None
        buf = ctypes.create_unicode_buffer(length.value)
        if get_pfn(ctypes.byref(length), buf) == 0:
            return buf.value
    except (OSError, AttributeError):
        return None
    return None


def detect_install_source() -> str:
    """Return the installation source for the running copy of OpenReader."""
    if not getattr(sys, "frozen", False):
        return SOURCE

    # Reliable signal: the process carries an AppX package identity.
    if _package_family_name() is not None:
        return STORE_MSIX

    # Fallback: MSIX packages always run from the WindowsApps store.
    exe = str(Path(sys.executable).resolve()).lower()
    if WINDOWSAPPS_MARKER in exe:
        return STORE_MSIX
    if "program files" in exe:
        return SETUP_EXE
    return PORTABLE_ZIP
