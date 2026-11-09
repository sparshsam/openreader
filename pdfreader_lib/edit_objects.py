"""Editable PDF objects: text, signatures and images.

This module is deliberately Qt-free.  It owns the on-disk representation of
OpenReader-created objects and the document-level operations needed to add,
update, remove, undo and flatten them.

Persistence strategy
--------------------
* **Text** is stored as a native ``FreeText`` annotation.  The text, style,
  rotation and object id are also mirrored into a custom ``OpenReaderData``
  string key on the annotation xref, so OpenReader can find and re-edit its
  own objects after the file is saved and reopened.  FreeText keeps the text
  selectable and searchable in other PDF viewers.
* **Signatures and images** are stored as image XObjects placed in the page
  content by ``Page.insert_image``.  The object metadata lives in a custom
  ``OpenReaderData`` key on the image xref.  Images are reinserted when moved,
  resized, rotated or duplicated.
* Nothing here is temporary: every object is written into the PDF by the
  caller's save.  ``export_flattened`` uses PyMuPDF's ``Document.bake`` to
  convert annotations and widgets into page content on a copy, leaving the
  original document untouched.

All coordinates are PDF points in the page's unrotated coordinate space.
Pages with a non-zero ``/Rotate`` are rejected for editing by the GUI.
"""

from __future__ import annotations

import base64
import copy
import html
import io
import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

import fitz

META_KEY = "OpenReaderData"
TEXT_KIND = "text"
SIGNATURE_KIND = "signature"
IMAGE_KIND = "image"
EDITABLE_KINDS = (TEXT_KIND, SIGNATURE_KIND, IMAGE_KIND)

# Curated PDF Base-14 families.  These are embedded by every PDF viewer and
# keep user-added text selectable.  The label is what the UI shows.
TEXT_FONTS: tuple[tuple[str, str], ...] = (
    ("Helvetica", "Helvetica"),
    ("Times New Roman", "Times-Roman"),
    ("Courier New", "Courier"),
)
_FONT_ALIASES = {
    "helvetica": "Helvetica",
    "arial": "Helvetica",
    "sans": "Helvetica",
    "sans-serif": "Helvetica",
    "times": "Times-Roman",
    "times new roman": "Times-Roman",
    "serif": "Times-Roman",
    "courier": "Courier",
    "courier new": "Courier",
    "mono": "Courier",
    "monospace": "Courier",
}
_FONT_FILES = {
    "Helvetica": ("helv", "hebo", "heit", "hebi"),
    "Times-Roman": ("tiro", "tibo", "tiit", "tibi"),
    "Courier": ("cour", "cobo", "coit", "cobi"),
}


def normalize_font(family: str) -> str:
    key = (family or "").strip().lower()
    if key in _FONT_ALIASES:
        return _FONT_ALIASES[key]
    for label, pdf_name in TEXT_FONTS:
        if key == label.lower() or key == pdf_name.lower():
            return pdf_name
    return "Helvetica"


def _clamp_color(value: str) -> str:
    value = (value or "#000000").strip()
    if len(value) == 7 and value.startswith("#"):
        try:
            int(value[1:], 16)
            return value.lower()
        except ValueError:
            pass
    return "#000000"


def _rgb(hex_color: str) -> tuple[float, float, float]:
    color = _clamp_color(hex_color)
    return (
        int(color[1:3], 16) / 255.0,
        int(color[3:5], 16) / 255.0,
        int(color[5:7], 16) / 255.0,
    )


@dataclass
class TextStyle:
    font_family: str = "Helvetica"
    font_size: float = 14.0
    color: str = "#000000"
    bold: bool = False
    italic: bool = False
    underline: bool = False
    align: str = "left"

    def normalized(self) -> "TextStyle":
        align = self.align if self.align in ("left", "center", "right") else "left"
        return TextStyle(
            font_family=normalize_font(self.font_family),
            font_size=max(4.0, min(200.0, float(self.font_size or 14.0))),
            color=_clamp_color(self.color),
            bold=bool(self.bold),
            italic=bool(self.italic),
            underline=bool(self.underline),
            align=align,
        )

    def to_dict(self) -> dict:
        return asdict(self.normalized())

    @classmethod
    def from_dict(cls, data: dict | None) -> "TextStyle":
        data = data or {}
        return cls(
            font_family=normalize_font(str(data.get("font_family", "Helvetica"))),
            font_size=float(data.get("font_size", 14.0) or 14.0),
            color=str(data.get("color", "#000000") or "#000000"),
            bold=bool(data.get("bold", False)),
            italic=bool(data.get("italic", False)),
            underline=bool(data.get("underline", False)),
            align=str(data.get("align", "left") or "left"),
        ).normalized()


@dataclass
class EditObject:
    oid: str
    kind: str
    page_index: int
    rect: tuple[float, float, float, float]
    rotation: int = 0
    text: str = ""
    style: TextStyle = field(default_factory=TextStyle)
    image_png: bytes = b""
    name: str = ""
    z: int = 0
    xref: int = 0          # image XObject xref (runtime)
    annot_xref: int = 0    # FreeText annotation xref (runtime)

    def normalized(self) -> "EditObject":
        x0, y0, x1, y1 = (float(v) for v in self.rect)
        if x1 < x0:
            x0, x1 = x1, x0
        if y1 < y0:
            y0, y1 = y1, y0
        return EditObject(
            oid=self.oid or uuid.uuid4().hex,
            kind=self.kind,
            page_index=max(0, int(self.page_index)),
            rect=(x0, y0, max(x0 + 1.0, x1), max(y0 + 1.0, y1)),
            rotation=int(self.rotation or 0) % 360,
            text=self.text or "",
            style=self.style.normalized(),
            image_png=self.image_png or b"",
            name=self.name or "",
            z=int(self.z or 0),
            xref=int(self.xref or 0),
            annot_xref=int(self.annot_xref or 0),
        )

    def to_meta(self) -> dict:
        obj = self.normalized()
        return {
            "oid": obj.oid,
            "kind": obj.kind,
            "page": obj.page_index,
            "rect": [round(v, 4) for v in obj.rect],
            "rotation": obj.rotation,
            "text": obj.text,
            "style": obj.style.to_dict(),
            "name": obj.name,
            "z": obj.z,
        }

    @classmethod
    def from_meta(cls, meta: dict, *, xref: int = 0, annot_xref: int = 0,
                  image_png: bytes = b"") -> "EditObject":
        rect = meta.get("rect") or [0, 0, 100, 30]
        return cls(
            oid=str(meta.get("oid") or uuid.uuid4().hex),
            kind=str(meta.get("kind") or TEXT_KIND),
            page_index=int(meta.get("page", 0) or 0),
            rect=tuple(float(v) for v in rect[:4]),
            rotation=int(meta.get("rotation", 0) or 0),
            text=str(meta.get("text", "") or ""),
            style=TextStyle.from_dict(meta.get("style")),
            image_png=image_png,
            name=str(meta.get("name", "") or ""),
            z=int(meta.get("z", 0) or 0),
            xref=xref,
            annot_xref=annot_xref,
        ).normalized()

    def copy(self) -> "EditObject":
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# Metadata on PDF xrefs
# ---------------------------------------------------------------------------


def _meta_text(meta: dict) -> str:
    return fitz.get_pdf_str(json.dumps(meta, ensure_ascii=False))


def set_object_meta(doc: fitz.Document, xref: int, meta: dict) -> None:
    doc.xref_set_key(xref, META_KEY, _meta_text(meta))


def get_object_meta(doc: fitz.Document, xref: int) -> dict | None:
    try:
        kind, value = doc.xref_get_key(xref, META_KEY)
    except Exception:
        return None
    if kind != "string" or not value:
        return None
    try:
        meta = json.loads(value)
    except (TypeError, ValueError):
        return None
    if not isinstance(meta, dict) or meta.get("kind") not in EDITABLE_KINDS:
        return None
    return meta


# ---------------------------------------------------------------------------
# FreeText styling
# ---------------------------------------------------------------------------


def _fontname(style: TextStyle) -> str:
    family = normalize_font(style.font_family)
    names = _FONT_FILES.get(family, _FONT_FILES["Helvetica"])
    if style.bold and style.italic:
        return names[3]
    if style.bold:
        return names[1]
    if style.italic:
        return names[2]
    return names[0]


def _align_value(style: TextStyle) -> int:
    return {"left": 0, "center": 1, "right": 2}.get(style.align, 0)


def _style_css(style: TextStyle) -> str:
    style = style.normalized()
    parts = [
        f"font-family:{style.font_family}",
        f"font-size:{style.font_size:g}px",
        f"color:{style.color}",
        f"text-align:{style.align}",
    ]
    if style.bold:
        parts.append("font-weight:bold")
    if style.italic:
        parts.append("font-style:italic")
    if style.underline:
        parts.append("text-decoration:underline")
    return ";".join(parts)


def _html_text(text: str) -> str:
    body = html.escape(text or " ").replace("\r\n", "\n").replace("\r", "\n")
    return body.replace("\n", "<br>") or " "


def _add_text(doc: fitz.Document, obj: EditObject) -> EditObject:
    obj = obj.normalized()
    page = doc[obj.page_index]
    annot = page.add_freetext_annot(
        fitz.Rect(*obj.rect),
        _html_text(obj.text),
        fontsize=obj.style.font_size,
        fontname=_fontname(obj.style),
        text_color=_rgb(obj.style.color),
        border_width=0,
        align=_align_value(obj.style),
        rotate=obj.rotation,
        richtext=True,
        style=_style_css(obj.style),
    )
    try:
        annot.set_info(title="OpenReader", subject="OpenReader editable text")
    except Exception:
        pass
    annot.update()
    set_object_meta(doc, annot.xref, obj.to_meta())
    obj.annot_xref = annot.xref
    return obj


def _unique_png(png_bytes: bytes, oid: str) -> bytes:
    """Return PNG bytes with a unique metadata chunk.

    PyMuPDF reuses an existing image XObject for byte-identical images.  Two
    OpenReader image objects with their own metadata must not share one
    XObject, so each placement carries a small private tEXt chunk.
    """
    try:
        from PIL import Image, PngImagePlugin

        with Image.open(io.BytesIO(png_bytes)) as image:
            info = PngImagePlugin.PngInfo()
            info.add_text("OpenReaderOID", oid)
            buffer = io.BytesIO()
            image.save(buffer, "PNG", pnginfo=info)
            return buffer.getvalue()
    except Exception:
        return png_bytes


def _add_image(doc: fitz.Document, obj: EditObject) -> EditObject:
    obj = obj.normalized()
    if not obj.image_png:
        raise ValueError("image object has no image data")
    page = doc[obj.page_index]
    xref = page.insert_image(
        fitz.Rect(*obj.rect),
        stream=_unique_png(obj.image_png, obj.oid),
        overlay=True,
        keep_proportion=False,
    )
    set_object_meta(doc, xref, obj.to_meta())
    obj.xref = xref
    return obj


def add_object(doc: fitz.Document, obj: EditObject) -> EditObject:
    """Add an object to the document and return it with runtime xrefs set."""
    obj = obj.normalized()
    if obj.kind == TEXT_KIND:
        return _add_text(doc, obj)
    if obj.kind in (SIGNATURE_KIND, IMAGE_KIND):
        return _add_image(doc, obj)
    raise ValueError(f"unsupported object kind: {obj.kind}")


# ---------------------------------------------------------------------------
# Discovery / deletion
# ---------------------------------------------------------------------------


def _image_bytes(doc: fitz.Document, xref: int) -> bytes:
    try:
        extracted = doc.extract_image(xref)
        return extracted.get("image", b"") or b""
    except Exception:
        return b""


def _objects_on_page(doc: fitz.Document, page_index: int) -> list[EditObject]:
    page = doc[page_index]
    found: list[EditObject] = []
    seen: set[str] = set()
    try:
        annotations = list(page.annots() or [])
    except Exception:
        annotations = []
    for annot in annotations:
        meta = get_object_meta(doc, annot.xref)
        if meta and meta.get("kind") == TEXT_KIND:
            obj = EditObject.from_meta(meta, annot_xref=annot.xref)
            if obj.oid not in seen:
                found.append(obj)
                seen.add(obj.oid)
    try:
        images = page.get_images(full=True) or []
    except Exception:
        images = []
    for image in images:
        xref = int(image[0])
        meta = get_object_meta(doc, xref)
        if meta and meta.get("kind") in (SIGNATURE_KIND, IMAGE_KIND):
            obj = EditObject.from_meta(
                meta, xref=xref, image_png=_image_bytes(doc, xref)
            )
            if obj.oid not in seen:
                found.append(obj)
                seen.add(obj.oid)
    return found


def list_objects(doc: fitz.Document) -> list[EditObject]:
    """Return every OpenReader-created editable object in the document."""
    objects: list[EditObject] = []
    for page_index in range(doc.page_count):
        objects.extend(_objects_on_page(doc, page_index))
    objects.sort(key=lambda o: (o.page_index, o.z, o.oid))
    return objects


def remove_object(doc: fitz.Document, obj: EditObject) -> None:
    obj = obj.normalized()
    if obj.kind == TEXT_KIND:
        page = doc[obj.page_index]
        target = None
        try:
            for annot in page.annots() or []:
                if annot.xref == obj.annot_xref or get_object_meta(doc, annot.xref):
                    meta = get_object_meta(doc, annot.xref)
                    if meta and meta.get("oid") == obj.oid:
                        target = annot
                        break
        except Exception:
            target = None
        if target is not None:
            try:
                page.delete_annot(target)
            except Exception:
                pass
        return
    if obj.xref:
        page = doc[obj.page_index]
        try:
            page.delete_image(obj.xref)
        except Exception:
            pass


def clear_objects(doc: fitz.Document) -> None:
    for obj in list_objects(doc):
        remove_object(doc, obj)


def apply_objects(doc: fitz.Document, objects: Iterable[EditObject]) -> list[EditObject]:
    """Replace all OpenReader objects with ``objects`` (used by undo/redo)."""
    clear_objects(doc)
    applied: list[EditObject] = []
    ordered = sorted(
        (o.copy() for o in objects),
        key=lambda o: (o.page_index, o.z, o.oid),
    )
    for obj in ordered:
        try:
            applied.append(add_object(doc, obj))
        except Exception:
            continue  # one bad object must not block the rest
    return applied


def snapshot(doc: fitz.Document) -> list[EditObject]:
    return [obj.copy() for obj in list_objects(doc)]


# ---------------------------------------------------------------------------
# Document safety
# ---------------------------------------------------------------------------


def document_has_signatures(doc: fitz.Document) -> bool:
    """Return True when the document contains a digital signature field."""
    try:
        for page in doc:
            for widget in page.widgets() or []:
                if int(getattr(widget, "field_type", -1)) == int(
                    getattr(fitz, "PDF_WIDGET_TYPE_SIGNATURE", 8)
                ):
                    return True
    except Exception:
        pass
    try:
        for page in doc:
            for annot in page.annots() or []:
                try:
                    kind, value = doc.xref_get_key(annot.xref, "FT")
                except Exception:
                    continue
                if kind == "name" and value == "/Sig":
                    return True
    except Exception:
        pass
    return False


def document_allows_editing(
    doc: fitz.Document, *, encrypted: bool | None = None
) -> bool:
    """Conservative editability check.

    Encrypted documents are treated as read-only.  PyMuPDF 1.28 corrupts its
    decryption state when encryption properties are inspected after
    ``authenticate()``, so callers that may have authenticated must pass the
    ``encrypted`` flag captured at open time; without it, only the pre-auth
    state is read.
    """
    if doc is None or getattr(doc, "is_closed", False):
        return False
    if encrypted is not None:
        return not encrypted
    try:
        if doc.needs_pass or doc.is_encrypted:
            return False
    except Exception:
        return False
    return True


def page_allows_editing(page: fitz.Page) -> bool:
    try:
        return int(page.rotation or 0) % 360 == 0
    except Exception:
        return True


# ---------------------------------------------------------------------------
# Saving
# ---------------------------------------------------------------------------


def _atomic_write(doc: fitz.Document, target: Path) -> None:
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.stem}-", suffix=".tmp", dir=str(target.parent)
    )
    os.close(fd)
    try:
        # KEEP is also correct for unencrypted documents: PyMuPDF writes them
        # unencrypted.  For encrypted documents it preserves the encryption
        # dictionary and passwords even after the user has authenticated
        # (``is_encrypted`` becomes False after authentication).
        encryption = int(getattr(fitz, "PDF_ENCRYPT_KEEP", 2))
        doc.save(
            tmp_name,
            garbage=3,
            deflate=True,
            encryption=encryption,
        )
        os.replace(tmp_name, target)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def save_document(doc: fitz.Document, target: str | Path) -> None:
    """Atomically write the document to ``target``."""
    _atomic_write(doc, Path(target))


def export_flattened(doc: fitz.Document, target: str | Path) -> None:
    """Write a flattened copy with annotations/widgets baked into content.

    The original document object is not modified.
    """
    target = Path(target)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".openreader-flat-", suffix=".pdf", dir=str(target.parent)
    )
    os.close(fd)
    try:
        doc.save(tmp_name, garbage=1, deflate=True)
        copy_doc = fitz.open(tmp_name)
        try:
            copy_doc.bake(annots=True, widgets=True)
            _atomic_write(copy_doc, target)
        finally:
            copy_doc.close()
    finally:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Image helpers (Qt-free; used by tests and the controller)
# ---------------------------------------------------------------------------


def png_from_bytes(data: bytes) -> bytes:
    """Normalize arbitrary image bytes to PNG when Pillow is available."""
    try:
        from PIL import Image
        import io

        with Image.open(io.BytesIO(data)) as image:
            buffer = io.BytesIO()
            image.save(buffer, "PNG")
            return buffer.getvalue()
    except Exception:
        return data


def rotated_png(png_bytes: bytes, angle: int) -> bytes:
    """Rotate a PNG by an arbitrary angle, expanding the canvas."""
    from PIL import Image
    import io

    with Image.open(io.BytesIO(png_bytes)) as image:
        rotated = image.convert("RGBA").rotate(
            -int(angle or 0) % 360, expand=True, resample=Image.Resampling.BICUBIC
        )
        buffer = io.BytesIO()
        rotated.save(buffer, "PNG")
        return buffer.getvalue()


def aspect_size(width: float, image_png: bytes) -> float:
    try:
        from PIL import Image
        import io

        with Image.open(io.BytesIO(image_png)) as image:
            w, h = image.size
        if w:
            return max(1.0, width * h / w)
    except Exception:
        pass
    return max(1.0, width * 0.35)


def base64_image(png_bytes: bytes) -> str:
    """Optional helper for embedding image data in JSON (tests/debugging)."""
    return base64.b64encode(png_bytes).decode("ascii")
