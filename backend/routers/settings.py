"""Settings endpoints: API keys and default engines."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import config
from core import settings as settings_store
from providers import cli_provider

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    openai_base_url: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    default_analyzer: str | None = None
    agy_model: str | None = None
    codex_model: str | None = None
    fallback_analyzer: str | None = None
    fallback_model: str | None = None
    default_image_engine: str | None = None
    rea_video_lang: str | None = None
    rea_video_vlm: bool | None = None
    auto_analyze: bool | None = None
    default_style_prompt: str | None = None
    max_scene_seconds: float | None = None


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
    if "fallback_analyzer" in values:
        fb = str(values["fallback_analyzer"]).strip()
        if fb == "":
            values["fallback_analyzer"] = ""
        elif fb not in config.ANALYZER_ENGINES:
            values.pop("fallback_analyzer")
        else:
            values["fallback_analyzer"] = fb
    for model_key in ("agy_model", "codex_model", "fallback_model"):
        if model_key in values:
            cleaned = str(values[model_key]).strip()
            values[model_key] = cleaned or "default"
    if "default_image_engine" in values and values["default_image_engine"] not in config.IMAGE_ENGINES:
        values.pop("default_image_engine")
    if "max_scene_seconds" in values:
        try:
            seconds = float(values["max_scene_seconds"])
        except (TypeError, ValueError):
            values.pop("max_scene_seconds")
        else:
            if not 1.0 <= seconds <= 60.0:
                values.pop("max_scene_seconds")
            else:
                values["max_scene_seconds"] = seconds
    settings_store.save(values)
    return {"settings": settings_store.masked()}


@router.get("/cli-models/{engine}")
async def cli_models(engine: str) -> dict[str, Any]:
    if engine not in ("agy", "codex"):
        raise HTTPException(status_code=400, detail=f"CLI engine tidak dikenal: {engine}")
    models = await asyncio.to_thread(cli_provider.list_models, engine)
    return {
        "engine": engine,
        "available": cli_provider.cli_path(engine) is not None,
        "models": models,
    }
