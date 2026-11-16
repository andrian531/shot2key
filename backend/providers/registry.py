"""Engine registry: one place that maps an engine id to an implementation."""

from __future__ import annotations

from typing import Any

import config
from providers import api_provider, cli_provider
from providers.base import ProviderError


def analyzer(engine: str) -> Any:
    if engine in ("agy", "codex"):
        return cli_provider.CliAnalyzer(engine)
    if engine in ("gemini", "openai"):
        return api_provider.build_analyzer(engine)
    raise ProviderError(f"Engine analisis tidak dikenal: {engine}")


def image_generator(engine: str) -> Any:
    if engine in config.IMAGE_ENGINES:
        return cli_provider.CliImageGenerator(engine)
    raise ProviderError(
        f"Engine gambar tidak dikenal: {engine} (pilih salah satu: {', '.join(config.IMAGE_ENGINES)})"
    )


def status() -> dict[str, Any]:
    return {
        "analyzers": list(config.ANALYZER_ENGINES),
        "image_engines": list(config.IMAGE_ENGINES),
        "agy": cli_provider.describe("agy"),
        "codex": cli_provider.describe("codex"),
    }
