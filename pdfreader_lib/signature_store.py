"""Local-only signature library for OpenReader.

Signatures are stored as PNG files plus a small JSON index in the app's
private data directory.  Nothing is uploaded; the store is entirely local and
can be cleared by the user at any time.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

INDEX_NAME = "signatures.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe_id(value: str) -> str:
    return "".join(ch for ch in str(value) if ch.isalnum() or ch in "-_") or uuid.uuid4().hex


@dataclass(frozen=True)
class SignatureEntry:
    id: str
    name: str
    kind: str
    created: str
    path: Path

    def load(self) -> bytes:
        return self.path.read_bytes()


class SignatureStore:
    """A small, atomic, local signature library."""

    def __init__(self, base_dir: str | Path | None = None):
        self.base_dir = Path(base_dir) if base_dir else (
            Path.home() / ".openreader" / "signatures"
        )
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.base_dir / INDEX_NAME

    # -- index ---------------------------------------------------------

    def _read_index(self) -> dict:
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _write_index(self, data: dict) -> None:
        fd, tmp_name = tempfile.mkstemp(
            prefix=".signatures-", suffix=".json", dir=str(self.base_dir)
        )
        os.close(fd)
        try:
            Path(tmp_name).write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            os.replace(tmp_name, self.index_path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    # -- public API ----------------------------------------------------

    def save(self, name: str, png_bytes: bytes, kind: str = "drawn") -> SignatureEntry:
        if not png_bytes:
            raise ValueError("signature image is empty")
        entry_id = uuid.uuid4().hex
        path = self.base_dir / f"{entry_id}.png"
        fd, tmp_name = tempfile.mkstemp(
            prefix=".sig-", suffix=".png", dir=str(self.base_dir)
        )
        os.close(fd)
        try:
            Path(tmp_name).write_bytes(png_bytes)
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
        created = _now()
        data = self._read_index()
        data[entry_id] = {
            "name": (name or "Signature").strip() or "Signature",
            "kind": kind,
            "created": created,
        }
        self._write_index(data)
        return SignatureEntry(entry_id, data[entry_id]["name"], kind, created, path)

    def list(self) -> list[SignatureEntry]:
        data = self._read_index()
        entries: list[SignatureEntry] = []
        for entry_id, meta in data.items():
            entry_id = _safe_id(entry_id)
            path = self.base_dir / f"{entry_id}.png"
            if not path.exists():
                continue
            entries.append(
                SignatureEntry(
                    id=entry_id,
                    name=str(meta.get("name", "Signature")),
                    kind=str(meta.get("kind", "drawn")),
                    created=str(meta.get("created", "")),
                    path=path,
                )
            )
        entries.sort(key=lambda e: e.created, reverse=True)
        return entries

    def load(self, entry_id: str) -> bytes:
        path = self.base_dir / f"{_safe_id(entry_id)}.png"
        if not path.exists():
            raise FileNotFoundError(entry_id)
        return path.read_bytes()

    def delete(self, entry_id: str) -> None:
        entry_id = _safe_id(entry_id)
        path = self.base_dir / f"{entry_id}.png"
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        data = self._read_index()
        if entry_id in data:
            data.pop(entry_id, None)
            self._write_index(data)

    def clear(self) -> None:
        for entry in self.list():
            try:
                entry.path.unlink()
            except OSError:
                pass
        self._write_index({})

    def count(self) -> int:
        return len(self.list())
