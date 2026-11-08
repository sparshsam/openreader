"""Regression tests for continuous scrolling.

These tests pin the behaviours that broke in v1.2.7: the continuous view
rendered only a sliding window around the current page, so the scroll range
was limited to that window and navigating with Next/Previous rebuilt the
layout and discarded every page outside it.

The tests run offscreen and do not need a display.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication


def _flush(window) -> None:
    """Run a render synchronously, bypassing the debounce timer."""
    window._render_timer.stop()
    window._do_render()
    QApplication.processEvents()
    QApplication.processEvents()


def _settle(window, attempts: int = 6) -> None:
    """Render until the viewport and scroll range stop changing.

    Fit-to-window zoom depends on whether scrollbars are present, so the very
    first render can legitimately trigger one rebuild.
    """
    previous = None
    for _ in range(attempts):
        _flush(window)
        if window.document is None:
            return
        viewport = window.scroll_area.viewport()
        state = (
            viewport.width(),
            viewport.height(),
            window.scroll_area.verticalScrollBar().maximum(),
            len(window._continuous_pages),
        )
        if state == previous:
            return
        previous = state


def _open(window, path) -> None:
    window.open_pdf(str(path))
    _settle(window)


def _open_rendered_page_count(window) -> int:
    """Pages with an actual pixmap (lazy rendering may keep fewer)."""
    return len(getattr(window, "_continuous_rendered", ()))


# ---------------------------------------------------------------------------
# Continuous scrolling
# ---------------------------------------------------------------------------


def test_every_page_exists_in_the_scrollable_document(make_window, make_pdf):
    pdf = make_pdf(76)
    window = make_window()

    _open(window, pdf)

    assert window.document.page_count == 76
    assert len(window._continuous_pages) == 76


def test_scrollbar_reaches_the_last_page(make_window, make_pdf):
    pdf = make_pdf(76)
    window = make_window()
    _open(window, pdf)

    scrollbar = window.scroll_area.verticalScrollBar()
    scrollbar.setValue(scrollbar.maximum())
    QApplication.processEvents()

    assert scrollbar.maximum() > 0
    assert window.current_page == 75
    assert window.page_spin.value() == 76


def test_scrolling_updates_the_page_indicator(make_window, make_pdf):
    pdf = make_pdf(76)
    window = make_window()
    _open(window, pdf)

    target = window._continuous_pages[29]
    window.scroll_area.verticalScrollBar().setValue(target.y())
    QApplication.processEvents()

    assert window.current_page == 29
    assert window.page_spin.value() == 30


def test_navigation_does_not_discard_pages(make_window, make_pdf):
    pdf = make_pdf(76)
    window = make_window()
    _open(window, pdf)

    first_page_widget = window._continuous_pages[0]
    for _ in range(6):
        window.next_page()
        _flush(window)

    assert window.current_page == 6
    assert len(window._continuous_pages) == 76
    # The layout must be reused, not rebuilt, so page 1 stays reachable.
    assert window._continuous_pages[0] is first_page_widget

    window.jump_to_page(1)
    _flush(window)

    assert window.current_page == 0
    assert (
        window.scroll_area.verticalScrollBar().value()
        <= window._continuous_pages[0].y()
    )
    assert len(window._continuous_pages) == 76


def test_jump_scrolls_directly_to_the_requested_page(make_window, make_pdf):
    pdf = make_pdf(76)
    window = make_window()
    _open(window, pdf)

    window.jump_to_page(50)
    _flush(window)

    scrollbar = window.scroll_area.verticalScrollBar()
    page_49 = window._continuous_pages[49]
    top = scrollbar.value()

    assert window.current_page == 49
    assert window.page_spin.value() == 50
    assert page_49.y() <= top + 40
    assert page_49.y() + page_49.height() > top
    assert len(window._continuous_pages) == 76


def test_scroll_range_survives_zoom_changes(make_window, make_pdf):
    pdf = make_pdf(76)
    window = make_window()
    _open(window, pdf)

    window.jump_to_page(40)
    _flush(window)
    before = window.current_page

    window.zoom_in()
    _flush(window)

    assert window.current_page == before
    assert len(window._continuous_pages) == 76
    scrollbar = window.scroll_area.verticalScrollBar()
    scrollbar.setValue(scrollbar.maximum())
    QApplication.processEvents()
    assert window.current_page == 75


def test_rendering_is_virtualized(make_window, make_pdf):
    pdf = make_pdf(200)
    window = make_window()

    _open(window, pdf)

    assert len(window._continuous_pages) == 200
    # Only the viewport plus a small overscan may hold pixmaps.
    assert _open_rendered_page_count(window) <= 12


def test_continuous_render_does_not_raise(make_window, make_pdf):
    """Regression: v1.2.7 raised NameError on every continuous render."""
    pdf = make_pdf(3)
    window = make_window()

    window.open_pdf(str(pdf))
    window._render_timer.stop()
    window._do_render()  # must not raise


def test_small_documents_still_scroll_end_to_end(make_window, make_pdf):
    pdf = make_pdf(2)
    window = make_window()
    _open(window, pdf)

    assert len(window._continuous_pages) == 2
    window.next_page()
    _flush(window)
    assert window.current_page == 1
    assert window.page_spin.value() == 2
    window.previous_page()
    _flush(window)
    assert window.current_page == 0
