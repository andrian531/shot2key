"""Local character & costume database stored under ``data/characters``."""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config

_LOCK = threading.RLock()
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
ALLOWED_IMAGE_EXTS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg", ".webp"})


class CharacterNotFound(KeyError):
    """Raised when a character id does not exist."""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_id(prefix: str = "char") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _index_path() -> Path:
    return config.get_characters_dir() / "characters.json"


def _images_dir() -> Path:
    return config.get_characters_dir() / "images"


def _read_all() -> list[dict[str, Any]]:
    path = _index_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _write_all(items: list[dict[str, Any]]) -> None:
    path = _index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _normalize_costumes(costumes: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for item in costumes or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        desc = str(item.get("description") or "").strip()
        if not name and not desc:
            continue
        cid = str(item.get("id") or "").strip() or _new_id("cos")
        result.append({"id": cid, "name": name or "Default", "description": desc})
    return result


def list_characters() -> list[dict[str, Any]]:
    with _LOCK:
        return _read_all()


def get_character(char_id: str) -> dict[str, Any]:
    if not _ID_RE.match(char_id or ""):
        raise CharacterNotFound(char_id)
    with _LOCK:
        for item in _read_all():
            if item.get("id") == char_id:
                return item
    raise CharacterNotFound(char_id)


def create_character(
    name: str,
    appearance: str = "",
    costumes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Nama karakter wajib diisi.")
    now = _utcnow()
    item = {
        "id": _new_id("char"),
        "name": clean_name,
        "appearance": appearance.strip(),
        "reference_image": None,
        "costumes": _normalize_costumes(costumes),
        "created_at": now,
        "updated_at": now,
    }
    with _LOCK:
        items = _read_all()
        items.append(item)
        _write_all(items)
    return item


def update_character(
    char_id: str,
    name: str | None = None,
    appearance: str | None = None,
    costumes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    with _LOCK:
        items = _read_all()
        for item in items:
            if item.get("id") == char_id:
                if name is not None and name.strip():
                    item["name"] = name.strip()
                if appearance is not None:
                    item["appearance"] = appearance.strip()
                if costumes is not None:
                    item["costumes"] = _normalize_costumes(costumes)
                item["updated_at"] = _utcnow()
                _write_all(items)
                return item
    raise CharacterNotFound(char_id)


def set_reference_image(char_id: str, suffix: str, content: bytes) -> dict[str, Any]:
    ext = suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        raise ValueError(f"Format gambar {ext} tidak didukung.")
    with _LOCK:
        items = _read_all()
        for item in items:
            if item.get("id") == char_id:
                old = item.get("reference_image")
                if old:
                    Path(old).unlink(missing_ok=True)
                img_dir = _images_dir()
                img_dir.mkdir(parents=True, exist_ok=True)
                dest = img_dir / f"{char_id}{ext}"
                dest.write_bytes(content)
                item["reference_image"] = str(dest)
                item["updated_at"] = _utcnow()
                _write_all(items)
                return item
    raise CharacterNotFound(char_id)


def delete_character(char_id: str) -> None:
    with _LOCK:
        items = _read_all()
        kept: list[dict[str, Any]] = []
        found = False
        for item in items:
            if item.get("id") == char_id:
                found = True
                old = item.get("reference_image")
                if old:
                    Path(old).unlink(missing_ok=True)
            else:
                kept.append(item)
        if not found:
            raise CharacterNotFound(char_id)
        _write_all(kept)
