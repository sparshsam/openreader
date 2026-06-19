#!/usr/bin/env python3
"""Capture OpenReader v1.2.2 screenshots in offscreen mode (1920x1080).

Usage:
    source .venv-test-screenshots/bin/activate
    QT_QPA_PLATFORM=offscreen python tools/capture_screenshots.py

Output: assets/screenshots/v1.2.2/
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEventLoop, QTimer as QLoopTimer

OUT_DIR = ROOT / "assets" / "screenshots" / "v1.2.2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

app = QApplication(sys.argv)


def shot(widget, filename, delay_ms=600):
    """Capture a widget after a short delay for rendering."""
    result = []

    def capture():
        pixmap = widget.grab()
        path = OUT_DIR / filename
        pixmap.save(str(path))
        result.append(path)
        print(f"  Captured: {path} ({pixmap.width()}x{pixmap.height()})")

    QLoopTimer.singleShot(delay_ms, capture)
    loop = QEventLoop()
    QLoopTimer.singleShot(delay_ms + 200, loop.quit)
    loop.exec()
    return result[0] if result else None


def main():
    from main import PdfReaderWindow

    print("Creating window...")
    window = PdfReaderWindow()
    window.show()
    window.resize(1920, 1080)
    app.processEvents()

    # 1. Empty state — fresh launch, no PDFs open
    print("\n1. Empty state...")
    shot(window, "empty-state.png", delay_ms=800)

    # 2. Open a test PDF
    test_pdf = str(ROOT / "screenshots_test.pdf")
    if os.path.exists(test_pdf):
        print(f"\n2. Opening test PDF...")
        window.open_pdf(test_pdf)
        app.processEvents()
        shot(window, "reader-main.png", delay_ms=1000)

        # 3. Dark mode
        print("\n3. Dark mode...")
        window.set_theme(window.THEME_DARK)
        app.processEvents()
        shot(window, "dark-mode.png", delay_ms=800)

        # Reset to light
        print("\n4. Light mode for tools...")
        window.set_theme(window.THEME_LIGHT)
        app.processEvents()

    # 5. Tools view
    print("\n5. Tools view...")
    # Try to open the merge/split dialog for a more interesting capture
    try:
        window._open_compare_dialog()
        app.processEvents()
    except Exception:
        pass  # nosec B110 — expected failure if compare dialog unavailable
    shot(window, "merge-split.png", delay_ms=800)

    # 6. About dialog — use the real about method
    print("\n6. About dialog...")
    try:
        window._show_about()
        app.processEvents()
        about_widgets = [w for w in app.topLevelWidgets() if w != window and w.isVisible()]
        if about_widgets:
            shot(about_widgets[0], "about.png", delay_ms=800)
            about_widgets[0].close()
        else:
            print("  No about dialog found, capturing fallback...")
            shot(window, "about.png")
    except Exception as e:
        print(f"  About dialog failed: {e}")
        shot(window, "about.png")

    print(f"\nAll screenshots saved to: {OUT_DIR}")
    for p in sorted(OUT_DIR.glob("*.png")):
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
