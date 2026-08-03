"""Tests for pdfreader_lib.install_source (channel-aware update source)."""

import sys

from pdfreader_lib import install_source

STORE_EXE = (
    r"C:\Program Files\WindowsApps\SparshSam.OpenReader_1.2.7.0_x64__yh0byntbzd2qw"
    r"\OpenReader.exe"
)


def _patch_runtime(monkeypatch, frozen: bool, executable: str, pfn=None):
    if frozen:
        monkeypatch.setattr(sys, "frozen", True, raising=False)
    else:
        monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(sys, "executable", executable)
    monkeypatch.setattr(install_source, "_package_family_name", lambda: pfn)


def test_source_when_not_frozen(monkeypatch):
    _patch_runtime(monkeypatch, False, "/usr/bin/python3", pfn=None)
    assert install_source.detect_install_source() == install_source.SOURCE


def test_msix_detected_via_package_api(monkeypatch):
    """Packaged execution is signalled by the Windows package API, not the path."""
    _patch_runtime(
        monkeypatch,
        True,
        r"C:\Packages\OpenReader.exe",  # not WindowsApps — the API is the signal
        pfn=install_source.PFN,
    )
    assert install_source.detect_install_source() == install_source.STORE_MSIX


def test_msix_windowsapps_path_fallback(monkeypatch):
    """The WindowsApps path remains a fallback when the API is unavailable."""
    _patch_runtime(monkeypatch, True, STORE_EXE, pfn=None)
    assert install_source.detect_install_source() == install_source.STORE_MSIX


def test_msix_marker_matches_differing_case(monkeypatch):
    _patch_runtime(
        monkeypatch,
        True,
        r"C:\Program Files\WindowsApps\SomePkg\OpenReader.exe",
        pfn=None,
    )
    assert install_source.detect_install_source() == install_source.STORE_MSIX


def test_program_files_is_setup_exe(monkeypatch):
    _patch_runtime(
        monkeypatch, True, r"C:\Program Files\OpenReader\OpenReader.exe", pfn=None
    )
    assert install_source.detect_install_source() == install_source.SETUP_EXE


def test_elsewhere_is_portable_zip(monkeypatch):
    _patch_runtime(monkeypatch, True, r"D:\Tools\OpenReader\OpenReader.exe", pfn=None)
    assert install_source.detect_install_source() == install_source.PORTABLE_ZIP


def test_all_channels_distinct():
    channels = {
        install_source.SOURCE,
        install_source.STORE_MSIX,
        install_source.SETUP_EXE,
        install_source.PORTABLE_ZIP,
    }
    assert len(channels) == 4
