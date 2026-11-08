"""Regression tests for the unified toolbar and window chrome."""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QLabel

import main as app_main


def _flush(window) -> None:
    window._render_timer.stop()
    window._do_render()
    QApplication.processEvents()
    QApplication.processEvents()


def _open(window, path) -> None:
    window.open_pdf(str(path))
    _flush(window)


def test_toolbar_is_a_single_compact_row(make_window):
    window = make_window()

    assert window.toolbar.objectName() == "MainToolbar"
    assert window.toolbar.isMovable() is False
    assert window.toolbar.isFloatable() is False
    assert window.toolbar.height() <= 48


def test_every_toolbar_control_exists(make_window):
    window = make_window()

    for attribute in (
        "prev_button",
        "next_button",
        "page_spin",
        "page_count_label",
        "zoom_out_button",
        "zoom_in_button",
        "zoom_label",
        "fit_button",
        "copy_button",
        "highlight_button",
        "underline_button",
        "strike_button",
        "sticky_button",
        "search_input",
        "search_prev_button",
        "search_next_button",
        "search_count_label",
        "semantic_cb",
    ):
        assert hasattr(window, attribute), attribute


def test_icons_share_one_size_and_carry_accessibility(make_window):
    window = make_window()

    for name, button in window._icon_buttons.items():
        if name == "new_tab":
            continue
        assert button.iconSize() == QSize(18, 18), name
        assert not button.icon().isNull(), name
        assert button.toolTip(), name
        assert button.accessibleName(), name

    assert window.prev_button.size() == QSize(30, 30)
    assert window.search_prev_button.size() == QSize(26, 26)
    assert window.new_tab_button.iconSize() == QSize(16, 16)


def test_theme_switch_recolors_stylesheet_and_icons(make_window):
    window = make_window()
    window.set_theme(window.THEME_LIGHT)
    light_icon = window._icon_buttons["minus"].icon().pixmap(18, 18).toImage()
    light_pixel = light_icon.pixelColor(9, 9)

    window.set_theme(window.THEME_DARK)

    assert window._dark_mode is True
    assert "Fluent dark theme" in window.styleSheet()
    dark_icon = window._icon_buttons["minus"].icon().pixmap(18, 18).toImage()
    dark_pixel = dark_icon.pixelColor(9, 9)

    assert light_pixel.lightness() < 128
    assert dark_pixel.lightness() > 128


def test_keyboard_shortcuts_are_registered(make_window):
    window = make_window()

    sequences = {shortcut.key().toString() for shortcut in window._app_shortcuts}
    expected_sequences = {
        QKeySequence(sequence).toString()
        for sequence in (
            "Ctrl+O",
            "Ctrl+S",
            "Ctrl+F",
            "Ctrl+C",
            "Page Up",
            "Page Down",
            "Ctrl+=",
            "Ctrl+-",
            "Ctrl+0",
            "Ctrl+W",
            "Ctrl+T",
        )
    }
    assert expected_sequences <= sequences


def test_navigation_buttons_update_the_indicator(make_window, make_pdf):
    pdf = make_pdf(10)
    window = make_window()
    _open(window, pdf)

    window.next_button.click()
    _flush(window)
    assert window.current_page == 1
    assert window.page_spin.value() == 2

    window.prev_button.click()
    _flush(window)
    assert window.current_page == 0
    assert window.page_spin.value() == 1

    window.page_spin.setValue(7)
    _flush(window)
    assert window.current_page == 6


def test_zoom_controls_update_the_percentage(make_window, make_pdf):
    pdf = make_pdf(3)
    window = make_window()
    _open(window, pdf)

    assert window.zoom_label.text().endswith("%")

    window.zoom_in()
    _flush(window)
    assert window.zoom_label.text() == (
        f"{int(round(window.current_render_zoom * 100))}%"
    )

    window.zoom_out()
    _flush(window)
    assert window.zoom_label.text().endswith("%")


def test_annotation_buttons_require_a_selection(make_window, make_pdf):
    pdf = make_pdf(3)
    window = make_window()
    _open(window, pdf)

    window.selected_text = ""
    window._update_controls()
    assert not window.copy_button.isEnabled()
    assert not window.highlight_button.isEnabled()

    window.selected_text = "some text"
    window._update_controls()
    assert window.copy_button.isEnabled()
    assert window.highlight_button.isEnabled()
    assert window.underline_button.isEnabled()
    assert window.strike_button.isEnabled()


def test_annotation_visibility_toggle_rerenders(make_window, make_pdf):
    pdf = make_pdf(3)
    window = make_window()
    _open(window, pdf)

    window.show_annots_action.setChecked(False)
    window._toggle_annotations_visible(False)
    _flush(window)
    assert window.show_annots_action.isChecked() is False

    window.show_annots_action.setChecked(True)
    window._toggle_annotations_visible(True)
    _flush(window)
    assert window.show_annots_action.isChecked() is True


def test_search_updates_count_and_jumps_between_pages(make_window, make_pdf):
    pdf = make_pdf(5, body="needle in this page")
    window = make_window()
    _open(window, pdf)

    window.search_input.setText("needle")
    window.search()
    QApplication.processEvents()

    assert len(window.search_results) == 5
    assert window.current_page == 0
    assert window.search_count_label.text() == "1/5"

    window.next_search_result()
    QApplication.processEvents()
    assert window.current_page == 1

    window.previous_search_result()
    QApplication.processEvents()
    assert window.current_page == 0


def test_multiple_tabs_keep_independent_documents(make_window, make_pdf):
    first = make_pdf(4, label="first")
    second = make_pdf(9, label="second")
    window = make_window()

    _open(window, first)
    _open(window, second)

    assert window.tab_bar.count() == 2
    assert window.tab_bar.isVisible()
    assert window.document.page_count == 9

    window.tab_bar.setCurrentIndex(0)
    QApplication.processEvents()
    _flush(window)

    assert window.document.page_count == 4
    assert window.page_count_label.text() == "/ 4"
    assert window.page_spin.value() == 1


def test_continuous_toggle_rebuilds_a_complete_document(make_window, make_pdf):
    pdf = make_pdf(12)
    window = make_window()
    _open(window, pdf)
    assert len(window._continuous_pages) == 12

    window._toggle_continuous_mode(False)
    _flush(window)
    assert window._continuous_mode is False
    assert window.scroll_area.widget() is window.page_label

    window._toggle_continuous_mode(True)
    _flush(window)
    assert window._continuous_mode is True
    assert len(window._continuous_pages) == 12


def test_empty_state_is_shown_before_a_document(make_window):
    window = make_window()
    assert window.scroll_area.widget() is window.empty_state_widget
    assert isinstance(window.zoom_label, QLabel)
    assert window.zoom_label.text() == "—"
