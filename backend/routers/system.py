"""System status endpoint: is everything this app depends on ready?"""

from __future__ import annotations

import platform
import sys

from fastapi import APIRouter

import config
from core import decomposer, media
from core import settings as settings_store
from providers import cli_provider, registry

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status")
def status() -> dict[str, object]:
    rea = decomposer.describe()
    ffmpeg = media.describe_ffmpeg()
    agy = cli_provider.describe("agy")
    codex = cli_provider.describe("codex")
    settings = settings_store.masked()

    api_ready = {
        "gemini": bool(settings.get("gemini_api_key_set")),
        "openai": bool(settings.get("openai_api_key_set")),
    }
    analyzers_ready = {
        "agy": bool(agy["available"]),
        "codex": bool(codex["available"]),
        "gemini": api_ready["gemini"],
        "openai": api_ready["openai"],
    }

    return {
        "ready": bool(rea["available"] and ffmpeg["available"]),
        "rea_video": rea,
        "ffmpeg": ffmpeg,
        "agy": agy,
        "codex": codex,
        "api_keys": api_ready,
        "analyzers_ready": analyzers_ready,
        "engines": registry.status(),
        "defaults": {
            "analyzer": settings.get("default_analyzer"),
            "image_engine": settings.get("default_image_engine"),
        },
        "max_scene_seconds": config.MAX_SCENE_SECONDS,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "data_dir": str(config.get_data_dir()),
    }
