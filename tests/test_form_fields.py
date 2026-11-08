"""Tests for pdfreader_lib.form_fields (Phase 2 — PDF Form Intelligence).

Covers the shared form module used by both the GUI and the MCP server:
field enumeration/normalization, radio grouping, value read/write round-trips,
incremental-save persistence, type detection (explicit vs inferred), advisory
validation, and the local form-state store.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import fitz
import pytest

from pdfreader_lib import form_fields as ff

from tests._form_fixtures import make_form_fixture

# Ensure fixtures land in a temp dir (tests should not write to the repo).
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "form_test.pdf"


@pytest.fixture(scope="module")
def form_doc():
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    make_form_fixture(str(FIXTURE_PATH))
    doc = fitz.open(str(FIXTURE_PATH))
    yield doc
    doc.close()
    FIXTURE_PATH.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# v1.3.0 — enumeration & normalization
# ---------------------------------------------------------------------------


def test_build_index_types(form_doc):
    fields = ff.build_field_index(form_doc)
    by_name = {f.name: f for f in fields}
    assert by_name["fullname"].field_type == ff.FieldType.TEXT
    assert by_name["comments"].field_type == ff.FieldType.MULTILINE
    assert by_name["agree"].field_type == ff.FieldType.CHECKBOX
    assert by_name["gender"].field_type == ff.FieldType.RADIO
    assert by_name["country"].field_type == ff.FieldType.COMBO
    assert by_name["tags"].field_type == ff.FieldType.LISTBOX


def test_flags_are_mapped(form_doc):
    by_name = {f.name: f for f in ff.build_field_index(form_doc)}
    assert by_name["ref"].readonly is True
    assert by_name["phone"].required is True
    assert by_name["comments"].multiline is True
    assert by_name["pin"].password is True
    assert by_name["fullname"].max_length == 40
    assert by_name["country"].choices == ["US", "CA", "UK"]


def test_radio_group_is_collapsed(form_doc):
    fields = ff.build_field_index(form_doc)
    radios = [f for f in fields if f.field_type == ff.FieldType.RADIO]
    assert len(radios) == 1
    radio = radios[0]
    assert radio.name == "gender"
    assert radio.choices == ["M", "F"]
    assert radio.value == "F"


def test_has_form_fields(form_doc):
    assert ff.has_form_fields(form_doc) is True
    empty = fitz.open()
    empty.new_page()
    assert ff.has_form_fields(empty) is False
    empty.close()


def test_readonly_field_not_editable(form_doc):
    field = ff.field_by_name(ff.build_field_index(form_doc), "ref")
    assert field.readonly
    assert field.is_editable() is False


# ---------------------------------------------------------------------------
# v1.3.0 — value read / write round-trips
# ---------------------------------------------------------------------------


def test_set_get_roundtrip(form_doc):
    fields = ff.build_field_index(form_doc)
    cases = {
        "fullname": "Alice Smith",
        "comments": "Multi\nline\ntext",
        "agree": True,
        "country": "UK",
        "tags": "c",
        "gender": "M",
    }
    for name, value in cases.items():
        field = ff.field_by_name(fields, name)
        assert ff.set_field_value(form_doc, field, value) is True
        assert ff.get_field_value(form_doc, field) == value


def test_checkbox_toggle_off(form_doc):
    field = ff.field_by_name(ff.build_field_index(form_doc), "agree")
    assert ff.set_field_value(form_doc, field, False) is True
    assert ff.get_field_value(form_doc, field) is False


def test_radio_clear(form_doc):
    field = ff.field_by_name(ff.build_field_index(form_doc), "gender")
    assert ff.set_field_value(form_doc, field, "M") is True
    assert ff.set_field_value(form_doc, field, "") is True
    assert ff.get_field_value(form_doc, field) == ""


def test_readonly_write_refused(form_doc):
    field = ff.field_by_name(ff.build_field_index(form_doc), "ref")
    assert ff.set_field_value(form_doc, field, "HACK") is False
    assert ff.get_field_value(form_doc, field) == ""


def test_max_length_truncated(form_doc):
    field = ff.field_by_name(ff.build_field_index(form_doc), "fullname")
    assert ff.set_field_value(form_doc, field, "x" * 100) is True
    assert len(ff.get_field_value(form_doc, field)) == 40


def test_invalid_choice_refused(form_doc):
    field = ff.field_by_name(ff.build_field_index(form_doc), "country")
    assert ff.set_field_value(form_doc, field, "NotAChoice") is False


def test_incremental_save_persists_values(tmp_path):
    src = tmp_path / "form_inc.pdf"
    make_form_fixture(str(src))
    doc = fitz.open(str(src))
    fields = ff.build_field_index(doc)
    for name, value in {
        "fullname": "Alice Smith",
        "agree": True,
        "gender": "M",
        "country": "CA",
    }.items():
        assert ff.set_field_value(doc, ff.field_by_name(fields, name), value) is True
    doc.save(str(src), incremental=True, encryption=0)
    doc.close()

    # Reopen — values must be present and re-readable.
    doc = fitz.open(str(src))
    fields = ff.build_field_index(doc)
    assert ff.get_field_value(doc, ff.field_by_name(fields, "fullname")) == "Alice Smith"
    assert ff.get_field_value(doc, ff.field_by_name(fields, "agree")) is True
    assert ff.get_field_value(doc, ff.field_by_name(fields, "gender")) == "M"
    assert ff.get_field_value(doc, ff.field_by_name(fields, "country")) == "CA"
    doc.close()


# ---------------------------------------------------------------------------
# v1.3.1 — type detection (explicit vs inferred)
# ---------------------------------------------------------------------------


def _field(**kwargs) -> ff.FormField:
    return ff.FormField(name=kwargs.pop("name", "field"), page_index=0, **kwargs)


def test_explicit_type_from_format():
    field = _field(name="some_value", text_format=fitz.PDF_WIDGET_TX_FORMAT_DATE)
    ff.FormTypeDetector().detect(field)
    assert field.explicit_type == ff.TYPE_DATE
    assert field.detected_type == ff.TYPE_DATE
    assert field.is_inferred is False


def test_explicit_type_wins_over_inference():
    field = _field(name="dob", text_format=fitz.PDF_WIDGET_TX_FORMAT_NUMBER)
    ff.FormTypeDetector().detect(field)
    assert field.detected_type == ff.TYPE_NUMERIC
    assert field.explicit_type == ff.TYPE_NUMERIC
    assert field.is_inferred is False


def test_inferred_from_name():
    cases = {
        "dob": ff.TYPE_DATE,
        "home_phone": ff.TYPE_PHONE,
        "postalCode": ff.TYPE_ZIP,
        "email_address": ff.TYPE_EMAIL,
        "total_amount": ff.TYPE_CURRENCY,
        "quantity": ff.TYPE_NUMERIC,
    }
    for name, expected in cases.items():
        field = _field(name=name)
        ff.FormTypeDetector().detect(field)
        assert field.inferred_type == expected, name
        assert field.detected_type == expected
        assert field.is_inferred is True


def test_inferred_from_label_text():
    field = _field(name="field_7")
    ff.FormTypeDetector().detect(field, label_text="Date of Birth:")
    assert field.inferred_type == ff.TYPE_DATE
    assert field.is_inferred is True


def test_no_detection_for_plain_field():
    field = _field(name="notes")
    ff.FormTypeDetector().detect(field, label_text="")
    assert field.detected_type is None
    assert field.is_inferred is False


def test_annotate_field_types_uses_nearby_labels(form_doc):
    fields = ff.build_field_index(form_doc)
    ff.annotate_field_types(fields, form_doc)
    by_name = {f.name: f for f in fields}
    assert by_name["dob"].detected_type == ff.TYPE_DATE


# ---------------------------------------------------------------------------
# v1.3.1 — validation (advisory, international-tolerant)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ftype,value,expected_ok",
    [
        (ff.TYPE_DATE, "2026-08-03", True),
        (ff.TYPE_DATE, "03/08/2026", True),
        (ff.TYPE_DATE, "3 Aug 2026", True),
        (ff.TYPE_DATE, "not-a-date", False),
        (ff.TYPE_TIME, "14:30", True),
        (ff.TYPE_TIME, "2:30 PM", True),
        (ff.TYPE_TIME, "late afternoon", False),
        (ff.TYPE_PHONE, "+1 555 123 4567", True),
        (ff.TYPE_PHONE, "020 7946 0958", True),
        (ff.TYPE_PHONE, "(212) 555-0199", True),
        (ff.TYPE_PHONE, "123", False),
        (ff.TYPE_ZIP, "90210", True),
        (ff.TYPE_ZIP, "SW1A 1AA", True),
        (ff.TYPE_ZIP, "12", False),
        (ff.TYPE_EMAIL, "name@example.com", True),
        (ff.TYPE_EMAIL, "not-an-email", False),
        (ff.TYPE_CURRENCY, "$1,234.56", True),
        (ff.TYPE_CURRENCY, "€99", True),
        (ff.TYPE_CURRENCY, "free", False),
        (ff.TYPE_NUMERIC, "-12.5", True),
        (ff.TYPE_NUMERIC, "3,000", True),
        (ff.TYPE_NUMERIC, "twelve", False),
        (None, "anything", True),  # no detected type -> always ok
    ],
)
def test_validator_rules(ftype, value, expected_ok):
    ok, message = ff.FormValidator.validate(_field(detected_type=ftype), value)
    assert ok is expected_ok, message


def test_validation_never_blocks_editing(form_doc):
    field = ff.field_by_name(ff.build_field_index(form_doc), "dob")
    assert field.is_editable() is True
    # An inferred date field still accepts any text.
    assert ff.set_field_value(form_doc, field, "ordinary text") is True


# ---------------------------------------------------------------------------
# v1.3.2 — form state store
# ---------------------------------------------------------------------------


def test_state_store_roundtrip(tmp_path):
    store = ff.FormStateStore(tmp_path)
    path = tmp_path / "doc.pdf"
    store.save(path, {"fullname": "Alice", "agree": True}, {"dob": ff.TYPE_DATE})
    data = store.load(path)
    assert data["values"] == {"fullname": "Alice", "agree": True}
    assert data["overrides"] == {"dob": ff.TYPE_DATE}
    assert store.has_state(path) is True


def test_state_store_isolation(tmp_path):
    store = ff.FormStateStore(tmp_path)
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    store.save(a, {"x": "1"})
    store.save(b, {"y": "2"})
    assert store.load(a)["values"] == {"x": "1"}
    assert store.load(b)["values"] == {"y": "2"}
    store.clear(a)
    assert store.has_state(a) is False
    assert store.has_state(b) is True


def test_checkbox_string_boolean_coercion(form_doc):
    """Agents may pass "true"/"false" strings — they must coerce correctly."""
    field = ff.field_by_name(ff.build_field_index(form_doc), "agree")
    assert ff.set_field_value(form_doc, field, "true") is True
    assert ff.get_field_value(form_doc, field) is True
    assert ff.set_field_value(form_doc, field, "false") is True
    assert ff.get_field_value(form_doc, field) is False
    assert ff.set_field_value(form_doc, field, "off") is True
    assert ff.get_field_value(form_doc, field) is False
