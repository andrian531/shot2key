"""Central configuration for the Shot2Key backend.

Every path is resolved here so tests can point the app at a throwaway data
directory (``SHOT2KEY_DATA_DIR``) without touching the real one.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

#: Root for project metadata, settings and job state.
DATA_DIR = Path(os.environ.get("SHOT2KEY_DATA_DIR") or (BASE_DIR / "data")).resolve()

#: Uploaded source videos (git-ignored).
UPLOADS_DIR = Path(os.environ.get("SHOT2KEY_UPLOADS_DIR") or (BASE_DIR / "uploads")).resolve()

#: Generated keyframes and rea-video breakdowns (git-ignored).
OUTPUTS_DIR = Path(os.environ.get("SHOT2KEY_OUTPUTS_DIR") or (BASE_DIR / "outputs")).resolve()

#: One JSON file per project.
PROJECTS_DIR = DATA_DIR / "projects"

#: rea-video ``decompose`` output, one folder per project.
BREAKDOWNS_DIR = OUTPUTS_DIR / "breakdowns"

#: API keys and model choices (never committed).
SETTINGS_PATH = DATA_DIR / "settings.json"

#: Hard cap for a single scene, in seconds. The splitter never exceeds it.
MAX_SCENE_SECONDS = float(os.environ.get("SHOT2KEY_MAX_SCENE_SECONDS") or 10.0)

ALLOWED_VIDEO_EXTS: frozenset[str] = frozenset({".mp4", ".mov", ".mkv"})

#: Upload ceiling (2 GB) — a reference clip, not a feature film.
MAX_UPLOAD_BYTES = int(os.environ.get("SHOT2KEY_MAX_UPLOAD_BYTES") or 2 * 1024 * 1024 * 1024)

#: Engines the UI can pick for analysis / image generation.
ANALYZER_ENGINES: tuple[str, ...] = ("agy", "codex", "gemini", "openai")
IMAGE_ENGINES: tuple[str, ...] = ("agy", "codex")

#: How many keyframe generations may run at once (each spawns a CLI agent).
IMAGE_CONCURRENCY = int(os.environ.get("SHOT2KEY_IMAGE_CONCURRENCY") or 2)

#: Subprocess timeouts (seconds).
ANALYZE_TIMEOUT = float(os.environ.get("SHOT2KEY_ANALYZE_TIMEOUT") or 300)
IMAGE_TIMEOUT = float(os.environ.get("SHOT2KEY_IMAGE_TIMEOUT") or 900)
DECOMPOSE_TIMEOUT = float(os.environ.get("SHOT2KEY_DECOMPOSE_TIMEOUT") or 3600)

#: Vite dev server origins allowed to call the API.
CORS_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

#: Defaults written into ``settings.json`` on first run.
DEFAULT_SETTINGS: dict[str, object] = {
    "gemini_api_key": "",
    "gemini_model": "gemini-2.5-flash",
    "openai_base_url": "https://api.openai.com/v1",
    "openai_api_key": "",
    "openai_model": "gpt-4o-mini",
    "default_analyzer": "agy",
    "default_image_engine": "agy",
    "rea_video_lang": "en",
    "rea_video_vlm": False,
}


def get_data_dir() -> Path:
    override = os.environ.get("SHOT2KEY_DATA_DIR")
    return Path(override).resolve() if override else DATA_DIR


def get_uploads_dir() -> Path:
    override = os.environ.get("SHOT2KEY_UPLOADS_DIR")
    return Path(override).resolve() if override else UPLOADS_DIR


def get_outputs_dir() -> Path:
    override = os.environ.get("SHOT2KEY_OUTPUTS_DIR")
    return Path(override).resolve() if override else OUTPUTS_DIR


def get_projects_dir() -> Path:
    return get_data_dir() / "projects"


def get_breakdowns_dir() -> Path:
    return get_outputs_dir() / "breakdowns"


def get_settings_path() -> Path:
    return get_data_dir() / "settings.json"


def ensure_dirs() -> None:
    """Create every runtime directory the app writes to."""
    for path in (
        get_data_dir(),
        get_projects_dir(),
        get_uploads_dir(),
        get_outputs_dir(),
        get_breakdowns_dir(),
    ):
        path.mkdir(parents=True, exist_ok=True)
