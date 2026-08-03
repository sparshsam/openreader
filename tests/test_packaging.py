"""Packaging validation tests for OpenReader.

These tests parse the MSIX manifest, AppInstaller config, and MCP package
metadata directly. They deliberately do NOT import main.py (which pulls in
PySide6) — the app version is read from source via regex.

Covered:
- Frozen MSIX identity (Name / Publisher) is unchanged.
- The .pdf file-type association is declared for FullTrust activation.
- Every version source agrees with main.py.__version__.
- A version-regex regression cannot touch MinVersion/MaxVersionTested.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

APPX_NS = "http://schemas.microsoft.com/appx/manifest/foundation/windows10"
UAP_NS = "http://schemas.microsoft.com/appx/manifest/uap/windows10"
APPINSTALLER_NS = "http://schemas.microsoft.com/appx/appinstaller/2021"

IDENTITY_NAME = "SparshSam.OpenReader"
IDENTITY_PUBLISHER = "CN=E6186421-BF8A-47E0-A89C-0F513DFF91C0"
EXECUTABLE = "OpenReader.exe"
ENTRY_POINT = "Windows.FullTrustApplication"


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main_version() -> str:
    match = re.search(r'__version__ = "([^"]+)"', _read("main.py"))
    assert match, "could not find __version__ in main.py"
    return match.group(1)


def _appx_root() -> ET.Element:
    return ET.fromstring(_read("packaging/msix/AppxManifest.xml"))


def test_frozen_identity_unchanged():
    identity = _appx_root().find(f"{{{APPX_NS}}}Identity")
    assert identity is not None
    assert identity.get("Name") == IDENTITY_NAME
    assert identity.get("Publisher") == IDENTITY_PUBLISHER


def test_application_is_fulltrust_open_reader():
    application = _appx_root().find(
        f"{{{APPX_NS}}}Applications/{{{APPX_NS}}}Application"
    )
    assert application is not None
    assert application.get("Id") == "OpenReader"
    assert application.get("Executable") == EXECUTABLE
    assert application.get("EntryPoint") == ENTRY_POINT


def test_pdf_file_type_association_declared():
    ext = _appx_root().find(
        f"{{{APPX_NS}}}Applications/{{{APPX_NS}}}Application/"
        f"{{{APPX_NS}}}Extensions/{{{UAP_NS}}}Extension"
    )
    assert ext is not None
    assert ext.get("Category") == "windows.fileTypeAssociation"

    fta = ext.find(f"{{{UAP_NS}}}FileTypeAssociation")
    assert fta is not None
    assert fta.get("Name") == "openreader"

    display = fta.find(f"{{{UAP_NS}}}DisplayName")
    assert display is not None and display.text
    logo = fta.find(f"{{{UAP_NS}}}Logo")
    assert logo is not None and logo.text

    file_types = [
        t.text
        for t in fta.findall(f"{{{UAP_NS}}}SupportedFileTypes/{{{UAP_NS}}}FileType")
    ]
    assert ".pdf" in file_types


def test_manifest_version_matches_main_version():
    identity = _appx_root().find(f"{{{APPX_NS}}}Identity")
    assert identity is not None
    assert identity.get("Version") == f"{main_version()}.0"


def test_appinstaller_name_and_version():
    root = ET.fromstring(_read("packaging/msix/AppInstaller.xml"))
    main_pkg = root.find(f"{{{APPINSTALLER_NS}}}MainPackage")
    assert main_pkg is not None
    assert main_pkg.get("Name") == IDENTITY_NAME
    assert main_pkg.get("Version") == f"{main_version()}.0"


def test_mcp_package_version_matches_main_version():
    text = _read("packages/mcp-server/pyproject.toml")
    match = re.search(r'^version = "([^"]+)"', text, re.MULTILINE)
    assert match, "could not find version in packages/mcp-server/pyproject.toml"
    assert match.group(1) == main_version()


def test_version_patch_cannot_touch_min_max_version():
    # CI DOM-patches only Identity.Version. This guards against a regression
    # where a version rewrite could clobber MinVersion/MaxVersionTested.
    dep = _appx_root().find(
        f"{{{APPX_NS}}}Dependencies/{{{APPX_NS}}}TargetDeviceFamily"
    )
    assert dep is not None
    assert dep.get("MinVersion") == "10.0.17763.0"
    assert dep.get("MaxVersionTested") == "10.0.22621.0"
