"""Settings endpoints: API keys and default engines."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

import config
from core import settings as settings_store

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    openai_base_url: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    default_analyzer: str | None = None
    default_image_engine: str | None = None
    rea_video_lang: str | None = None
    rea_video_vlm: bool | None = None


@router.get("")
def get_settings() -> dict[str, Any]:
    return {
        "settings": settings_store.masked(),
        "engines": {
            "analyzers": list(config.ANALYZER_ENGINES),
            "image": list(config.IMAGE_ENGINES),
        },
    }


@router.put("")
def put_settings(body: SettingsUpdate) -> dict[str, Any]:
    values = {key: value for key, value in body.model_dump().items() if value is not None}
    if "default_analyzer" in values and values["default_analyzer"] not in config.ANALYZER_ENGINES:
        values.pop("default_analyzer")
    if "default_image_engine" in values and values["default_image_engine"] not in config.IMAGE_ENGINES:
        values.pop("default_image_engine")
    settings_store.save(values)
    return {"settings": settings_store.masked()}
