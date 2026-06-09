"""Per-tab state container.

``TabData`` holds all document- and view-related state for a single tab in
the PDF reader.  Freshly-created tabs use the defaults shown below; the
main window swaps these in and out on tab switch.

This module has *no* Qt or UI dependency — it is a pure data definition.
"""

from collections import OrderedDict
from dataclasses import dataclass, field

import fitz


@dataclass
class TabData:
    """State for one PDF-viewer tab."""

    name: str
    path: str | None = None
    document: fitz.Document | None = None
    current_page: int = 0
    zoom: float = 1.25
    fit_to_window: bool = True
    search_text: str = ""
    search_results: list = field(default_factory=list)
    current_result_index: int = -1
    current_render_zoom: float = 1.0
    selected_text: str = ""
    selected_rects: list = field(default_factory=list)
    ocr_text_pages: OrderedDict = field(default_factory=OrderedDict)
    ocr_warning_shown: bool = False
