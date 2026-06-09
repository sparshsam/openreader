"""Theme / dark-mode system.

Provides the Catppuccin-based dark stylesheet and the ``ThemeManager``
helper that decouples theme logic from the main window.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget


# ── constants ──────────────────────────────────────────────────────────

THEME_AUTO = 0
THEME_LIGHT = 1
THEME_DARK = 2

# ── dark stylesheet ────────────────────────────────────────────────────

DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QMainWindow::separator {
    background-color: #313244;
}
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    padding: 4px 12px;
    border-radius: 4px;
    min-height: 22px;
}
QPushButton:hover {
    background-color: #45475a;
}
QPushButton:pressed {
    background-color: #585b70;
}
QPushButton:checked {
    background-color: #a6e3a1;
    color: #1e1e2e;
    border-color: #a6e3a1;
}
QPushButton:disabled {
    background-color: #313244;
    color: #585b70;
    border-color: #313244;
}
QLineEdit {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    padding: 4px 6px;
    border-radius: 4px;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
}
QLineEdit:focus {
    border-color: #89b4fa;
}
QSpinBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    padding: 4px;
    border-radius: 4px;
}
QSpinBox:focus {
    border-color: #89b4fa;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #45475a;
    border: none;
    width: 18px;
}
QLabel {
    color: #cdd6f4;
    background-color: transparent;
}
QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #313244;
}
QScrollArea {
    background-color: #1e1e2e;
    border: none;
}
QToolBar {
    background-color: #181825;
    border: none;
    border-bottom: 1px solid #313244;
    spacing: 4px;
    padding: 2px 4px;
}
QToolBar QToolButton {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 4px 6px;
    color: #cdd6f4;
}
QToolBar QToolButton:hover {
    background-color: #313244;
}
QToolBar QToolButton:pressed {
    background-color: #45475a;
}
QToolBar QToolButton:disabled {
    color: #585b70;
}
QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    padding: 6px 18px;
    border: none;
    border-right: 1px solid #313244;
    min-height: 24px;
}
QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #89b4fa;
    border-bottom: 2px solid #89b4fa;
}
QTabBar::tab:hover:!selected {
    background-color: #313244;
    color: #cdd6f4;
}
QTabBar::close-button {
    image: none;
    background-color: transparent;
    border: none;
    padding: 2px;
    margin: 2px;
    color: #a6adc8;
}
QTabBar::close-button:hover {
    background-color: #f38ba8;
    border-radius: 3px;
    color: #1e1e2e;
}
QMenuBar {
    background-color: #181825;
    color: #cdd6f4;
    border-bottom: 1px solid #313244;
    padding: 2px;
}
QMenuBar::item {
    padding: 4px 10px;
    background-color: transparent;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background-color: #313244;
}
QMenu {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #45475a;
    padding: 4px;
}
QMenu::item {
    padding: 6px 28px 6px 20px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #45475a;
}
QMenu::item:disabled {
    color: #585b70;
}
QMenu::separator {
    height: 1px;
    background-color: #313244;
    margin: 4px 8px;
}
QProgressDialog {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #45475a;
}
QMessageBox {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QMessageBox QLabel {
    color: #cdd6f4;
}
QMessageBox QPushButton {
    min-width: 80px;
}
QInputDialog {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QScrollBar:horizontal {
    background-color: #181825;
    height: 10px;
    border: none;
}
QScrollBar::handle:horizontal {
    background-color: #45475a;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #585b70;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QScrollBar:vertical {
    background-color: #181825;
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""


# ── manager ────────────────────────────────────────────────────────────

class ThemeManager:
    """Encapsulates theme selection logic.

    ``theme`` is one of ``THEME_AUTO`` / ``THEME_LIGHT`` / ``THEME_DARK``.
    Call ``apply(widget)`` to push the stylesheet onto the target widget.
    """

    def __init__(self, theme: int = THEME_AUTO):
        self._theme = theme

    @property
    def theme(self) -> int:
        return self._theme

    @theme.setter
    def theme(self, value: int) -> None:
        self._theme = value

    def is_dark(self) -> bool:
        """Return ``True`` if the effective mode is dark."""
        if self._theme == THEME_LIGHT:
            return False
        if self._theme == THEME_DARK:
            return True
        # Auto: query system
        scheme = QApplication.styleHints().colorScheme()
        return scheme == Qt.ColorScheme.Dark

    def apply(self, widget: QWidget) -> None:
        """Push the correct stylesheet (dark or blank) onto *widget*."""
        if self.is_dark():
            widget.setStyleSheet(DARK_STYLESHEET)
        else:
            widget.setStyleSheet("")

    def on_system_theme_change(self) -> None:
        """Call when the OS colour-scheme changes (only relevant in AUTO)."""
        pass  # The window's slot should reinterpret via is_dark + apply
