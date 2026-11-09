"""Tests for the local-only signature library."""

from __future__ import annotations

import io

from PIL import Image

from pdfreader_lib.signature_store import SignatureStore


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", (40, 20), (10, 20, 30, 255)).save(buffer, "PNG")
    return buffer.getvalue()


def test_save_list_load_delete(tmp_path):
    store = SignatureStore(tmp_path)
    entry = store.save("Sparsh", _png(), kind="typed")
    assert entry.name == "Sparsh"
    assert entry.kind == "typed"
    assert entry.path.exists()
    assert entry.load()[:8] == b"\x89PNG\r\n\x1a\n"

    entries = store.list()
    assert len(entries) == 1
    assert entries[0].id == entry.id
    assert store.load(entry.id) == entry.load()

    store.delete(entry.id)
    assert store.list() == []
    assert not entry.path.exists()


def test_clear_and_count(tmp_path):
    store = SignatureStore(tmp_path)
    store.save("One", _png())
    store.save("Two", _png())
    assert store.count() == 2
    store.clear()
    assert store.count() == 0
    assert list(tmp_path.glob("*.png")) == []


def test_empty_signature_rejected(tmp_path):
    store = SignatureStore(tmp_path)
    try:
        store.save("Bad", b"")
    except ValueError:
        pass
    else:
        raise AssertionError("empty signature should be rejected")


def test_missing_index_degrades_gracefully(tmp_path):
    store = SignatureStore(tmp_path)
    (tmp_path / "signatures.json").write_text("not json", encoding="utf-8")
    assert store.list() == []
    entry = store.save("Recovered", _png())
    assert store.list()[0].id == entry.id


def test_path_traversal_id_is_sanitized(tmp_path):
    store = SignatureStore(tmp_path)
    entry = store.save("Safe", _png())
    # Unknown/traversal ids never resolve outside the store directory.
    try:
        store.load("../../etc/passwd")
    except FileNotFoundError:
        pass
    store.delete("../../etc/passwd")
    assert store.count() == 1
    assert entry.path.exists()
