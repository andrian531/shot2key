"""Engine registry: one place that maps an engine id to an implementation."""

from __future__ import annotations

from typing import Any

import config
from core import settings as settings_store
from providers import api_provider, cli_provider
from providers.base import ProviderError, SceneAnalysis


def analyzer(engine: str) -> Any:
    if engine in ("agy", "codex"):
        return cli_provider.CliAnalyzer(engine)
    if engine in ("gemini", "openai"):
        return api_provider.build_analyzer(engine)
    raise ProviderError(f"Engine analisis tidak dikenal: {engine}")


def configured_model(engine: str, cfg: dict[str, Any] | None = None) -> str:
    """Return the configured model name for ``engine`` from settings."""
    data = cfg if cfg is not None else settings_store.load()
    if engine in ("agy", "codex"):
        return str(data.get(f"{engine}_model") or "default").strip() or "default"
    if engine == "gemini":
        return str(data.get("gemini_model") or "gemini-2.5-flash").strip()
    if engine == "openai":
        return str(data.get("openai_model") or "gpt-4o-mini").strip()
    return "default"


def resolve_analyzer_attempts(
    primary_engine: str,
    primary_model: str | None = None,
) -> list[tuple[str, str]]:
    """Build ``[(primary_engine, primary_model), (fallback_engine, fallback_model)?]``."""
    cfg = settings_store.load()
    primary_chosen = (primary_model or configured_model(primary_engine, cfg)).strip() or "default"
    attempts: list[tuple[str, str]] = [(primary_engine, primary_chosen)]

    fb_engine = str(cfg.get("fallback_analyzer") or "").strip()
    if fb_engine and fb_engine in config.ANALYZER_ENGINES:
        fb_model = str(cfg.get("fallback_model") or "default").strip() or "default"
        if not (fb_engine == primary_engine and fb_model == primary_chosen):
            attempts.append((fb_engine, fb_model))
    return attempts


async def run_analyze_with_fallback(
    scene: dict[str, Any],
    context: dict[str, Any],
    primary_engine: str,
    primary_model: str | None = None,
) -> tuple[SceneAnalysis, str, str, str | None]:
    """Run analyzer with optional configured fallback on failure.

    Returns ``(result, used_engine, used_model, fallback_reason)``.
    """
    attempts = resolve_analyzer_attempts(primary_engine, primary_model)
    first_error: str | None = None

    for idx, (engine, model) in enumerate(attempts):
        attempt_ctx = dict(context)
        attempt_ctx["model"] = model
        impl = analyzer(engine)
        try:
            result = await impl.analyze(scene, attempt_ctx)
        except (ProviderError, Exception) as exc:  # noqa: BLE001
            if idx == 0 and len(attempts) > 1:
                first_error = f"{engine} ({model}): {exc}"
                continue
            if first_error is not None:
                raise ProviderError(
                    f"Primary {first_error} | Fallback {engine} ({model}): {exc}"
                ) from exc
            raise
        used_model = str((result.extra or {}).get("model") or model)
        return result, engine, used_model, first_error

    raise ProviderError("Tidak ada analyzer yang berhasil.")


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
