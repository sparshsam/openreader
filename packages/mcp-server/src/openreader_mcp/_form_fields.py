"""AcroForm field intelligence — shared by the GUI and the MCP server.

Pure-logic module: it must never import PySide6 so it can run inside the
standalone MCP server process and be unit-tested without a Qt platform.

Responsibilities
---------------
* v1.3.0 — enumerate AcroForm widgets into a normalized ``FormField`` model,
  read and write field values (including radio groups / checkboxes / choices),
  respect read-only and max-length rules.
* v1.3.1 — infer and validate field types (date, phone, ZIP, email, currency,
  numeric) from PDF formatting rules, field names and nearby labels. Inference
  is advisory and is never presented as certainty.
* v1.3.2 — ``FormStateStore`` persists unsaved form values and user type
  overrides to local JSON for autosave / crash recovery.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import fitz


# ---------------------------------------------------------------------------
# Normalized field types
# ---------------------------------------------------------------------------


class FieldType:
    """Normalized AcroForm field types (independent of PyMuPDF constants)."""

    TEXT = "text"
    MULTILINE = "multiline"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    COMBO = "combo"
    LISTBOX = "listbox"
    SIGNATURE = "signature"
    PUSHBUTTON = "button"
    UNKNOWN = "unknown"


EDITABLE_TYPES = {
    FieldType.TEXT,
    FieldType.MULTILINE,
    FieldType.CHECKBOX,
    FieldType.RADIO,
    FieldType.COMBO,
    FieldType.LISTBOX,
}

# Detected "field intelligence" types used for affordances + validation.
TYPE_DATE = "date"
TYPE_TIME = "time"
TYPE_PHONE = "phone"
TYPE_ZIP = "zip"
TYPE_EMAIL = "email"
TYPE_CURRENCY = "currency"
TYPE_NUMERIC = "numeric"

# ---------------------------------------------------------------------------
# Widget flag bits (PDF spec — ISO 32000 Ff entries)
# ---------------------------------------------------------------------------

FLAG_READONLY = 0x1
FLAG_REQUIRED = 0x2
FLAG_NO_EXPORT = 0x4
FLAG_MULTILINE = 0x1000
FLAG_PASSWORD = 0x2000
FLAG_NO_TOGGLE_TO_OFF = 0x4000
FLAG_RADIO = 0x8000
FLAG_PUSHBUTTON = 0x10000
FLAG_COMBO = 0x20000
FLAG_EDIT = 0x40000
FLAG_COMB = 0x100000
FLAG_MULTISELECT = 0x200000

# PyMuPDF text_format values → explicit detected types.
_EXPLICIT_BY_TEXT_FORMAT = {
    fitz.PDF_WIDGET_TX_FORMAT_DATE: TYPE_DATE,     # 3
    fitz.PDF_WIDGET_TX_FORMAT_TIME: TYPE_TIME,     # 4
    fitz.PDF_WIDGET_TX_FORMAT_NUMBER: TYPE_NUMERIC,  # 1
}


# ---------------------------------------------------------------------------
# FormField model
# ---------------------------------------------------------------------------


@dataclass
class FormField:
    """Normalized, defensive view of one AcroForm field."""

    name: str
    page_index: int
    rect: tuple = (0.0, 0.0, 0.0, 0.0)  # PDF points (x0, y0, x1, y1)
    field_type: str = FieldType.TEXT
    # Display label (from /TU) when present, else the field name.
    label: str = ""

    # Field rules
    readonly: bool = False
    required: bool = False
    multiline: bool = False
    password: bool = False
    comb: bool = False
    max_length: int = 0
    hidden: bool = False

    # Choice fields
    editable_choice: bool = False
    choices: list = field(default_factory=list)

    # Button widgets
    button_caption: Optional[str] = None
    on_state: str = "Yes"
    radio_group_xref: int = -1
    # Parallel to ``choices``: the PDF rect of each radio option (for overlays).
    option_rects: list = field(default_factory=list)

    # Formatting
    text_format: int = 0

    # Current value in the normalized model:
    #   text/multiline/combo/listbox → str
    #   checkbox → bool
    #   radio    → str (selected option caption/on-state) or ""
    value: object = ""

    # Type intelligence (v1.3.1)
    explicit_type: Optional[str] = None
    inferred_type: Optional[str] = None
    detected_type: Optional[str] = None
    type_confidence: float = 0.0
    is_inferred: bool = False
    validation_message: str = ""

    # Back-reference used to find the live widget(s) when writing.
    widget_xref: int = -1

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        """Serializable dict for the MCP server / tool output."""
        return {
            "name": self.name,
            "label": self.label,
            "page": self.page_index + 1,
            "page_index": self.page_index,
            "rect": [round(v, 2) for v in self.rect],
            "type": self.field_type,
            "detected_type": self.detected_type,
            "explicit_type": self.explicit_type,
            "inferred_type": self.inferred_type,
            "is_inferred": self.is_inferred,
            "type_confidence": round(self.type_confidence, 2),
            "readonly": self.readonly,
            "required": self.required,
            "max_length": self.max_length,
            "password": self.password,
            "choices": list(self.choices),
            "option_rects": [[round(v, 2) for v in r] for r in self.option_rects],
            "value": self.value,
            "validation_message": self.validation_message,
        }

    def is_editable(self) -> bool:
        return self.field_type in EDITABLE_TYPES and not self.readonly and not self.hidden

    def display_name(self) -> str:
        return self.label or self.name or "(unnamed field)"


# ---------------------------------------------------------------------------
# Widget → FormField mapping helpers
# ---------------------------------------------------------------------------


def _normalize_type(widget) -> str:
    wtype = widget.field_type
    if wtype == fitz.PDF_WIDGET_TYPE_TEXT:
        return FieldType.MULTILINE if (widget.field_flags & FLAG_MULTILINE) else FieldType.TEXT
    if wtype == fitz.PDF_WIDGET_TYPE_CHECKBOX:
        return FieldType.CHECKBOX
    if wtype == fitz.PDF_WIDGET_TYPE_COMBOBOX:
        return FieldType.COMBO
    if wtype == fitz.PDF_WIDGET_TYPE_LISTBOX:
        return FieldType.LISTBOX
    if wtype == fitz.PDF_WIDGET_TYPE_RADIOBUTTON:
        return FieldType.RADIO
    if wtype == fitz.PDF_WIDGET_TYPE_SIGNATURE:
        return FieldType.SIGNATURE
    if wtype == fitz.PDF_WIDGET_TYPE_BUTTON:
        return FieldType.PUSHBUTTON
    return FieldType.UNKNOWN


def _safe_on_state(widget) -> str:
    """On-state name of a checkbox/radio widget, defaulting to 'Yes'."""
    try:
        state = widget.on_state()
        if isinstance(state, str) and state:
            return state
        if state is True:
            return "Yes"
    except Exception:
        pass
    return "Yes"


def _clean_field_name(widget, page_index: int) -> str:
    name = getattr(widget, "field_name", None)
    if name:
        return name
    return f"field_{page_index}_{widget.xref}"


def _widget_value(widget):
    """Normalized current value of a non-grouped widget."""
    value = widget.field_value
    if value is None:
        return ""
    if widget.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
        return str(value) != "Off" and bool(value)
    return str(value)


def _from_widget(widget, page_index: int) -> FormField:
    flags = widget.field_flags
    field_type = _normalize_type(widget)
    name = _clean_field_name(widget, page_index)
    label = getattr(widget, "field_label", None) or name
    rect = (widget.rect.x0, widget.rect.y0, widget.rect.x1, widget.rect.y1)
    text_format = int(getattr(widget, "text_format", 0) or 0)
    return FormField(
        name=name,
        page_index=page_index,
        rect=rect,
        field_type=field_type,
        label=label,
        readonly=bool(flags & FLAG_READONLY),
        required=bool(flags & FLAG_REQUIRED),
        multiline=bool(flags & FLAG_MULTILINE),
        password=bool(flags & FLAG_PASSWORD),
        comb=bool(flags & FLAG_COMB),
        max_length=int(getattr(widget, "text_maxlen", 0) or 0),
        hidden=int(getattr(widget, "field_display", 0) or 0) == 1,
        editable_choice=bool(flags & FLAG_EDIT),
        choices=list(getattr(widget, "choice_values", None) or []),
        button_caption=getattr(widget, "button_caption", None),
        on_state=_safe_on_state(widget),
        radio_group_xref=int(getattr(widget, "rb_parent", None) or -1),
        text_format=text_format,
        value=_widget_value(widget),
        widget_xref=widget.xref,
    )


def _from_radio_group(kids, page_index: int) -> FormField:
    """Collapse the widgets of one radio group into a single FormField."""
    first = kids[0]
    flags = first.field_flags
    name = _clean_field_name(first, page_index)
    choices = []
    option_rects = []
    selected = ""
    for w in kids:
        on = _safe_on_state(w)
        caption = getattr(w, "button_caption", None) or on
        if caption not in choices:
            choices.append(caption)
            option_rects.append((w.rect.x0, w.rect.y0, w.rect.x1, w.rect.y1))
        value = w.field_value
        if value and str(value) != "Off":
            selected = caption
    rect = (first.rect.x0, first.rect.y0, first.rect.x1, first.rect.y1)
    return FormField(
        name=name,
        page_index=page_index,
        rect=rect,
        field_type=FieldType.RADIO,
        label=getattr(first, "field_label", None) or name,
        readonly=bool(flags & FLAG_READONLY),
        required=bool(flags & FLAG_REQUIRED),
        choices=choices,
        option_rects=option_rects,
        radio_group_xref=int(getattr(first, "rb_parent", None) or -1),
        value=selected,
        widget_xref=first.xref,
    )


# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------


def build_field_index(doc) -> list:
    """Enumerate every AcroForm field in a document.

    Radio button groups are collapsed into a single ``FormField`` per group
    (the widgets that share a ``/Parent``).
    """
    fields: list = []
    radio_groups: dict = {}  # rb_parent xref -> (page_index, [widgets])
    for page_index in range(doc.page_count):
        try:
            page = doc.load_page(page_index)
        except Exception:
            continue
        try:
            widgets = list(page.widgets())
        except Exception:
            widgets = []
        for w in widgets:
            if w.field_type == fitz.PDF_WIDGET_TYPE_RADIOBUTTON:
                rbp = int(getattr(w, "rb_parent", None) or -1)
                entry = radio_groups.setdefault(rbp, [page_index, []])
                entry[1].append(w)
            else:
                fields.append(_from_widget(w, page_index))
    for rbp, (page_index, kids) in radio_groups.items():
        fields.append(_from_radio_group(kids, page_index))
    fields.sort(key=lambda f: (f.page_index, f.rect[1], f.rect[0]))
    return fields


def form_field_count(doc) -> int:
    return len(build_field_index(doc))


def has_form_fields(doc) -> bool:
    for page_index in range(doc.page_count):
        try:
            page = doc.load_page(page_index)
        except Exception:
            continue
        try:
            if next(page.widgets(), None) is not None:
                return True
        except Exception:
            continue
    return False


def field_by_name(fields, name) -> Optional[FormField]:
    for f in fields:
        if f.name == name:
            return f
    return None


# ---------------------------------------------------------------------------
# Reading / writing values
# ---------------------------------------------------------------------------


def _widget_for_field(doc, field: FormField):
    """Return ``(page, widget)`` backing a (non-radio-group) FormField.

    The page is returned too so the caller keeps a strong reference — a Widget's
    annotation is bound to its page via a weakref, and PyMuPDF raises "Annot is
    not bound to a page" if the page is garbage-collected before ``update()``.
    """
    try:
        page = doc.load_page(field.page_index)
    except Exception:
        return None, None
    try:
        for w in page.widgets():
            if w.xref == field.widget_xref:
                return page, w
    except Exception:
        pass
    return None, None


def _iter_radio_kids(doc, group_xref: int):
    """Yield ``(page, widget)`` for every radio in a group."""
    for page_index in range(doc.page_count):
        try:
            page = doc.load_page(page_index)
        except Exception:
            continue
        try:
            for w in page.widgets():
                if int(getattr(w, "rb_parent", None) or -1) == group_xref:
                    yield page, w
        except Exception:
            continue


def get_field_value(doc, field: FormField):
    """Re-read the current value of a field straight from the PDF."""
    if field.field_type == FieldType.RADIO:
        for _page, w in _iter_radio_kids(doc, field.radio_group_xref):
            value = w.field_value
            if value and str(value) != "Off":
                on = _safe_on_state(w)
                return getattr(w, "button_caption", None) or on
        return ""
    _page, widget = _widget_for_field(doc, field)
    if widget is None:
        return field.value
    return _widget_value(widget)


def _as_bool(value) -> bool:
    """Coerce bool-ish values (agents may pass "true"/"false" strings)."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in ("", "0", "false", "off", "no")
    return bool(value)


def set_field_value(doc, field: FormField, value) -> bool:
    """Write ``value`` into the PDF for ``field``.

    Respects read-only rules and max lengths. Returns ``True`` on success.
    The value is stored via PyMuPDF's ``update()``, which regenerates the
    appearance stream so the value renders in any PDF viewer.
    """
    if not field.is_editable():
        return False
    if field.field_type == FieldType.RADIO:
        return _set_radio_value(doc, field, value)
    if field.field_type == FieldType.CHECKBOX:
        return _set_checkbox_value(doc, field, _as_bool(value))
    if field.field_type in (FieldType.COMBO, FieldType.LISTBOX):
        return _set_choice_value(doc, field, value)
    return _set_text_value(doc, field, value)


def _set_text_value(doc, field: FormField, value) -> bool:
    _page, widget = _widget_for_field(doc, field)
    if widget is None:
        return False
    text = str(value) if value is not None else ""
    maxlen = int(getattr(widget, "text_maxlen", 0) or 0)
    if maxlen > 0:
        text = text[:maxlen]
    try:
        widget.field_value = text
        widget.update()
    except Exception:
        return False
    return True


def _set_checkbox_value(doc, field: FormField, value) -> bool:
    _page, widget = _widget_for_field(doc, field)
    if widget is None:
        return False
    on = _safe_on_state(widget)
    try:
        widget.field_value = on if value else "Off"
        widget.update()
    except Exception:
        return False
    return True


def _set_choice_value(doc, field: FormField, value) -> bool:
    _page, widget = _widget_for_field(doc, field)
    if widget is None:
        return False
    text = str(value) if value is not None else ""
    choices = list(getattr(widget, "choice_values", None) or [])
    if text not in choices and not field.editable_choice:
        return False
    try:
        widget.field_value = text
        widget.update()
    except Exception:
        return False
    return True


def _set_radio_value(doc, field: FormField, value) -> bool:
    kids = list(_iter_radio_kids(doc, field.radio_group_xref))
    if not kids:
        return False
    text = str(value) if value is not None else ""
    target = None
    for _page, w in kids:
        caption = getattr(w, "button_caption", None) or _safe_on_state(w)
        if caption == text:
            target = w
            break
    # Turn every option off first — setting a radio to "" resets the group.
    for _page, w in kids:
        try:
            w.field_value = ""
            w.update()
        except Exception:
            continue
    if target is not None:
        try:
            target.field_value = _safe_on_state(target)
            target.update()
        except Exception:
            return False
    return True


# ---------------------------------------------------------------------------
# v1.3.1 — Field type intelligence
# ---------------------------------------------------------------------------


class FormTypeDetector:
    """Detect field types from formatting rules, names and nearby labels.

    Two tiers are always kept distinct:
      * ``explicit_type`` — authoritative, from the PDF's own formatting rule.
      * ``inferred_type`` — heuristic, from the field name / nearby label.
    Inference is advisory; callers must never present it as certainty.
    """

    # (regex, detected type, confidence)
    NAME_PATTERNS = [
        (re.compile(r"(?i)(^|[_\- .])(date|dob|birth|born|birthday)([_\- .]|$)"), TYPE_DATE, 0.9),
        (re.compile(r"(?i)(^|[_\- .])(ph|phone|tel|telephone|mobile|cell|fax)([_\- .]|$)"), TYPE_PHONE, 0.9),
        (re.compile(r"(?i)(^|[_\- .])(zip|postal|postcode|pincode)([_\- .]|$)"), TYPE_ZIP, 0.9),
        (re.compile(r"(?i)(^|[_\- .])(email|e-?mail)([_\- .]|$)"), TYPE_EMAIL, 0.95),
        (re.compile(r"(?i)(^|[_\- .])(amount|price|cost|fee|salary|total|balance|currency|payment)([_\- .]|$)"), TYPE_CURRENCY, 0.85),
        (re.compile(r"(?i)(^|[_\- .])(qty|quantity|count|number|num|age|year|weight|height)([_\- .]|$)"), TYPE_NUMERIC, 0.7),
    ]

    # Simple label fragment heuristics (word-ish matches), lower confidence.
    LABEL_PATTERNS = [
        (re.compile(r"(?i)\bdate\b|\bdob\b|\bbirth\b|\bborn\b"), TYPE_DATE, 0.6),
        (re.compile(r"(?i)\bphone\b|\btelephone\b|\bmobile\b|\bcell\b"), TYPE_PHONE, 0.6),
        (re.compile(r"(?i)\bzip\b|\bpostal\b|\bpostcode\b|\bpin\b"), TYPE_ZIP, 0.6),
        (re.compile(r"(?i)\bemail\b|\be-?mail\b"), TYPE_EMAIL, 0.7),
        (re.compile(r"(?i)\b(amount|price|cost|fee|salary|total|balance)\b|\$"), TYPE_CURRENCY, 0.6),
        (re.compile(r"(?i)\b(quantity|qty|count|age|year)\b"), TYPE_NUMERIC, 0.55),
    ]

    def detect(self, field: FormField, label_text: str = "") -> None:
        """Populate the explicit / inferred / detected type fields in place."""
        explicit = None
        if field.field_type in (FieldType.TEXT, FieldType.MULTILINE):
            explicit = _EXPLICIT_BY_TEXT_FORMAT.get(field.text_format)
        inferred = None
        confidence = 0.0
        # Normalize camelCase ("postalCode" -> "postal_Code") so word-boundary
        # patterns match common form naming conventions.
        normalized_name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", field.name or "")
        for regex, ftype, conf in self.NAME_PATTERNS:
            if regex.search(normalized_name):
                inferred, confidence = ftype, conf
                break
        if inferred is None and label_text:
            for regex, ftype, conf in self.LABEL_PATTERNS:
                if regex.search(label_text):
                    inferred, confidence = ftype, conf
                    break
        detected = explicit or inferred
        field.explicit_type = explicit
        field.inferred_type = inferred
        field.detected_type = detected
        field.type_confidence = confidence if detected == inferred else 1.0
        field.is_inferred = bool(inferred) and not explicit


def annotate_field_types(fields, doc) -> None:
    """Run the type detector over every field, pulling nearby labels from the PDF."""
    detector = FormTypeDetector()
    for f in fields:
        label_text = _nearby_label_text(doc, f) if f.field_type in (FieldType.TEXT, FieldType.MULTILINE) else ""
        detector.detect(f, label_text)


def _nearby_label_text(doc, field: FormField) -> str:
    """Best-effort label text to the left / above a text field."""
    try:
        page = doc.load_page(field.page_index)
        words = page.get_text("words")
    except Exception:
        return ""
    rx0, ry0, rx1, ry1 = field.rect
    collected = []
    for word in words:
        wx0, wy0, wx1, wy1, text, *_ = word
        # Left of the field on the same line band, or directly above it.
        left_of = wx1 <= rx0 + 2 and wy0 < ry1 and wy1 > ry0 - 6 and rx0 - wx1 < 220
        above = wy1 <= ry0 + 2 and wy1 >= ry0 - 40 and wx0 < rx1 and wx1 > rx0 - 60
        if left_of or above:
            collected.append(text)
    return " ".join(collected)


# ---------------------------------------------------------------------------
# v1.3.1 — Validation
# ---------------------------------------------------------------------------


class FormValidator:
    """Advisory, international-tolerant validation for detected field types.

    Validation never blocks input — it only produces a message the UI can
    surface. Values that do not match still save.
    """

    _EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    @classmethod
    def validate(cls, field: FormField, value) -> tuple:
        """Return ``(ok: bool, message: str)`` for ``value`` on ``field``."""
        text = str(value or "").strip()
        if not text or not field.detected_type:
            return True, ""
        rule = {
            TYPE_DATE: cls._validate_date,
            TYPE_TIME: cls._validate_time,
            TYPE_PHONE: cls._validate_phone,
            TYPE_ZIP: cls._validate_zip,
            TYPE_EMAIL: cls._validate_email,
            TYPE_CURRENCY: cls._validate_currency,
            TYPE_NUMERIC: cls._validate_numeric,
        }.get(field.detected_type)
        if rule is None:
            return True, ""
        return rule(text)

    # -- individual rules ------------------------------------------------

    @staticmethod
    def _validate_date(text: str) -> tuple:
        # Tolerates ISO, slash, dash, dotted and month-name dates.
        tokens = re.split(r"[-/., ]+", text.strip())
        if len(tokens) < 3:
            return False, "Expected a date like 2026-08-03."
        if not all(tok.isdigit() or tok[:1].isalpha() for tok in tokens):
            return False, "Expected a date like 2026-08-03."
        year = None
        for tok in tokens:
            if len(tok) == 4 and tok.isdigit():
                year = int(tok)
                break
        months = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }
        month_ok = any(tok.lower()[:3] in months for tok in tokens)
        day_ok = any(tok.isdigit() and 1 <= int(tok) <= 31 for tok in tokens)
        if year is not None and (month_ok or day_ok):
            return True, ""
        if month_ok and day_ok:
            return True, ""
        return False, "Expected a date like 2026-08-03."

    @staticmethod
    def _validate_time(text: str) -> tuple:
        if re.match(r"^\d{1,2}:\d{2}(:\d{2})?(\s*[AaPp][Mm])?$", text.strip()):
            return True, ""
        return False, "Expected a time like 14:30."

    @staticmethod
    def _validate_phone(text: str) -> tuple:
        digits = re.sub(r"[^\d]", "", text)
        if text.lstrip().startswith("+"):
            digits = digits.lstrip() or ""
        cleaned = re.sub(r"[\s\-()./]", "", text)
        if cleaned.startswith("+"):
            cleaned = cleaned[1:]
        if cleaned.isdigit() and 6 <= len(cleaned) <= 15:
            return True, ""
        return False, "Expected a phone number like +1 555 123 4567."

    @staticmethod
    def _validate_zip(text: str) -> tuple:
        cleaned = re.sub(r"[\s\-]", "", text)
        # International postal codes are alphanumeric and 3–10 characters.
        if cleaned.isalnum() and 3 <= len(cleaned) <= 10:
            return True, ""
        return False, "Expected a postal code (letters and digits)."

    @staticmethod
    def _validate_email(text: str) -> tuple:
        if FormValidator._EMAIL.match(text.strip()):
            return True, ""
        return False, "Expected an email address like name@example.com."

    @staticmethod
    def _validate_currency(text: str) -> tuple:
        cleaned = text.strip().replace(",", "")
        cleaned = re.sub(r"^[$£€₹¥]|[$£€₹¥]$", "", cleaned)
        if re.match(r"^\d+(\.\d{1,2})?$", cleaned) and cleaned.replace(".", "").isdigit():
            return True, ""
        return False, "Expected an amount like 1,234.56."

    @staticmethod
    def _validate_numeric(text: str) -> tuple:
        cleaned = text.strip().replace(",", "")
        if re.match(r"^[+-]?\d+(\.\d+)?$", cleaned):
            return True, ""
        return False, "Expected a number."


# ---------------------------------------------------------------------------
# v1.3.2 — Form state store (autosave / crash recovery / overrides)
# ---------------------------------------------------------------------------


class FormStateStore:
    """Persist unsaved form values and user type overrides to local JSON.

    Keyed by document path hash so form work survives app restarts. The GUI
    owns the file location; this class is deliberately dumb and Qt-free.
    """

    STATE_VERSION = 1
    FILE_PREFIX = "formstate_"

    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else None

    # -- key / path helpers ----------------------------------------------

    def _dir(self) -> Path:
        return self.base_dir

    @staticmethod
    def key_for_path(path) -> str:
        return hashlib.sha256(str(path).encode("utf-8")).hexdigest()

    def _file_for(self, path) -> Path:
        return self._dir() / f"{self.FILE_PREFIX}{self.key_for_path(path)}.json"

    # -- read / write ----------------------------------------------------

    def load(self, path) -> dict:
        try:
            data = json.loads(self._file_for(path).read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("version") == self.STATE_VERSION:
                return data
        except Exception:
            pass
        return {}

    def save(self, path, values: dict, overrides: Optional[dict] = None) -> None:
        data = {
            "version": self.STATE_VERSION,
            "values": values or {},
            "overrides": overrides or {},
        }
        try:
            self._dir().mkdir(parents=True, exist_ok=True)
            tmp = self._file_for(path).with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp.replace(self._file_for(path))
        except Exception:
            pass  # best-effort autosave must never crash the app

    def clear(self, path) -> None:
        try:
            self._file_for(path).unlink(missing_ok=True)
        except Exception:
            pass

    def has_state(self, path) -> bool:
        try:
            return self._file_for(path).exists()
        except Exception:
            return False
