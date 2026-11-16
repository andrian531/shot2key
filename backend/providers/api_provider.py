"""API engines: Gemini (native) and any OpenAI-compatible chat endpoint.

The reference keyframe is sent inline as base64 so the model describes what is
actually in the frame instead of guessing from the timestamp.
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

import httpx

import config
from core import settings as settings_store
from providers.base import (
    ProviderError,
    SceneAnalysis,
    analysis_from_payload,
    analyze_prompt,
    extract_json,
    scene_input_images,
)

TIMEOUT = httpx.Timeout(120.0, connect=15.0)


def _inline_image(path: str | Path | None) -> tuple[str, str] | None:
    if not path:
        return None
    file_path = Path(path)
    if not file_path.is_file():
        return None
    mime = mimetypes.guess_type(file_path.name)[0] or "image/jpeg"
    data = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return mime, data


def _scene_images(scene: dict[str, Any]) -> list[tuple[str, str, str]]:
    """First Frame, Last Frame and Contact Sheet as ``(label, mime, base64)``."""
    images: list[tuple[str, str, str]] = []
    for label, path in scene_input_images(scene):
        inline = _inline_image(path)
        if inline is not None:
            mime, data = inline
            images.append((label, mime, data))
    return images


class GeminiAnalyzer:
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def analyze(self, scene: dict[str, Any], context: dict[str, Any]) -> SceneAnalysis:
        if not self.api_key:
            raise ProviderError("Gemini API key belum diisi (Settings).")

        prompt_text = analyze_prompt(scene, context)
        parts: list[dict[str, Any]] = [{"text": prompt_text}]
        for label, mime, data in _scene_images(scene):
            parts.append({"text": f"{label}:"})
            parts.append({"inline_data": {"mime_type": mime, "data": data}})

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        body = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"},
        }
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(url, params={"key": self.api_key}, json=body)
        if response.status_code >= 400:
            raise ProviderError(f"Gemini {response.status_code}: {response.text[:300]}")

        payload = response.json()
        try:
            text = "".join(
                part.get("text", "")
                for part in payload["candidates"][0]["content"]["parts"]
            )
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"Jawaban Gemini tidak dikenali: {str(payload)[:300]}") from exc

        result = analysis_from_payload(extract_json(text), raw=text)
        result.prompt_sent = prompt_text
        return result


class OpenAICompatibleAnalyzer:
    name = "openai"

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key
        self.model = model

    async def analyze(self, scene: dict[str, Any], context: dict[str, Any]) -> SceneAnalysis:
        if not self.api_key:
            raise ProviderError("API key OpenAI-compatible belum diisi (Settings).")

        prompt_text = analyze_prompt(scene, context)
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt_text}]
        for label, mime, data in _scene_images(scene):
            content.append({"type": "text", "text": f"{label}:"})
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}
            )

        body = {
            "model": self.model,
            "temperature": 0.4,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "You answer with a single JSON object."},
                {"role": "user", "content": content},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions", json=body, headers=headers
            )
        if response.status_code >= 400:
            raise ProviderError(f"API {response.status_code}: {response.text[:300]}")

        payload = response.json()
        try:
            text = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"Jawaban API tidak dikenali: {str(payload)[:300]}") from exc

        result = analysis_from_payload(extract_json(text), raw=text)
        result.prompt_sent = prompt_text
        return result


def build_analyzer(engine: str) -> Any:
    """Factory for the API engines, reading keys from the settings file."""
    values = settings_store.load()
    if engine == "gemini":
        return GeminiAnalyzer(
            api_key=str(values.get("gemini_api_key") or ""),
            model=str(values.get("gemini_model") or config.DEFAULT_SETTINGS["gemini_model"]),
        )
    if engine == "openai":
        return OpenAICompatibleAnalyzer(
            base_url=str(values.get("openai_base_url") or ""),
            api_key=str(values.get("openai_api_key") or ""),
            model=str(values.get("openai_model") or config.DEFAULT_SETTINGS["openai_model"]),
        )
    raise ProviderError(f"Engine API tidak dikenal: {engine}")
