"""CLI engines: ``agy`` (Antigravity) and ``codex`` (OpenAI Codex).

Both are agent CLIs, not image APIs: we hand them a prompt that names the exact
output path, let the agent use its own image tool, then verify the file on disk.
If the agent saved somewhere else we recover the newest image it produced.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import config
from providers.base import (
    ProviderError,
    SceneAnalysis,
    analysis_from_payload,
    analyze_prompt,
    extract_json,
    image_prompt,
)

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")


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


def _run(cmd: list[str], cwd: Path, timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=_env(),
        creationflags=_CREATE_NO_WINDOW,
    )


def _run_agy(prompt: str, cwd: Path, timeout: float) -> str:
    exe = cli_path("agy")
    if not exe:
        raise ProviderError("agy CLI tidak ditemukan di PATH.")
    proc = _run(
        [exe, "-p", prompt, "--dangerously-skip-permissions", "--output-format", "text"],
        cwd,
        timeout,
    )
    if proc.returncode != 0:
        raise ProviderError(f"agy gagal (exit {proc.returncode}): {(proc.stderr or proc.stdout)[-500:]}")
    return proc.stdout or ""


def _run_codex(prompt: str, cwd: Path, timeout: float) -> str:
    exe = cli_path("codex")
    if not exe:
        raise ProviderError("codex CLI tidak ditemukan di PATH.")
    with tempfile.TemporaryDirectory() as tmp:
        last_message = Path(tmp) / "last.txt"
        proc = _run(
            [
                exe,
                "exec",
                "--skip-git-repo-check",
                "--dangerously-bypass-approvals-and-sandbox",
                "-C",
                str(cwd),
                "-o",
                str(last_message),
                prompt,
            ],
            cwd,
            timeout,
        )
        if proc.returncode != 0:
            raise ProviderError(
                f"codex gagal (exit {proc.returncode}): {(proc.stderr or proc.stdout)[-500:]}"
            )
        if last_message.is_file():
            text = last_message.read_text(encoding="utf-8", errors="replace").strip()
            if text:
                return text
        return proc.stdout or ""


def run_cli(engine: str, prompt: str, cwd: Path, timeout: float) -> str:
    if engine == "agy":
        return _run_agy(prompt, cwd, timeout)
    if engine == "codex":
        return _run_codex(prompt, cwd, timeout)
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

    def __init__(self, engine: str) -> None:
        self.name = engine

    async def analyze(self, scene: dict[str, Any], context: dict[str, Any]) -> SceneAnalysis:
        prompt = analyze_prompt(scene, context)
        workdir = Path(context.get("workdir") or config.get_data_dir())
        workdir.mkdir(parents=True, exist_ok=True)
        text = await asyncio.to_thread(
            run_cli, self.name, prompt, workdir, config.ANALYZE_TIMEOUT
        )
        return analysis_from_payload(extract_json(text), raw=text)


class CliImageGenerator:
    """Generate a keyframe with a CLI agent's own image tool."""

    def __init__(self, engine: str) -> None:
        self.name = engine

    async def generate(self, scene: dict[str, Any], out_path: Path) -> Path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        prompt = image_prompt(scene, out_path)
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
