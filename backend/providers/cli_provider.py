"""CLI engines: ``agy`` (Antigravity) and ``codex`` (OpenAI Codex).

Both are agent CLIs, not image APIs: we hand them a prompt that names the exact
output path, let the agent use its own image tool, then verify the file on disk.
If the agent saved somewhere else we recover the newest image it produced.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import config
from core import characters as char_store
from core import settings as settings_store
from providers.base import (
    ProviderError,
    SceneAnalysis,
    analysis_from_payload,
    analyze_prompt,
    extract_json,
    image_prompt,
)

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
_MAX_ARGV_PROMPT_CHARS = 24_000
_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")

_AGY_FALLBACK_MODELS: list[str] = [
    "default",
    "gemini-4-argon-medium",
    "gemini-4-argon-high",
    "gemini-4-hydrogen-medium",
    "gemini-4-hydrogen-high",
    "gemini-3.8-flash-medium",
    "gemini-3.8-flash-high",
]

_CODEX_FALLBACK_MODELS: list[str] = [
    "default",
    "gpt-6.1-sol",
    "gpt-6-astra",
    "gpt-5.6-sol",
    "gpt-5",
]


def cli_path(engine: str) -> str | None:
    """Resolve the executable for ``agy`` / ``codex``."""
    name = "agy" if engine == "agy" else "codex"
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt":
        for candidate in (
            Path(os.environ.get("LOCALAPPDATA", "")) / "agy" / "bin" / "agy.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "OpenAI" / "Codex" / "bin" / "codex.exe",
        ):
            if candidate.is_file():
                return str(candidate)
    return None


def describe(engine: str) -> dict[str, Any]:
    path = cli_path(engine)
    return {"available": path is not None, "path": path}


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["NO_COLOR"] = "1"
    env["FORCE_COLOR"] = "0"
    return env


def list_models(engine: str) -> list[str]:
    """Discover available CLI models for ``agy`` or ``codex`` (always starts with ``default``)."""
    if engine == "agy":
        exe = cli_path("agy")
        if not exe:
            return list(_AGY_FALLBACK_MODELS)
        try:
            proc = subprocess.run(
                [exe, "models"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15.0,
                env=_env(),
                creationflags=_CREATE_NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError):
            return list(_AGY_FALLBACK_MODELS)

        models: list[str] = ["default"]
        seen = {"default"}
        for raw_line in (proc.stdout or "").splitlines():
            line = raw_line.strip()
            if not line or line.lower().startswith("fetching"):
                continue
            slug = line.split("\t", 1)[0].split()[0].strip()
            if slug and slug not in seen:
                seen.add(slug)
                models.append(slug)
        return models if len(models) > 1 else list(_AGY_FALLBACK_MODELS)

    if engine == "codex":
        cache_path = Path.home() / ".codex" / "models_cache.json"
        models = ["default"]
        seen = {"default"}
        if cache_path.is_file():
            try:
                payload = json.loads(cache_path.read_text(encoding="utf-8", errors="replace"))
                for item in payload.get("models") or []:
                    slug = str(item.get("slug") or "").strip() if isinstance(item, dict) else ""
                    if slug and slug not in seen:
                        seen.add(slug)
                        models.append(slug)
            except (OSError, json.JSONDecodeError):
                pass
        return models if len(models) > 1 else list(_CODEX_FALLBACK_MODELS)

    return ["default"]


def _run(
    cmd: list[str],
    cwd: Path,
    timeout: float,
    stdin_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        input=stdin_text,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=_env(),
        creationflags=_CREATE_NO_WINDOW,
    )


def _run_agy(prompt: str, cwd: Path, timeout: float, model: str | None = None) -> str:
    exe = cli_path("agy")
    if not exe:
        raise ProviderError("agy CLI tidak ditemukan di PATH.")
    chosen_model = (model or "").strip()

    with tempfile.TemporaryDirectory() as tmp:
        run_cwd = cwd
        if len(prompt) <= _MAX_ARGV_PROMPT_CHARS:
            prompt_arg = prompt
        else:
            tmp_dir = Path(tmp)
            (tmp_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
            run_cwd = tmp_dir
            prompt_arg = (
                "Read prompt.txt in the current working directory and follow every "
                "instruction inside it strictly. Output ONLY the exact final JSON result."
            )

        cmd = [
            exe,
            "--output-format",
            "text",
            "--disable-slash-commands",
            "--dangerously-skip-permissions",
        ]
        if chosen_model and chosen_model.lower() != "default":
            cmd.extend(["--model", chosen_model])
        cmd.append(f"-p={prompt_arg}")

        proc = _run(cmd, run_cwd, timeout)
    if proc.returncode != 0:
        raise ProviderError(f"agy gagal (exit {proc.returncode}): {(proc.stderr or proc.stdout)[-500:]}")
    return proc.stdout or ""


def _run_codex(prompt: str, cwd: Path, timeout: float, model: str | None = None) -> str:
    exe = cli_path("codex")
    if not exe:
        raise ProviderError("codex CLI tidak ditemukan di PATH.")
    chosen_model = (model or "").strip()
    with tempfile.TemporaryDirectory() as tmp:
        last_message = Path(tmp) / "last.txt"
        cmd = [
            exe,
            "exec",
            "--skip-git-repo-check",
            "--dangerously-bypass-approvals-and-sandbox",
            "-C",
            str(cwd),
            "-o",
            str(last_message),
        ]
        if chosen_model and chosen_model.lower() != "default":
            cmd.extend(["-m", chosen_model])
        cmd.append("-")

        proc = _run(cmd, cwd, timeout, stdin_text=prompt)
        if proc.returncode != 0:
            raise ProviderError(
                f"codex gagal (exit {proc.returncode}): {(proc.stderr or proc.stdout)[-500:]}"
            )
        if last_message.is_file():
            text = last_message.read_text(encoding="utf-8", errors="replace").strip()
            if text:
                return text
        return proc.stdout or ""


def run_cli(
    engine: str,
    prompt: str,
    cwd: Path,
    timeout: float,
    model: str | None = None,
) -> str:
    if engine == "agy":
        return _run_agy(prompt, cwd, timeout, model=model)
    if engine == "codex":
        return _run_codex(prompt, cwd, timeout, model=model)
    raise ProviderError(f"Engine CLI tidak dikenal: {engine}")


def _newest_image(directory: Path, since: float) -> Path | None:
    """Newest image written under ``directory`` after ``since`` (recursive)."""
    best: tuple[float, Path] | None = None
    for path in directory.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in _IMAGE_SUFFIXES:
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime + 1 < since:
            continue
        if best is None or mtime > best[0]:
            best = (mtime, path)
    return best[1] if best else None


class CliAnalyzer:
    """Analyze a scene with a CLI agent (text only, no image generation)."""

    def __init__(self, engine: str, model: str | None = None) -> None:
        self.name = engine
        self.model = model

    async def analyze(self, scene: dict[str, Any], context: dict[str, Any]) -> SceneAnalysis:
        prompt = analyze_prompt(scene, context)
        workdir = Path(context.get("workdir") or config.get_data_dir())
        workdir.mkdir(parents=True, exist_ok=True)
        chosen_model = str(
            self.model
            or context.get("model")
            or settings_store.load().get(f"{self.name}_model")
            or "default"
        ).strip()
        text = await asyncio.to_thread(
            run_cli,
            self.name,
            prompt,
            workdir,
            config.ANALYZE_TIMEOUT,
            chosen_model,
        )
        result = analysis_from_payload(extract_json(text), raw=text)
        result.prompt_sent = prompt
        result.extra["model"] = chosen_model
        return result


class CliImageGenerator:
    """Generate a keyframe with a CLI agent's own image tool."""

    def __init__(self, engine: str) -> None:
        self.name = engine
        #: Prompt of the most recent call, read by the job runner for logging.
        self.last_prompt = ""

    async def generate(self, scene: dict[str, Any], out_path: Path, target: str = "first") -> Path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cfg = settings_store.load()
        style_prompt = str(cfg.get("default_style_prompt") or "")
        char_lookup = {c["id"]: c for c in char_store.list_characters() if c.get("id")}
        prompt = image_prompt(
            scene,
            out_path,
            style_prompt=style_prompt,
            character_lookup=char_lookup,
            target=target,
        )
        self.last_prompt = prompt
        started = time.time()

        await asyncio.to_thread(
            run_cli, self.name, prompt, out_path.parent, config.IMAGE_TIMEOUT
        )

        if out_path.is_file() and out_path.stat().st_size > 0:
            return out_path

        # The agent may have written the file under another name: recover it.
        recovered = _newest_image(out_path.parent, started)
        if recovered is not None:
            shutil.move(str(recovered), str(out_path))
            return out_path

        raise ProviderError(
            f"{self.name} selesai tetapi tidak ada file gambar di {out_path.parent}."
        )
