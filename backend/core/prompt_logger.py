"""Structured prompt/response log, one JSONL file per project.

Every Analyze and Generate call appends one line so the exact prompt that was
sent, the images it referenced and the raw answer can be inspected later from
the UI (``GET /api/projects/{id}/logs``). Files live under ``data/logs`` which
is already git-ignored.
"""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config

_LOCK = threading.RLock()
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

#: Keep the log readable: a runaway agent answer must not bloat the file.
MAX_TEXT = 20000


class LogError(ValueError):
    """Raised for an invalid project id."""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def logs_dir() -> Path:
    return config.get_data_dir() / "logs"


def log_path(project_id: str) -> Path:
    if not _ID_RE.match(project_id or ""):
        raise LogError(f"project id tidak valid: {project_id!r}")
    return logs_dir() / f"{project_id}.jsonl"


def _clip(value: Any) -> Any:
    if isinstance(value, str) and len(value) > MAX_TEXT:
        return value[:MAX_TEXT] + f"... [truncated {len(value) - MAX_TEXT} chars]"
    return value


def log_event(
    project_id: str,
    scene_id: str | None,
    action: str,
    engine: str,
    prompt_sent: str = "",
    raw_response: str = "",
    input_images: list[str] | None = None,
    parsed: dict[str, Any] | None = None,
    duration_ms: int = 0,
    status: str = "ok",
    error: str | None = None,
    model: str | None = None,
    fallback_from: str | None = None,
) -> dict[str, Any]:
    """Append one event to the project's JSONL log and return it."""
    entry = {
        "timestamp": _utcnow(),
        "scene_id": scene_id,
        "action": action,
        "engine": engine,
        "model": model,
        "fallback_from": fallback_from,
        "input_images": list(input_images or []),
        "prompt_sent": _clip(prompt_sent or ""),
        "raw_response": _clip(raw_response or ""),
        "parsed": parsed,
        "duration_ms": int(duration_ms),
        "status": status,
        "error": error,
    }
    path = log_path(project_id)
    line = json.dumps(entry, ensure_ascii=False)
    with _LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    return entry


def read_logs(project_id: str, limit: int = 200) -> list[dict[str, Any]]:
    """Newest first, at most ``limit`` entries."""
    path = log_path(project_id)
    if not path.is_file():
        return []
    entries: list[dict[str, Any]] = []
    with _LOCK:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict):
                    entries.append(item)
    entries.reverse()
    return entries[: max(1, int(limit))]


def clear_logs(project_id: str) -> None:
    """Drop the project's log file (used when a project is deleted)."""
    path = log_path(project_id)
    with _LOCK:
        path.unlink(missing_ok=True)
