"""Qt editing layer for OpenReader v1.3.0 Fill / Edit / Sign.

The document model and persistence live in ``edit_objects`` (Qt-free).  This
module owns the interactive overlays, the inline text editor, the signature
creator and the per-tab editing controller.

The controller is attached to the window's persistent page QLabels used by
both single-page and virtualized continuous rendering, so editing works in
continuous-scroll mode without switching modes.
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path

from PySide6.QtCore import QBuffer, QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer, Signal, QObject
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QImage,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import edit_objects as eo
from . import signature_store as ss

HANDLE = 7
MIN_SIZE = 16
CONTENT_OFFSET = 1


def _qt_font_family(pdf_family: str) -> str:
    return {
        "Helvetica": "Arial",
        "Times-Roman": "Times New Roman",
        "Courier": "Courier New",
    }.get(pdf_family, pdf_family)


def _pdf_rect_to_label(
    rect: tuple[float, float, float, float],
    page_rect,
    zoom: float,
) -> QRect:
    x0 = round((rect[0] - page_rect.x0) * zoom) + CONTENT_OFFSET
    y0 = round((rect[1] - page_rect.y0) * zoom) + CONTENT_OFFSET
    x1 = round((rect[2] - page_rect.x0) * zoom) + CONTENT_OFFSET
    y1 = round((rect[3] - page_rect.y0) * zoom) + CONTENT_OFFSET
    return QRect(x0, y0, max(1, x1 - x0), max(1, y1 - y0))


def _label_rect_to_pdf(
    rect: QRect,
    page_rect,
    zoom: float,
) -> tuple[float, float, float, float]:
    if zoom <= 0:
        zoom = 1.0
    x0 = page_rect.x0 + (rect.x() - CONTENT_OFFSET) / zoom
    y0 = page_rect.y0 + (rect.y() - CONTENT_OFFSET) / zoom
    x1 = page_rect.x0 + (rect.x() + rect.width() - CONTENT_OFFSET) / zoom
    y1 = page_rect.y0 + (rect.y() + rect.height() - CONTENT_OFFSET) / zoom
    return (x0, y0, x1, y1)


class TextEditOverlay(QTextEdit):
    """Inline multiline editor anchored over a text object."""

    committed = Signal(str)
    cancelled = Signal()

    def __init__(self, text: str, style: eo.TextStyle, parent=None):
        super().__init__(parent)
        self.setPlainText(text)
        self.setAcceptRichText(False)
        self.setTabChangesFocus(False)
        self.setObjectName("InlineTextEditor")
        self._apply_style(style)
        self.setStyleSheet(
            "QTextEdit#InlineTextEditor {"
            " background: #ffffff; color: #111111;"
            " border: 1.5px solid #ff255f; border-radius: 2px;"
            " padding: 2px; }"
        )
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def _apply_style(self, style: eo.TextStyle) -> None:
        style = style.normalized()
        font = QFont(_qt_font_family(style.font_family))
        font.setPointSizeF(max(1.0, style.font_size))
        font.setBold(style.bold)
        font.setItalic(style.italic)
        font.setUnderline(style.underline)
        self.setFont(font)
        self.setTextColor(QColor(style.color))
        if style.align == "center":
            self.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        elif style.align == "right":
            self.setAlignment(Qt.AlignmentFlag.AlignRight)
        else:
            self.setAlignment(Qt.AlignmentFlag.AlignLeft)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (
            event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.committed.emit(self.toPlainText())
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class EditObjectWidget(QWidget):
    """Transparent selection/resize handle over a rendered PDF object."""

    selected = Signal(str)
    geometryCommitted = Signal(str, object)
    editRequested = Signal(str)

    def __init__(self, controller, obj: eo.EditObject, page_rect, zoom: float, parent):
        super().__init__(parent)
        self.controller = controller
        self.obj = obj
        self.page_rect = page_rect
        self.zoom = zoom
        self._hover = False
        self._selected = False
        self._mode = None
        self._handle = None
        self._start_pos = QPoint()
        self._start_rect = QRect()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setGeometry(_pdf_rect_to_label(obj.rect, page_rect, zoom))

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.update()

    def set_geometry_from_object(self) -> None:
        self.setGeometry(_pdf_rect_to_label(self.obj.rect, self.page_rect, self.zoom))

    # -- painting ------------------------------------------------------

    def paintEvent(self, event):
        if not (self._selected or self._hover):
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        accent = QColor("#ff255f")
        pen = QPen(accent, 1.4, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawRect(self.rect().adjusted(1, 1, -1, -1))
        if self._selected:
            painter.setPen(QPen(QColor("#ffffff"), 1.0))
            painter.setBrush(accent)
            for point in self._handle_points():
                painter.drawRect(
                    QRect(
                        point.x() - HANDLE // 2,
                        point.y() - HANDLE // 2,
                        HANDLE,
                        HANDLE,
                    )
                )
        painter.end()

    def _handle_points(self) -> list[QPoint]:
        r = self.rect()
        return [
            QPoint(r.left(), r.top()),
            QPoint(r.center().x(), r.top()),
            QPoint(r.right(), r.top()),
            QPoint(r.left(), r.center().y()),
            QPoint(r.right(), r.center().y()),
            QPoint(r.left(), r.bottom()),
            QPoint(r.center().x(), r.bottom()),
            QPoint(r.right(), r.bottom()),
        ]

    def _handle_at(self, pos: QPoint):
        if not self._selected:
            return None
        for index, point in enumerate(self._handle_points()):
            if (pos - point).manhattanLength() <= HANDLE + 4:
                return index
        return None

    # -- interaction ---------------------------------------------------

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        self.selected.emit(self.obj.oid)
        self._start_pos = event.position().toPoint()
        self._start_rect = self.geometry()
        self._handle = self._handle_at(self._start_pos)
        self._mode = "resize" if self._handle is not None else "move"
        event.accept()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        if self._mode is None:
            handle = self._handle_at(pos)
            if handle is not None:
                self.setCursor(self._cursor_for_handle(handle))
            elif self.obj.kind == eo.TEXT_KIND:
                self.setCursor(Qt.CursorShape.IBeamCursor)
            else:
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            event.accept()
            return
        delta = pos - self._start_pos
        rect = QRect(self._start_rect)
        if self._mode == "move":
            rect.translate(delta)
        else:
            rect = self._resized_rect(self._start_rect, self._handle, delta)
        self.setGeometry(self._clamped_rect(rect))
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._mode is None:
            event.ignore()
            return
        self._mode = None
        self._handle = None
        pdf_rect = _label_rect_to_pdf(self.geometry(), self.page_rect, self.zoom)
        self.geometryCommitted.emit(self.obj.oid, pdf_rect)
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if self.obj.kind == eo.TEXT_KIND and event.button() == Qt.MouseButton.LeftButton:
            self.editRequested.emit(self.obj.oid)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        event.ignore()

    def _resized_rect(self, start: QRect, handle, delta: QPoint) -> QRect:
        rect = QRect(start)
        left, top = rect.left(), rect.top()
        right, bottom = rect.right(), rect.bottom()
        if handle in (0, 3, 5):
            left += delta.x()
        if handle in (2, 4, 7):
            right += delta.x()
        if handle in (0, 1, 2):
            top += delta.y()
        if handle in (5, 6, 7):
            bottom += delta.y()
        if right - left < MIN_SIZE:
            right = left + MIN_SIZE
        if bottom - top < MIN_SIZE:
            bottom = top + MIN_SIZE
        rect = QRect(QPoint(left, top), QPoint(right, bottom))
        if self.obj.kind != eo.TEXT_KIND:
            aspect = max(0.01, self._start_rect.width() / max(1, self._start_rect.height()))
            if abs(rect.width() / max(1, rect.height()) - aspect) > 0.001:
                height = max(MIN_SIZE, int(rect.width() / aspect))
                if handle in (0, 2):
                    rect.setTop(rect.bottom() - height)
                else:
                    rect.setBottom(rect.top() + height)
        return rect

    def _clamped_rect(self, rect: QRect) -> QRect:
        bounds = self.parent().rect()
        rect = rect.normalized()
        if rect.left() < 0:
            rect.moveLeft(0)
        if rect.top() < 0:
            rect.moveTop(0)
        if rect.right() > bounds.right():
            rect.moveRight(bounds.right())
        if rect.bottom() > bounds.bottom():
            rect.moveBottom(bounds.bottom())
        return rect

    @staticmethod
    def _cursor_for_handle(handle) -> Qt.CursorShape:
        return {
            0: Qt.CursorShape.SizeFDiagCursor,
            1: Qt.CursorShape.SizeVerCursor,
            2: Qt.CursorShape.SizeBDiagCursor,
            3: Qt.CursorShape.SizeHorCursor,
            4: Qt.CursorShape.SizeHorCursor,
            5: Qt.CursorShape.SizeBDiagCursor,
            6: Qt.CursorShape.SizeVerCursor,
            7: Qt.CursorShape.SizeFDiagCursor,
        }.get(handle, Qt.CursorShape.SizeAllCursor)


class EditController(QObject):
    """Per-tab editing state for text, signatures and images."""

    selectionChanged = Signal(object)
    statusMessage = Signal(str)
    dirtyChanged = Signal(bool)
    toolChanged = Signal(object)

    def __init__(self, window, tab_id: int):
        super().__init__(window)
        self.window = window
        self.tab_id = tab_id
        self.doc = None
        self.path = None
        self.objects: list[eo.EditObject] = []
        self.history: list[list[eo.EditObject]] = []
        self.history_index = 0
        self.saved_index = 0
        self.tool: str | None = None
        self.pending_kind: str | None = None
        self.pending_png: bytes = b""
        self.pending_name = ""
        self.selected_oid: str | None = None
        self._overlays: dict[str, EditObjectWidget] = {}
        self._labels_by_page: dict[int, QWidget] = {}
        self._editor: TextEditOverlay | None = None
        self._editing_oid: str | None = None
        self._editing_original = ""
        self._clipboard: eo.EditObject | None = None
        self._active = False

    # -- lifecycle -----------------------------------------------------

    def load(self, doc, path) -> None:
        self.doc = doc
        self.path = path
        self.objects = eo.list_objects(doc) if doc is not None else []
        self.history = [[o.copy() for o in self.objects]]
        self.history_index = 0
        self.saved_index = 0
        self.selected_oid = None
        self.tool = None
        self._active = False
        self._detach_overlays()

    def mark_saved(self) -> None:
        self.saved_index = self.history_index
        self.dirtyChanged.emit(self.is_dirty())

    def is_dirty(self) -> bool:
        return self.history_index != self.saved_index

    def selected_object(self) -> eo.EditObject | None:
        return self.object_by_oid(self.selected_oid) if self.selected_oid else None

    def object_by_oid(self, oid: str | None) -> eo.EditObject | None:
        if not oid:
            return None
        for obj in self.objects:
            if obj.oid == oid:
                return obj
        return None

    # -- tools ---------------------------------------------------------

    def set_tool(self, tool: str | None) -> None:
        if tool not in (None, "fill", "text", "sign", "image"):
            return
        if tool != self.tool:
            self._finish_text_edit()
        self.tool = tool
        self._active = tool is not None
        if tool is None:
            self.pending_kind = None
            self.pending_png = b""
            self.pending_name = ""
        self._set_page_cursors()
        self.toolChanged.emit(tool)
        if self._active:
            self.refresh_visible()
        else:
            self._detach_overlays()
        if tool != "fill":
            self.select(None)

    def set_pending_image(self, kind: str, png_bytes: bytes, name: str = "") -> None:
        self.pending_kind = kind
        self.pending_png = png_bytes
        self.pending_name = name
        self.set_tool("sign" if kind == eo.SIGNATURE_KIND else "image")

    def refresh_visible(self) -> None:
        if (
            not self._active
            or self.doc is None
            or getattr(self.doc, "is_closed", False)
        ):
            self._detach_overlays()
            return
        labels = list(getattr(self.window, "_continuous_pages", []) or [])
        for page_index, label in enumerate(labels):
            if not self._is_label_rendered(label):
                self.detach_page(label)
                continue
            zoom = getattr(self.window, "_continuous_layout_zoom", None)
            if zoom:
                self.attach_page(label, page_index, zoom)
        if not getattr(self.window, "_continuous_mode", True):
            label = getattr(self.window, "page_label", None)
            if label is not None and self.doc is not None:
                zoom = getattr(self.window, "current_render_zoom", 1.0)
                self.attach_page(label, self._current_page(), zoom)

    def _is_label_rendered(self, label) -> bool:
        try:
            return bool(label.pixmap())
        except Exception:
            return True

    def _current_page(self) -> int:
        return int(getattr(self.window, "current_page", 0) or 0)

    def _set_page_cursors(self) -> None:
        cursor = Qt.CursorShape.CrossCursor if self.tool else Qt.CursorShape.ArrowCursor
        for label in getattr(self.window, "_continuous_pages", []) or []:
            label.setCursor(cursor)
        page_label = getattr(self.window, "page_label", None)
        if page_label is not None:
            page_label.setCursor(cursor)

    # -- overlays ------------------------------------------------------

    def attach_page(self, label, page_index: int, zoom: float) -> None:
        if (
            not self._active
            or self.doc is None
            or getattr(self.doc, "is_closed", False)
        ):
            return
        self._labels_by_page[page_index] = label
        for oid, widget in list(self._overlays.items()):
            if widget.parent() is label and self.object_by_oid(oid) is None:
                widget.setParent(None)
                widget.deleteLater()
                self._overlays.pop(oid, None)
        try:
            page = self.doc[page_index]
        except Exception:
            return
        for obj in self.objects:
            if obj.page_index != page_index:
                continue
            widget = self._overlays.get(obj.oid)
            if widget is None or widget.parent() is not label:
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()
                widget = EditObjectWidget(self, obj, page.rect, zoom, label)
                widget.selected.connect(self.select)
                widget.geometryCommitted.connect(self._on_geometry_committed)
                widget.editRequested.connect(self.begin_text_edit)
                self._overlays[obj.oid] = widget
            widget.obj = obj
            widget.page_rect = page.rect
            widget.zoom = zoom
            widget.setGeometry(_pdf_rect_to_label(obj.rect, page.rect, zoom))
            widget.show()
            widget.set_selected(obj.oid == self.selected_oid)

    def detach_page(self, label) -> None:
        for oid, widget in list(self._overlays.items()):
            if widget.parent() is label:
                widget.setParent(None)
                widget.deleteLater()
                self._overlays.pop(oid, None)

    def detach_all(self) -> None:
        # Never lose an in-progress text edit when the layout is rebuilt,
        # the tab changes or the document is saved.
        if self._editor is not None:
            try:
                self._finish_text_edit()
            except Exception:
                pass
        self._close_editor()
        self._detach_overlays()

    def _detach_overlays(self) -> None:
        for widget in list(self._overlays.values()):
            widget.setParent(None)
            widget.deleteLater()
        self._overlays.clear()
        self._labels_by_page.clear()

    def _refresh_selection_overlays(self) -> None:
        for oid, widget in self._overlays.items():
            widget.set_selected(oid == self.selected_oid)

    def select(self, oid: str | None) -> None:
        if self._editor is not None and oid != self._editing_oid:
            self._finish_text_edit()
        self.selected_oid = oid
        self._refresh_selection_overlays()
        obj = self.object_by_oid(oid)
        self.selectionChanged.emit(obj)

    # -- input ---------------------------------------------------------

    def handle_page_click(self, page_index: int, label, pos, zoom: float) -> bool:
        if not self._active or self.doc is None:
            return False
        if self.tool == "fill":
            return False
        try:
            page = self.doc[page_index]
        except Exception:
            return True
        if not eo.page_allows_editing(page):
            self.statusMessage.emit("Editing rotated pages is not supported in this release.")
            return True
        if not self._ensure_editable():
            return True
        pdf_x = page.rect.x0 + (pos.x() - CONTENT_OFFSET) / max(0.001, zoom)
        pdf_y = page.rect.y0 + (pos.y() - CONTENT_OFFSET) / max(0.001, zoom)
        if self.tool == "text":
            self.add_text_at(page_index, pdf_x, pdf_y, label, zoom)
            return True
        if self.tool in ("sign", "image") and self.pending_png:
            self.add_image_at(page_index, pdf_x, pdf_y, label, zoom)
            return True
        return False

    def add_text_at(self, page_index: int, x: float, y: float, label, zoom: float) -> None:
        if self.doc is None:
            return
        page = self.doc[page_index]
        width = min(220.0, max(80.0, page.rect.width - (x - page.rect.x0) - 8))
        rect = (x, y, x + width, min(page.rect.y1 - 4, y + 30))
        obj = eo.EditObject(
            oid=uuid.uuid4().hex,
            kind=eo.TEXT_KIND,
            page_index=page_index,
            rect=rect,
            text="",
            style=eo.TextStyle(),
            z=self._next_z(),
        )
        try:
            obj = eo.add_object(self.doc, obj)
        except Exception as exc:
            self.statusMessage.emit(f"Could not add text: {exc}")
            return
        self.objects.append(obj)
        self._record()
        self.select(obj.oid)
        self.window.render_page()
        QTimer.singleShot(0, lambda: self.begin_text_edit(obj.oid))
        self.statusMessage.emit(
            "Text added. Drag or resize it, or use the formatting bar."
        )
        self.tool = None
        self.pending_kind = None
        self.toolChanged.emit(None)
        self._set_page_cursors()

    def add_image_at(self, page_index: int, x: float, y: float, label, zoom: float) -> None:
        if self.doc is None or not self.pending_png:
            return
        page = self.doc[page_index]
        width = min(180.0, max(60.0, page.rect.width - (x - page.rect.x0) - 8))
        height = eo.aspect_size(width, self.pending_png)
        if y + height > page.rect.y1 - 4:
            y = max(page.rect.y0 + 4, page.rect.y1 - height - 4)
        rect = (x, y, x + width, y + height)
        obj = eo.EditObject(
            oid=uuid.uuid4().hex,
            kind=self.pending_kind or eo.IMAGE_KIND,
            page_index=page_index,
            rect=rect,
            image_png=self.pending_png,
            name=self.pending_name,
            z=self._next_z(),
        )
        try:
            obj = eo.add_object(self.doc, obj)
        except Exception as exc:
            self.statusMessage.emit(f"Could not place image: {exc}")
            return
        self.objects.append(obj)
        self._record()
        self.select(obj.oid)
        self.window.render_page()
        self.statusMessage.emit(
            "Signature placed."
            if obj.kind == eo.SIGNATURE_KIND
            else "Image placed."
        )
        self.tool = None
        self.pending_kind = None
        self.pending_png = b""
        self.pending_name = ""
        self.toolChanged.emit(None)
        self._set_page_cursors()

    def _on_geometry_committed(self, oid: str, pdf_rect) -> None:
        obj = self.object_by_oid(oid)
        if obj is None or self.doc is None:
            return
        obj.rect = tuple(pdf_rect)
        try:
            eo.remove_object(self.doc, obj)
            refreshed = eo.add_object(self.doc, obj)
        except Exception as exc:
            self.statusMessage.emit(f"Could not update object: {exc}")
            return
        self._replace_object(refreshed)
        self._record()
        self.window.render_page()
        QTimer.singleShot(0, self.refresh_visible)

    # -- text editing --------------------------------------------------

    def begin_text_edit(self, oid: str) -> None:
        obj = self.object_by_oid(oid)
        if obj is None or obj.kind != eo.TEXT_KIND or self.doc is None:
            return
        if self._editor is not None:
            self._finish_text_edit()
        page_index = obj.page_index
        label = self._labels_by_page.get(page_index)
        if label is None:
            labels = getattr(self.window, "_continuous_pages", []) or []
            if getattr(self.window, "_continuous_mode", True) and 0 <= page_index < len(labels):
                label = labels[page_index]
            else:
                label = getattr(self.window, "page_label", None)
        if label is None:
            self.statusMessage.emit("Scroll to the text object and try again.")
            return
        try:
            page = self.doc[page_index]
        except Exception:
            return
        zoom = (
            getattr(self.window, "_continuous_layout_zoom", None)
            or getattr(self.window, "current_render_zoom", 1.0)
        )
        rect = _pdf_rect_to_label(obj.rect, page.rect, zoom)
        editor = TextEditOverlay(obj.text, obj.style, label)
        editor.setGeometry(rect.adjusted(-4, -4, 4, 4))
        editor.committed.connect(lambda text, o=obj.oid: self._commit_text_edit(o, text))
        editor.cancelled.connect(self._cancel_text_edit)
        editor.show()
        editor.setFocus()
        editor.selectAll()
        self._editor = editor
        self._editing_oid = obj.oid
        self._editing_original = obj.text
        self.selectionChanged.emit(obj)

    def _auto_grow_text(self, obj: eo.EditObject, text: str) -> None:
        """Grow a text box vertically so multiline content is not clipped."""
        if self.doc is None or obj.kind != eo.TEXT_KIND:
            return
        try:
            font = QFont(_qt_font_family(obj.style.font_family))
            font.setPointSizeF(max(1.0, float(obj.style.font_size)))
            metrics = QFontMetrics(font)
            x0, y0, x1, y1 = obj.rect
            width = max(24.0, x1 - x0)
            lines = 0
            for paragraph in (text or " ").split("\n"):
                advance = metrics.horizontalAdvance(paragraph or " ")
                lines += max(1, int(advance / width) + 1)
            needed = max(28.0, lines * (metrics.height() + 2) + 8)
            if (y1 - y0) < needed:
                page = self.doc[obj.page_index]
                obj.rect = (
                    x0,
                    y0,
                    x1,
                    min(page.rect.y1 - 2, y0 + needed),
                )
        except Exception:
            pass

    def _commit_text_edit(self, oid: str, text: str) -> None:
        obj = self.object_by_oid(oid)
        if obj is None or self.doc is None:
            self._close_editor()
            return
        if not text.strip() and not obj.text.strip():
            self._delete_object(obj)
            self._close_editor()
            return
        self._auto_grow_text(obj, text)
        self._apply_text(obj, text=text)
        self._close_editor()
        self.selectionChanged.emit(self.selected_object())

    def _cancel_text_edit(self) -> None:
        obj = self.object_by_oid(self._editing_oid) if self._editing_oid else None
        if obj is not None and not obj.text.strip() and not self._editing_original.strip():
            self._delete_object(obj)
        self._close_editor()
        self.selectionChanged.emit(self.selected_object())

    def _finish_text_edit(self) -> None:
        if self._editor is not None:
            self._commit_text_edit(self._editing_oid or "", self._editor.toPlainText())

    def _close_editor(self) -> None:
        if self._editor is not None:
            self._editor.hide()
            self._editor.setParent(None)
            self._editor.deleteLater()
        self._editor = None
        self._editing_oid = None
        self._editing_original = ""

    def _apply_text(self, obj: eo.EditObject, text: str | None = None,
                    style: eo.TextStyle | None = None, rotation: int | None = None) -> None:
        if self.doc is None:
            return
        if text is not None:
            obj.text = text
        if style is not None:
            obj.style = style.normalized()
        if rotation is not None:
            obj.rotation = int(rotation) % 360
        try:
            eo.remove_object(self.doc, obj)
            refreshed = eo.add_object(self.doc, obj)
        except Exception as exc:
            self.statusMessage.emit(f"Could not update text: {exc}")
            return
        self._replace_object(refreshed)
        self._record()
        self.window.render_page()
        QTimer.singleShot(0, self._refresh_after_change)

    def apply_style(self, style: eo.TextStyle) -> None:
        obj = self.selected_object()
        if obj is None:
            return
        if obj.kind == eo.TEXT_KIND:
            self._apply_text(obj, style=style)
            if self._editor is not None:
                self._editor._apply_style(style)
        else:
            self.statusMessage.emit("Formatting applies to text objects.")

    def rotate_selected(self, delta: int = 90) -> None:
        obj = self.selected_object()
        if obj is None or self.doc is None:
            return
        if not self._ensure_editable():
            return
        if obj.kind == eo.TEXT_KIND:
            new_rotation = (obj.rotation + int(delta)) % 360
            if int(delta) % 180 != 0:
                x0, y0, x1, y1 = obj.rect
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                width, height = x1 - x0, y1 - y0
                obj.rect = (
                    cx - height / 2,
                    cy - width / 2,
                    cx + height / 2,
                    cy + width / 2,
                )
            self._apply_text(obj, rotation=new_rotation)
            return
        try:
            rotated = eo.rotated_png(obj.image_png, delta)
        except Exception as exc:
            self.statusMessage.emit(f"Could not rotate image: {exc}")
            return
        old = obj.rect
        cx = (old[0] + old[2]) / 2
        cy = (old[1] + old[3]) / 2
        width = max(old[2] - old[0], old[3] - old[1])
        height = eo.aspect_size(width, rotated)
        obj.image_png = rotated
        obj.rect = (cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2)
        obj.rotation = (obj.rotation + int(delta)) % 360
        try:
            eo.remove_object(self.doc, obj)
            refreshed = eo.add_object(self.doc, obj)
        except Exception as exc:
            self.statusMessage.emit(f"Could not rotate image: {exc}")
            return
        self._replace_object(refreshed)
        self._record()
        self.window.render_page()
        QTimer.singleShot(0, self._refresh_after_change)

    # -- object operations ---------------------------------------------

    def delete_selected(self) -> None:
        obj = self.selected_object()
        if obj is not None:
            self._delete_object(obj)

    def _delete_object(self, obj: eo.EditObject) -> None:
        if self.doc is None:
            return
        try:
            eo.remove_object(self.doc, obj)
        except Exception:
            pass
        self.objects = [o for o in self.objects if o.oid != obj.oid]
        self.selected_oid = None
        self._record()
        self.selectionChanged.emit(None)
        self.window.render_page()
        QTimer.singleShot(0, self.refresh_visible)

    def duplicate_selected(self) -> None:
        obj = self.selected_object()
        if obj is None or self.doc is None:
            return
        if not self._ensure_editable():
            return
        duplicate = obj.copy()
        duplicate.oid = uuid.uuid4().hex
        duplicate.rect = (
            obj.rect[0] + 12,
            obj.rect[1] + 12,
            obj.rect[2] + 12,
            obj.rect[3] + 12,
        )
        duplicate.z = self._next_z()
        try:
            duplicate = eo.add_object(self.doc, duplicate)
        except Exception as exc:
            self.statusMessage.emit(f"Could not duplicate: {exc}")
            return
        self.objects.append(duplicate)
        self._record()
        self.select(duplicate.oid)
        self.window.render_page()
        QTimer.singleShot(0, self._refresh_after_change)

    def copy_selected(self) -> bool:
        obj = self.selected_object()
        if obj is None:
            return False
        self._clipboard = obj.copy()
        self.statusMessage.emit("Object copied.")
        return True

    def paste(self) -> bool:
        if self._clipboard is None or self.doc is None:
            return False
        if not self._ensure_editable():
            return False
        obj = self._clipboard.copy()
        obj.oid = uuid.uuid4().hex
        obj.page_index = self._current_page()
        obj.rect = (
            obj.rect[0] + 16,
            obj.rect[1] + 16,
            obj.rect[2] + 16,
            obj.rect[3] + 16,
        )
        obj.z = self._next_z()
        try:
            obj = eo.add_object(self.doc, obj)
        except Exception as exc:
            self.statusMessage.emit(f"Could not paste: {exc}")
            return False
        self.objects.append(obj)
        self._record()
        self.select(obj.oid)
        self.window.render_page()
        QTimer.singleShot(0, self._refresh_after_change)
        return True

    # -- undo / redo ---------------------------------------------------

    def undo(self) -> bool:
        if self.history_index <= 0 or self.doc is None:
            return False
        self.history_index -= 1
        self._apply_history_state()
        return True

    def redo(self) -> bool:
        if self.history_index >= len(self.history) - 1 or self.doc is None:
            return False
        self.history_index += 1
        self._apply_history_state()
        return True

    def _record(self) -> None:
        self.history = self.history[: self.history_index + 1]
        self.history.append([o.copy() for o in self.objects])
        self.history_index = len(self.history) - 1
        self.dirtyChanged.emit(self.is_dirty())

    def _apply_history_state(self) -> None:
        if self.doc is None:
            return
        state = self.history[self.history_index]
        try:
            eo.apply_objects(self.doc, state)
        except Exception as exc:
            self.statusMessage.emit(f"Could not restore edit state: {exc}")
            return
        self.objects = eo.list_objects(self.doc)
        self.selected_oid = None
        self._close_editor()
        self.selectionChanged.emit(None)
        self.dirtyChanged.emit(self.is_dirty())
        self.window.render_page()
        QTimer.singleShot(0, self._refresh_after_change)

    # -- helpers -------------------------------------------------------

    def _refresh_after_change(self) -> None:
        self.refresh_visible()
        self._refresh_selection_overlays()

    def _replace_object(self, refreshed: eo.EditObject) -> None:
        for index, obj in enumerate(self.objects):
            if obj.oid == refreshed.oid:
                self.objects[index] = refreshed
                break
        else:
            self.objects.append(refreshed)

    def _next_z(self) -> int:
        return max((o.z for o in self.objects), default=0) + 1

    def _ensure_editable(self) -> bool:
        if self.doc is None:
            return False
        encrypted = False
        checker = getattr(self.window, "_current_document_encrypted", None)
        if checker is not None:
            try:
                encrypted = bool(checker())
            except Exception:
                encrypted = False
        if not eo.document_allows_editing(self.doc, encrypted=encrypted):
            self.statusMessage.emit(
                "This document is read-only or encrypted and cannot be edited."
            )
            return False
        checker = getattr(self.window, "_confirm_edit_on_signed", None)
        if checker is not None and not checker():
            return False
        return True


# ---------------------------------------------------------------------------
# Signature creation
# ---------------------------------------------------------------------------


class SignatureCanvas(QWidget):
    """Smooth freehand signature canvas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self._strokes: list[list[QPointF]] = []
        self._current: list[QPointF] = []

    def clear(self) -> None:
        self._strokes = []
        self._current = []
        self.update()

    def has_content(self) -> bool:
        return any(len(stroke) > 1 for stroke in self._strokes) or len(self._current) > 1

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor("#dfe0e4"), 1, Qt.PenStyle.DashLine))
        baseline = int(self.height() * 0.78)
        painter.drawLine(12, baseline, self.width() - 12, baseline)
        pen = QPen(QColor("#111111"), 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        for stroke in self._strokes + ([self._current] if self._current else []):
            if len(stroke) == 1:
                painter.drawPoint(stroke[0])
                continue
            path = self._stroke_path(stroke)
            painter.drawPath(path)
        painter.end()

    def _stroke_path(self, points: list[QPointF]):
        from PySide6.QtGui import QPainterPath

        path = QPainterPath(points[0])
        for index in range(1, len(points)):
            mid = (points[index - 1] + points[index]) / 2.0
            path.quadTo(points[index - 1], mid)
        path.lineTo(points[-1])
        return path

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._current = [event.position()]
            self.update()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._current:
            self._current.append(event.position())
            self.update()
            event.accept()

    def mouseReleaseEvent(self, event):
        if self._current:
            if len(self._current) > 1:
                self._strokes.append(self._current)
            self._current = []
            self.update()
            event.accept()

    def to_png(self) -> bytes:
        scale = 3
        image = QImage(
            max(1, self.width()) * scale,
            max(1, self.height()) * scale,
            QImage.Format.Format_ARGB32_Premultiplied,
        )
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.scale(scale, scale)
        painter.setPen(QPen(QColor("#111111"), 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        for stroke in self._strokes:
            if len(stroke) == 1:
                painter.drawPoint(stroke[0])
            else:
                painter.drawPath(self._stroke_path(stroke))
        painter.end()
        buffer = QBuffer()
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        return bytes(buffer.data())


def _image_to_png(image: QImage) -> bytes:
    buffer = QBuffer()
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data())


def _typed_signature_png(name: str, family: str) -> bytes:
    font = QFont(family)
    font.setPointSize(42)
    font.setItalic(True)
    metrics = QFontMetrics(font)
    width = max(320, metrics.horizontalAdvance(name) + 80)
    height = max(120, metrics.height() + 60)
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setFont(font)
    painter.setPen(QColor("#111111"))
    painter.drawText(image.rect(), Qt.AlignmentFlag.AlignCenter, name)
    painter.end()
    return _image_to_png(image)


class SignatureDialog(QDialog):
    """Draw, type or import a visual signature; optionally save it locally."""

    def __init__(self, store: ss.SignatureStore, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Signature")
        self.resize(620, 460)
        self.store = store
        self.result_png: bytes = b""
        self.result_name: str = ""
        self.result_kind: str = "drawn"
        self._imported: QImage | None = None

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        # Draw
        self.canvas = SignatureCanvas()
        draw_tab = QWidget()
        draw_layout = QVBoxLayout(draw_tab)
        draw_layout.addWidget(QLabel("Draw your signature with a mouse, trackpad, pen or touchscreen."))
        draw_layout.addWidget(self.canvas, 1)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.canvas.clear)
        draw_layout.addWidget(clear_btn, 0, Qt.AlignmentFlag.AlignLeft)
        self.tabs.addTab(draw_tab, "Draw")

        # Type
        type_tab = QWidget()
        type_layout = QFormLayout(type_tab)
        self.type_name = QLineEdit()
        self.type_name.setPlaceholderText("Your name")
        self.type_name.textChanged.connect(self._update_typed_preview)
        self.type_font = QComboBox()
        for family in self._signature_fonts():
            self.type_font.addItem(family)
        self.type_font.currentTextChanged.connect(self._update_typed_preview)
        self.type_preview = QLabel("Preview")
        self.type_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.type_preview.setMinimumHeight(140)
        self.type_preview.setStyleSheet("background:#ffffff; border:1px solid #dfe0e4;")
        type_layout.addRow("Name", self.type_name)
        type_layout.addRow("Style", self.type_font)
        type_layout.addRow(self.type_preview)
        self.tabs.addTab(type_tab, "Type")

        # Import
        import_tab = QWidget()
        import_layout = QVBoxLayout(import_tab)
        choose_btn = QPushButton("Choose Image…")
        choose_btn.clicked.connect(self._choose_import)
        import_layout.addWidget(choose_btn, 0, Qt.AlignmentFlag.AlignLeft)
        self.import_preview = QLabel("PNG, JPEG, BMP or WebP")
        self.import_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.import_preview.setMinimumHeight(140)
        self.import_preview.setStyleSheet("background:#ffffff; border:1px solid #dfe0e4;")
        import_layout.addWidget(self.import_preview, 1)
        self.tabs.addTab(import_tab, "Import")

        # Saved
        saved_tab = QWidget()
        saved_layout = QVBoxLayout(saved_tab)
        self.saved_list = QListWidget()
        self._reload_saved()
        saved_layout.addWidget(self.saved_list, 1)
        saved_buttons = QHBoxLayout()
        use_saved = QPushButton("Use Selected")
        use_saved.clicked.connect(self._use_saved)
        delete_saved = QPushButton("Delete Selected")
        delete_saved.clicked.connect(self._delete_saved)
        saved_buttons.addWidget(use_saved)
        saved_buttons.addWidget(delete_saved)
        saved_buttons.addStretch(1)
        saved_layout.addLayout(saved_buttons)
        self.tabs.addTab(saved_tab, "Saved")

        self.save_checkbox = QCheckBox("Save to my local signature library")
        self.save_checkbox.setChecked(False)
        layout.addWidget(self.save_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._update_typed_preview()

    def _signature_fonts(self) -> list[str]:
        preferred = [
            "Segoe Script",
            "Brush Script MT",
            "Lucida Handwriting",
            "Gabriola",
            "Freestyle Script",
            "Kunstler Script",
            "Comic Sans MS",
        ]
        available = set(QFontDatabase.families())
        fonts = [name for name in preferred if name in available]
        for name in sorted(available):
            if name not in fonts and len(fonts) < 12:
                fonts.append(name)
        return fonts or ["Sans Serif"]

    def _update_typed_preview(self) -> None:
        name = self.type_name.text().strip()
        if not name:
            self.type_preview.setText("Preview")
            return
        family = self.type_font.currentText() or "Sans Serif"
        png = _typed_signature_png(name, family)
        image = QImage.fromData(png, "PNG")
        self.type_preview.setPixmap(QPixmap.fromImage(image).scaled(
            440, 130, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        ))

    def _choose_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Signature Image",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif)",
        )
        if not path:
            return
        image = QImage(path)
        if image.isNull():
            QMessageBox.warning(self, "Signature", "That image could not be read.")
            return
        self._imported = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        self.import_preview.setPixmap(QPixmap.fromImage(self._imported).scaled(
            440, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        ))

    def _reload_saved(self) -> None:
        self.saved_list.clear()
        for entry in self.store.list():
            item = QListWidgetItem(f"{entry.name}  ·  {entry.kind}")
            item.setData(Qt.ItemDataRole.UserRole, entry.id)
            self.saved_list.addItem(item)

    def _use_saved(self) -> None:
        item = self.saved_list.currentItem()
        if item is None:
            return
        entry_id = item.data(Qt.ItemDataRole.UserRole)
        try:
            png = self.store.load(entry_id)
        except Exception as exc:
            QMessageBox.warning(self, "Signature", f"Could not load signature: {exc}")
            return
        self.result_png = png
        self.result_name = item.text().split("  ·  ")[0]
        self.result_kind = "saved"
        self.accept()

    def _delete_saved(self) -> None:
        item = self.saved_list.currentItem()
        if item is None:
            return
        entry_id = item.data(Qt.ItemDataRole.UserRole)
        self.store.delete(entry_id)
        self._reload_saved()

    def _accept(self) -> None:
        index = self.tabs.currentIndex()
        if index == 0:
            if not self.canvas.has_content():
                QMessageBox.information(self, "Signature", "Draw a signature first.")
                return
            png = self.canvas.to_png()
            kind = "drawn"
            name = "Drawn signature"
        elif index == 1:
            name = self.type_name.text().strip()
            if not name:
                QMessageBox.information(self, "Signature", "Enter a name to type.")
                return
            png = _typed_signature_png(name, self.type_font.currentText() or "Sans Serif")
            kind = "typed"
        elif index == 2:
            if self._imported is None:
                QMessageBox.information(self, "Signature", "Choose an image first.")
                return
            png = _image_to_png(self._imported)
            kind = "imported"
            name = "Imported signature"
        else:
            return
        if self.save_checkbox.isChecked():
            try:
                self.store.save(name, png, kind)
            except Exception as exc:
                QMessageBox.warning(self, "Signature", f"Could not save signature: {exc}")
        self.result_png = png
        self.result_name = name
        self.result_kind = kind
        self.accept()
