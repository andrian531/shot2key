"""Project persistence: one JSON document per project under ``data/projects``.

A local single-user app does not need a database; JSON files keep the project
folder portable and make the export step trivial. All writes go through a lock
and an atomic replace so a crash mid-write cannot truncate a project.
"""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import config

_LOCK = threading.RLock()

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class ProjectNotFound(KeyError):
    """Raised when a project id does not exist on disk."""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"p_{stamp}_{uuid.uuid4().hex[:6]}"


def _path(project_id: str) -> Path:
    if not _ID_RE.match(project_id or ""):
        raise ProjectNotFound(project_id)
    return config.get_projects_dir() / f"{project_id}.json"


def _write(project: dict[str, Any]) -> None:
    path = _path(project["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def create(filename: str, video_path: str, size_bytes: int = 0) -> dict[str, Any]:
    """Create and persist a fresh project in the ``uploaded`` state."""
    project = {
        "id": new_id(),
        "filename": filename,
        "video_path": str(video_path),
        "size_bytes": size_bytes,
        "created_at": utcnow(),
        "updated_at": utcnow(),
        "status": "uploaded",
        "progress": {"stage": "uploaded", "percent": 0, "message": "Video tersimpan"},
        "error": None,
        "source": {},
        "shots": [],
        "scenes": [],
        "analysis": {"engine": None, "status": "idle", "error": None},
        "generation": {"engine": None, "status": "idle", "queued": 0, "done": 0, "failed": 0},
        "breakdown_dir": None,
        "subtitles": {},
    }
    with _LOCK:
        _write(project)
    return project


def load(project_id: str) -> dict[str, Any]:
    path = _path(project_id)
    if not path.is_file():
        raise ProjectNotFound(project_id)
    with _LOCK:
        return json.loads(path.read_text(encoding="utf-8"))


def save(project: dict[str, Any]) -> dict[str, Any]:
    project["updated_at"] = utcnow()
    with _LOCK:
        _write(project)
    return project


def mutate(project_id: str, fn: Callable[[dict[str, Any]], Any]) -> dict[str, Any]:
    """Read-modify-write under the lock; ``fn`` may return a value to ignore."""
    with _LOCK:
        project = load(project_id)
        fn(project)
        return save(project)


def update(project_id: str, **fields: Any) -> dict[str, Any]:
    def apply(project: dict[str, Any]) -> None:
        project.update(fields)

    return mutate(project_id, apply)


def set_progress(project_id: str, stage: str, percent: int, message: str = "") -> None:
    def apply(project: dict[str, Any]) -> None:
        project["progress"] = {
            "stage": stage,
            "percent": max(0, min(100, int(percent))),
            "message": message,
        }

    try:
        mutate(project_id, apply)
    except ProjectNotFound:
        pass


def list_projects() -> list[dict[str, Any]]:
    """Newest first, without the heavy scene payload."""
    directory = config.get_projects_dir()
    if not directory.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for path in directory.glob("*.json"):
        try:
            project = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        items.append(
            {
                "id": project.get("id"),
                "filename": project.get("filename"),
                "status": project.get("status"),
                "created_at": project.get("created_at"),
                "updated_at": project.get("updated_at"),
                "scene_count": len(project.get("scenes") or []),
                "duration": (project.get("source") or {}).get("duration"),
                "progress": project.get("progress"),
            }
        )
    items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return items


def delete(project_id: str) -> None:
    path = _path(project_id)
    with _LOCK:
        path.unlink(missing_ok=True)


def find_scene(project: dict[str, Any], scene_id: str) -> dict[str, Any] | None:
    for scene in project.get("scenes") or []:
        if scene.get("id") == scene_id:
            return scene
    return None
