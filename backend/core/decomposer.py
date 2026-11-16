"""Wrapper around the ``rea-video`` CLI (JuneYaooo/rea-video, Apache-2.0).

rea-video is installed as a console script inside ``backend/.venv``. When the
script is missing we fall back to ``python -c "from rea_video.cli import main"``
so a source checkout still works.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import config
from core import media

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

_SHOT_LINE = re.compile(r"shot_(\d+)")


class DecomposeError(RuntimeError):
    """rea-video failed or produced no breakdown."""


def _console_script() -> Path | None:
    scripts = Path(sys.executable).parent
    for name in ("rea-video.exe", "rea-video"):
        candidate = scripts / name
        if candidate.is_file():
            return candidate
    return None


def rea_video_command() -> list[str] | None:
    """Command prefix that runs the rea-video CLI, or ``None`` if unavailable."""
    script = _console_script()
    if script is not None:
        return [str(script)]

    on_path = shutil.which("rea-video")
    if on_path:
        return [on_path]

    try:
        import rea_video  # noqa: F401  (installed package, not this module)
    except Exception:
        return None

    return [
        sys.executable,
        "-c",
        "import sys; from rea_video.cli import main; sys.exit(main())",
    ]


def rea_video_version() -> str | None:
    try:
        import importlib.metadata as metadata

        return metadata.version("rea-video")
    except Exception:
        return None


def describe() -> dict[str, Any]:
    cmd = rea_video_command()
    return {
        "available": cmd is not None,
        "command": " ".join(cmd) if cmd else None,
        "version": rea_video_version(),
    }


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    ffmpeg_dir = media.ffmpeg_dir()
    if ffmpeg_dir:
        env["PATH"] = ffmpeg_dir + os.pathsep + env.get("PATH", "")
    return env


def decompose(
    video_path: str | Path,
    out_dir: str | Path,
    on_progress: Callable[[int, str], None] | None = None,
    lang: str = "en",
    use_vlm: bool = False,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Run ``rea-video decompose`` and return the parsed ``breakdown.json``.

    ``on_progress(percent, message)`` is called from the worker thread as the
    CLI logs each shot, so the UI can show movement during a long run.
    """
    cmd = rea_video_command()
    if cmd is None:
        raise DecomposeError(
            "rea-video tidak terpasang di .venv. Jalankan start.bat untuk menginstal dependensi."
        )

    video_path = Path(video_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    args = [*cmd, "decompose", str(video_path), "-o", str(out_dir), "--lang", lang]
    if use_vlm:
        args.append("--vlm")

    if on_progress:
        on_progress(5, "Menjalankan rea-video decompose...")

    proc = subprocess.Popen(
        args,
        cwd=str(out_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_env(),
        creationflags=_CREATE_NO_WINDOW,
    )

    tail: list[str] = []
    shots_seen = 0
    try:
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.rstrip("\r\n")
            if not line:
                continue
            tail.append(line)
            if len(tail) > 200:
                tail.pop(0)
            match = _SHOT_LINE.search(line)
            if match:
                shots_seen = max(shots_seen, int(match.group(1)))
                if on_progress:
                    # Shots are measured one by one; the last 10% is the report.
                    on_progress(min(90, 10 + shots_seen * 4), f"Menganalisis shot {shots_seen}...")
            elif on_progress and ("report" in line.lower() or "VIDEO.md" in line):
                on_progress(92, "Menulis laporan...")
        proc.wait(timeout=timeout or config.DECOMPOSE_TIMEOUT)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise DecomposeError("rea-video decompose melebihi batas waktu.")
    finally:
        if proc.poll() is None:
            proc.kill()

    if proc.returncode != 0:
        detail = "\n".join(tail[-12:]) or f"exit code {proc.returncode}"
        raise DecomposeError(f"rea-video decompose gagal:\n{detail}")

    breakdown_path = out_dir / "breakdown.json"
    if not breakdown_path.is_file():
        raise DecomposeError("rea-video selesai tetapi breakdown.json tidak ditemukan.")

    if on_progress:
        on_progress(96, "Membaca breakdown...")

    return json.loads(breakdown_path.read_text(encoding="utf-8"))


def _asset(breakdown_dir: str | Path, shot: dict[str, Any], *keys: str) -> Path | None:
    assets = shot.get("assets") or {}
    for key in keys:
        relative = assets.get(key)
        if not relative:
            continue
        path = Path(breakdown_dir) / relative
        if path.is_file():
            return path
    return None


def shot_keyframe(breakdown_dir: str | Path, shot: dict[str, Any]) -> Path | None:
    """Absolute path of the first reference frame rea-video wrote for a shot."""
    return _asset(breakdown_dir, shot, "first_frame", "sheet")


def shot_last_keyframe(breakdown_dir: str | Path, shot: dict[str, Any]) -> Path | None:
    """Absolute path of the shot's last frame (Google Flow First+Last mode)."""
    return _asset(breakdown_dir, shot, "last_frame")


def shot_sheet(breakdown_dir: str | Path, shot: dict[str, Any]) -> Path | None:
    """Absolute path of the shot's contact sheet (frames across the shot)."""
    return _asset(breakdown_dir, shot, "sheet")


def audio_stems(breakdown_dir: str | Path) -> list[str]:
    """Which separated audio stems rea-video produced (original/vocals/music/effects)."""
    stems_dir = Path(breakdown_dir) / "stems"
    if not stems_dir.is_dir():
        return []
    found: list[str] = []
    for name in ("original", "vocals", "music", "effects"):
        if (stems_dir / f"{name}.wav").is_file():
            found.append(name)
    return found


def report_path(breakdown_dir: str | Path) -> Path | None:
    """rea-video's HTML report, if it was written."""
    path = Path(breakdown_dir) / "report.html"
    return path if path.is_file() else None


def packaging_files(breakdown_dir: str | Path) -> dict[str, Path]:
    """Subtitle files rea-video wrote, if any (``packaging/subtitles.srt`` ...)."""
    root = Path(breakdown_dir) / "packaging"
    found: dict[str, Path] = {}
    for key, name in (("srt", "subtitles.srt"), ("ass", "overlays.ass")):
        path = root / name
        if path.is_file() and path.stat().st_size > 0:
            found[key] = path
    return found
