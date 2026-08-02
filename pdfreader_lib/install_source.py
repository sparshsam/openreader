"""Install-source detection for OpenReader.

Determines how the running copy of OpenReader was installed so update
behaviour can match the channel:

    SOURCE        — running from source (``python main.py``)
    STORE_MSIX    — a packaged MSIX install; by product decision all MSIX
                    installs (Microsoft Store or sideloaded) are treated as
                    Store-managed. MSIX packages always run from
                    ``C:\\Program Files\\WindowsApps\\...``
    SETUP_EXE     — the legacy Inno Setup install (defaults to Program Files)
    PORTABLE_ZIP  — a user-placed PyInstaller onedir outside Program Files

The heuristic is intentionally pragmatic: Store and sideloaded MSIX packages
are not distinguished at runtime, and a user who moved a Setup.exe install out
of Program Files may be reported as PORTABLE_ZIP. That is acceptable for update
routing — both non-MSIX channels use the same GitHub release detection.
"""

import sys
from pathlib import Path

SOURCE = "source"
STORE_MSIX = "store_msix"
SETUP_EXE = "setup_exe"
PORTABLE_ZIP = "portable_zip"

WINDOWSAPPS_MARKER = "\\windowsapps\\"


def detect_install_source() -> str:
    """Return the installation source for the running copy of OpenReader."""
    if not getattr(sys, "frozen", False):
        return SOURCE

    exe = str(Path(sys.executable).resolve()).lower()
    if WINDOWSAPPS_MARKER in exe:
        return STORE_MSIX
    if "program files" in exe:
        return SETUP_EXE
    return PORTABLE_ZIP
