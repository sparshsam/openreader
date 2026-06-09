"""Self-update service for PDFReader by Sparsh.

Encapsulates the full update lifecycle — checking for releases on GitHub,
downloading platform-specific assets, and applying the update via platform-
specific batch/shell scripts.

This is a ``QObject`` that composes into ``PdfReaderWindow``.  It owns its
own ``QNetworkAccessManager`` instances and emits results back to the
window via method calls on a *host* reference.
"""

import json
import os.path
import platform
import re
import subprocess  # nosec B404 — needed for self-update mechanism
import sys
import tempfile
import zipfile
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QMessageBox, QProgressDialog
from PySide6.QtCore import Qt


# ── constants ──────────────────────────────────────────────────────────

GITHUB_REPO = "sparshsam/pdfreader-by-sparsh"
WINDOWS_UPDATE_ASSET = "PDFReader-by-Sparsh-Windows.zip"
MACOS_APPLE_SILICON_UPDATE_ASSET = "PDFReader-by-Sparsh-macOS-Apple-Silicon.zip"
MACOS_INTEL_UPDATE_ASSET = "PDFReader-by-Sparsh-macOS-Intel.zip"


# ── version parsing ────────────────────────────────────────────────────

def parse_version(tag: str) -> tuple[int, int, int] | None:
    """Extract ``(major, minor, patch)`` from a version tag string."""
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", tag)
    if not match:
        return None
    return tuple(int(x) for x in match.groups())


# ── helper helpers ─────────────────────────────────────────────────────

def is_packaged() -> bool:
    """Return ``True`` if running from a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def updater_temp_dir() -> Path:
    """Create and return a temp directory for update downloads/logs."""
    temp_dir = Path(tempfile.gettempdir()) / "PDFReader-Updates"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def updater_log_path() -> Path:
    """Path to the updater debug log."""
    return updater_temp_dir() / "updater-debug.log"


def log_update(message: str) -> None:
    """Append *message* to the updater debug log (silently ignore errors)."""
    try:
        with open(updater_log_path(), "a", encoding="utf-8") as f:
            f.write(f"{message}\n")
    except OSError:
        pass


def select_update_apply_method(system: str, asset_name: str, dest: Path
                               ) -> tuple[str | None, str]:
    """Determine how to apply an update for *system* and *asset_name*.

    Returns ``(method_name, diagnostic)`` where *method_name* is ``None``
    if the combination is unsupported.
    """
    suffix = dest.suffix.lower()
    if system == "Windows" and asset_name == WINDOWS_UPDATE_ASSET and suffix == ".zip":
        return "windows_zip", ""
    if system == "Darwin" and suffix == ".zip":
        return "macos_zip", ""
    diagnostic = (
        "Unsupported update package.\n\n"
        f"System: {system}\n"
        f"Asset: {asset_name or '<missing>'}\n"
        f"Path: {dest}\n"
        f"Suffix: {suffix or '<missing>'}"
    )
    return None, diagnostic


def validate_download_metadata(asset_name: str | None, latest_tag: str | None) -> str:
    """Return an error message if metadata is missing, otherwise ``\"\"``."""
    if not asset_name:
        return "Download metadata missing. The updater could not determine the release asset name."
    if not latest_tag:
        return "Download metadata missing. The updater could not determine the release tag."
    return ""


# ── updater class ──────────────────────────────────────────────────────

class PdfUpdater(QObject):
    """Self-update service that composes into ``PdfReaderWindow``."""

    def __init__(self, host, parent=None):
        super().__init__(parent)
        self._host = host          # PdfReaderWindow — for UI callbacks
        self._version: str = ""    # set post-init

        # Network managers
        self._update_nam = QNetworkAccessManager(self)
        self._update_nam.finished.connect(self._on_update_check_reply)
        self._download_nam = QNetworkAccessManager(self)
        self._download_nam.finished.connect(self._on_download_finished)

        # Download state
        self._update_progress: QProgressDialog | None = None
        self._update_latest_tag: str | None = None
        self._update_asset_name: str | None = None
        self._update_download_path: Path | None = None

    # ── public API ─────────────────────────────────────────────────

    def set_version(self, version: str) -> None:
        self._version = version

    @property
    def is_downloading(self) -> bool:
        return self._update_progress is not None

    def check_for_updates(self, update_action) -> None:
        """Query GitHub releases for the latest version."""
        if self._update_progress is not None:
            return
        update_action.setEnabled(False)
        self._host.statusBar().showMessage("Checking for updates...")
        url = QUrl(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.UserAgentHeader, "PDFReader-by-Sparsh/1.0")
        request.setTransferTimeout(15000)
        self._update_nam.get(request)

    def cancel_download(self) -> None:
        """Cancel an in-progress download."""
        self._download_nam.finished.disconnect(self._on_download_finished)
        self._download_nam = QNetworkAccessManager(self)
        self._download_nam.finished.connect(self._on_download_finished)
        self._update_progress = None
        self._update_latest_tag = None
        self._update_asset_name = None
        self._host.update_action.setEnabled(True)
        self._host.statusBar().showMessage("Download cancelled", 3000)

    # ── internal slots ─────────────────────────────────────────────

    def _on_update_check_reply(self, reply: QNetworkReply) -> None:
        self._host.update_action.setEnabled(True)
        if reply.error() != QNetworkReply.NoError:
            self._host.statusBar().showMessage(
                "Could not check for updates — check your internet connection", 5000
            )
            reply.deleteLater()
            return

        try:
            data = json.loads(bytes(reply.readAll()).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._host.statusBar().showMessage(
                "Update check failed — unexpected response", 5000
            )
            reply.deleteLater()
            return
        finally:
            reply.deleteLater()

        latest_tag = data.get("tag_name", "")
        latest_version = parse_version(latest_tag)
        current_version = parse_version(self._version)

        if latest_version is None or current_version is None:
            QMessageBox.information(
                self._host,
                "Update Check",
                f"Current version: {self._version}\n"
                f"Latest release: {latest_tag}\n\n"
                "Could not compare versions.",
            )
            return

        assets = data.get("assets", [])
        asset_url, asset_name = self._get_platform_asset(assets)

        if latest_version <= current_version:
            QMessageBox.information(
                self._host,
                "Up to Date",
                f"You're running {self._version}, which is the latest version.",
            )
            self._host.statusBar().showMessage(
                f"PDFReader is up to date (v{self._version})", 5000
            )
            return

        release_url = data.get(
            "html_url", f"https://github.com/{GITHUB_REPO}/releases"
        )
        release_notes = (data.get("body") or "")[:500]

        msg = (
            f"<h3>Update Available</h3>"
            f"<p><b>v{'.'.join(str(x) for x in current_version)}</b> \u2192 {latest_tag}</p>"
        )
        if release_notes:
            msg += f"<hr><pre style='white-space:pre-wrap'>{release_notes}</pre>"

        btn = QMessageBox(self._host)
        btn.setWindowTitle("Update Available")
        btn.setTextFormat(Qt.RichText)
        btn.setText(msg)

        if asset_url and asset_name:
            download_button = btn.addButton(
                "Download & Install", QMessageBox.AcceptRole
            )
        skip_button = btn.addButton("Skip This Version", QMessageBox.RejectRole)
        _ = btn.addButton("Later", QMessageBox.DestructiveRole)

        btn.exec()

        if btn.clickedButton() == skip_button:
            self._host.statusBar().showMessage("Update skipped", 3000)
            return

        if asset_url and btn.clickedButton() == download_button:
            self._start_download(asset_url, asset_name, latest_tag)
        elif not asset_url:
            import webbrowser
            webbrowser.open(release_url)
            self._host.statusBar().showMessage(
                "No installer for your platform. Opening releases page.", 5000
            )

    def _get_platform_asset(self, assets: list[dict]) -> tuple[str | None, str | None]:
        assets_by_name = {a.get("name", ""): a for a in assets}
        system = platform.system()
        if system == "Windows":
            asset = assets_by_name.get(WINDOWS_UPDATE_ASSET)
            if asset:
                return asset["browser_download_url"], asset["name"]
        elif system == "Darwin":
            is_arm = platform.machine() in ("arm64", "aarch64")
            expected_name = (
                MACOS_APPLE_SILICON_UPDATE_ASSET
                if is_arm
                else MACOS_INTEL_UPDATE_ASSET
            )
            asset = assets_by_name.get(expected_name)
            if asset:
                return asset["browser_download_url"], asset["name"]
        return None, None

    # ── download lifecycle ─────────────────────────────────────────

    def _start_download(self, asset_url: str, asset_name: str, latest_tag: str) -> None:
        system = platform.system()
        log_update(f"current_version={self._version}")
        log_update(f"latest_tag={latest_tag}")
        log_update(f"selected_asset_name={asset_name}")
        log_update(f"asset_url={asset_url}")
        log_update(f"detected_os={system}")

        validation_errors = []
        if not asset_url:
            validation_errors.append("missing asset URL")
        if not asset_name:
            validation_errors.append("missing asset name")
        if not latest_tag:
            validation_errors.append("missing release tag")
        if system == "Windows" and asset_name != WINDOWS_UPDATE_ASSET:
            validation_errors.append(
                f"Windows updater expected {WINDOWS_UPDATE_ASSET}, "
                f"got {asset_name or '<missing>'}"
            )
        if validation_errors:
            message = "Cannot start update download:\n\n" + "\n".join(validation_errors)
            log_update(f"failure={message}")
            QMessageBox.critical(self._host, "Update Error", message)
            return

        self._update_latest_tag = latest_tag
        self._update_asset_name = asset_name
        self._update_download_path = None

        self._update_progress = QProgressDialog(
            f"Downloading {asset_name}\u2026", "Cancel", 0, 0, self._host
        )
        self._update_progress.setWindowTitle("Downloading Update")
        self._update_progress.setWindowModality(Qt.WindowModal)
        self._update_progress.setMinimumDuration(0)
        self._update_progress.setValue(0)
        self._update_progress.canceled.connect(self.cancel_download)
        self._update_progress.show()

        self._host.update_action.setEnabled(False)
        self._host.statusBar().showMessage(f"Downloading {asset_name}\u2026")

        request = QNetworkRequest(QUrl(asset_url))
        request.setHeader(QNetworkRequest.UserAgentHeader, "PDFReader-by-Sparsh/1.0")
        request.setTransferTimeout(300000)
        reply = self._download_nam.get(request)
        reply.setProperty("asset_name", asset_name)
        reply.setProperty("latest_tag", latest_tag)
        reply.downloadProgress.connect(self._on_download_progress)

    def _on_download_progress(self, received: int, total: int) -> None:
        if self._update_progress is None:
            return
        if total > 0:
            self._update_progress.setMaximum(int(total))
            self._update_progress.setValue(int(received))
            mb_rec = received / (1024 * 1024)
            mb_tot = total / (1024 * 1024)
            self._update_progress.setLabelText(
                f"Downloading update\u2026 {mb_rec:.1f} / {mb_tot:.1f} MB"
            )
        else:
            self._update_progress.setMaximum(0)
            self._update_progress.setValue(0)

    def _on_download_finished(self, reply: QNetworkReply) -> None:
        self._host.update_action.setEnabled(True)
        if self._update_progress is not None:
            self._update_progress.close()
            self._update_progress = None

        asset_name = reply.property("asset_name")
        latest_tag = reply.property("latest_tag")
        metadata_error = validate_download_metadata(asset_name, latest_tag)
        if metadata_error:
            log_update("failure=download metadata missing")
            QMessageBox.critical(self._host, "Update Error", metadata_error)
            reply.deleteLater()
            return

        if reply.error() != QNetworkReply.NoError:
            log_update(f"failure=download failed: {reply.errorString()}")
            QMessageBox.critical(
                self._host,
                "Download Failed",
                f"Could not download the update:\n{reply.errorString()}",
            )
            reply.deleteLater()
            return

        try:
            temp_dir = updater_temp_dir()
            dest = temp_dir / asset_name
            log_update(f"download_destination={dest}")
            data = reply.readAll()
            with open(dest, "wb") as f:
                f.write(bytes(data))
            self._update_download_path = dest
        except Exception as exc:
            log_update(f"failure=could not save download: {exc}")
            QMessageBox.critical(
                self._host,
                "Download Failed",
                f"Could not save the downloaded file:\n{exc}",
            )
            reply.deleteLater()
            return
        finally:
            reply.deleteLater()

        self._apply_update(dest, latest_tag, asset_name)

    # ── apply update ───────────────────────────────────────────────

    def _apply_update(self, dest: Path, latest_tag: str, asset_name: str) -> None:
        if dest is None or not dest.exists():
            log_update("failure=update file not found")
            QMessageBox.critical(self._host, "Update Error", "Update file not found.")
            return

        system = platform.system()
        log_update(f"detected_os={system}")
        method, diagnostic = select_update_apply_method(system, asset_name, dest)
        log_update(f"selected_apply_method={method or 'unsupported'}")

        if method == "windows_zip":
            self._apply_update_windows_zip(dest, latest_tag)
        elif method == "macos_zip":
            # macOS method expected to exist; fallback handled below
            try:
                self._apply_update_macos(dest, latest_tag)
            except AttributeError:
                log_update("failure=macos updater not implemented")
                QMessageBox.critical(
                    self._host, "Update Error",
                    "macOS updater is not yet available in this build.",
                )
        else:
            log_update(f"failure={diagnostic}")
            QMessageBox.critical(self._host, "Update Error", diagnostic)

    def _apply_update_windows_zip(self, dest: Path, tag: str) -> None:
        """Replace the running app via ZIP extract + batch updater (onedir mode)."""
        current_exe = Path(sys.executable)
        app_dir = current_exe.parent
        if not app_dir.exists():
            log_update("failure=could not locate app directory")
            QMessageBox.critical(
                self._host, "Update Error", "Could not locate the app directory."
            )
            return

        extract_dir = dest.parent / f"extracted_{tag}"
        log_update(f"extract_directory={extract_dir}")
        try:
            if extract_dir.exists():
                import shutil
                shutil.rmtree(extract_dir)
            with zipfile.ZipFile(str(dest), "r") as zf:
                zf.extractall(str(extract_dir))
        except Exception as exc:
            log_update(f"failure=could not extract update: {exc}")
            QMessageBox.critical(
                self._host, "Update Error",
                f"Could not extract the update.\n\n{exc}",
            )
            return

        log_path = updater_log_path()
        bat_path = app_dir / f"_update_{tag}.bat"
        log_update(f"batch_script_path={bat_path}")
        bat_content = (
            "@echo off\n"
            "title=PDFReader Updater\n"
            "setlocal enabledelayedexpansion\n"
            f'set LOG="{log_path}"\n'
            "echo [%date% %time%] Starting update... >> \"%LOG%\"\n"
            "\n"
            ":wait\n"
            f'tasklist /FI "PID eq {os.getpid()}" 2>>"%LOG%" | find "{os.getpid()}" >nul\n'
            "if not errorlevel 1 (\n"
            "    timeout /t 1 /nobreak >nul\n"
            "    goto wait\n"
            ")\n"
            "\n"
            "echo [%date% %time%] Process exited, waiting 2s... >> \"%LOG%\"\n"
            "timeout /t 2 /nobreak >nul\n"
            "\n"
            "echo [%date% %time%] Copying _internal folder... >> \"%LOG%\"\n"
            "set RETRY=0\n"
            ":retry_xcopy\n"
            f'xcopy /E /I /Y "{extract_dir}\\_internal" "{app_dir}\\_internal" >>"%LOG%" 2>&1\n'
            "if errorlevel 1 (\n"
            "    set /a RETRY+=1\n"
            "    if !RETRY! lss 3 (\n"
            "        timeout /t 1 /nobreak >nul\n"
            "        goto retry_xcopy\n"
            "    )\n"
            "    echo [%date% %time%] ERROR: xcopy failed after 3 retries >> \"%LOG%\"\n"
            "    goto fail\n"
            ")\n"
            "\n"
            "echo [%date% %time%] Copying EXE... >> \"%LOG%\"\n"
            "set RETRY=0\n"
            ":retry_copy\n"
            f'copy /Y /V "{extract_dir}\\PDFReader by Sparsh.exe" "{current_exe}" >>"%LOG%" 2>&1\n'
            "if errorlevel 1 (\n"
            "    set /a RETRY+=1\n"
            "    if !RETRY! lss 3 (\n"
            "        timeout /t 1 /nobreak >nul\n"
            "        goto retry_copy\n"
            "    )\n"
            "    echo [%date% %time%] ERROR: copy failed after 3 retries >> \"%LOG%\"\n"
            "    goto fail\n"
            ")\n"
            "\n"
            "echo [%date% %time%] Unblocking EXE... >> \"%LOG%\"\n"
            f'powershell -Command "Unblock-File -Path \'{current_exe}\'" >>"%LOG%" 2>&1\n'
            "\n"
            "echo [%date% %time%] Launching new version... >> \"%LOG%\"\n"
            f'start "" "{current_exe}"\n'
            "\n"
            "echo [%date% %time%] Update successful, cleaning up... >> \"%LOG%\"\n"
            f'rmdir /S /Q "{extract_dir}" >>"%LOG%" 2>&1\n'
            f'del "{dest}" >>"%LOG%" 2>&1\n'
            'del "%~f0" >nul 2>&1\n'
            "exit /b 0\n"
            "\n"
            ":fail\n"
            "echo [%date% %time%] UPDATE FAILED >> \"%LOG%\"\n"
            f'start "" notepad "{log_path}"\n'
            "pause\n"
            "exit /b 1\n"
        )

        try:
            with open(bat_path, "w") as f:
                f.write(bat_content)
            subprocess.Popen(  # nosec
                ["cmd.exe", "/c", str(bat_path)],
                creationflags=0x08000000,
            )
            log_update("success=launched Windows ZIP updater")
        except Exception as exc:
            log_update(f"failure=could not launch update script: {exc}")
            QMessageBox.critical(
                self._host, "Update Error",
                f"Could not launch the update script.\n\n{exc}",
            )
            return

        QMessageBox.information(
            self._host,
            "Update Starting",
            "PDFReader will now close and update itself."
            " It will reopen automatically in a moment.",
        )
        QTimer.singleShot(500, self._host.close)
