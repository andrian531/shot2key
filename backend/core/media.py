"""ffmpeg plumbing: discovery, probing and frame extraction.

``imageio-ffmpeg`` ships a static ffmpeg inside a wheel, so a machine without
ffmpeg on PATH still works once ``backend/requirements.txt`` is installed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


@lru_cache(maxsize=1)
def ffmpeg_path() -> str | None:
    """Resolve ffmpeg: explicit env var, PATH, then the imageio-ffmpeg wheel."""
    explicit = os.environ.get("SHOT2KEY_FFMPEG")
    if explicit and Path(explicit).is_file():
        return explicit

    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path

    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def ffmpeg_source() -> str:
    """Human-readable origin of the resolved binary (for the status bar)."""
    if os.environ.get("SHOT2KEY_FFMPEG"):
        return "env"
    if shutil.which("ffmpeg"):
        return "system"
    try:
        import imageio_ffmpeg  # noqa: F401

        return "imageio-ffmpeg"
    except Exception:
        return "missing"


def ffmpeg_dir() -> str | None:
    """Directory to prepend to ``PATH`` so child processes see ffmpeg too."""
    exe = ffmpeg_path()
    return str(Path(exe).parent) if exe else None


def run(cmd: list[str], timeout: float = 120) -> subprocess.CompletedProcess[str]:
    """Run a command without flashing a console window on Windows."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=_CREATE_NO_WINDOW,
    )


def probe_video(path: str | Path) -> dict[str, Any]:
    """Read duration / size / fps straight from ``ffmpeg -i`` stderr.

    Using ffmpeg instead of ffprobe keeps the dependency set to one binary.
    Returns an empty dict when the file cannot be read.
    """
    exe = ffmpeg_path()
    if not exe:
        return {}
    try:
        proc = run([exe, "-hide_banner", "-i", str(path)], timeout=60)
    except Exception:
        return {}

    info: dict[str, Any] = {}
    for line in proc.stderr.splitlines():
        line = line.strip()
        if line.startswith("Duration:") and "duration" not in info:
            stamp = line.split("Duration:", 1)[1].split(",", 1)[0].strip()
            parts = stamp.split(":")
            if len(parts) == 3:
                try:
                    hours, minutes, seconds = (float(part) for part in parts)
                    info["duration"] = round(hours * 3600 + minutes * 60 + seconds, 3)
                except ValueError:
                    pass
        elif "Video:" in line and "width" not in info:
            import re

            size = re.search(r"(\d{2,5})x(\d{2,5})", line)
            if size:
                info["width"] = int(size.group(1))
                info["height"] = int(size.group(2))
            fps = re.search(r"([\d.]+) fps", line)
            if fps:
                try:
                    info["fps"] = round(float(fps.group(1)), 3)
                except ValueError:
                    pass
    return info


def extract_frame(
    video: str | Path,
    at_seconds: float,
    out_path: str | Path,
    width: int = 1280,
) -> Path | None:
    """Write a single JPEG at ``at_seconds``; returns the path or ``None``."""
    exe = ffmpeg_path()
    if not exe:
        return None
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        exe,
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{max(0.0, float(at_seconds)):.3f}",
        "-i",
        str(video),
        "-frames:v",
        "1",
        "-vf",
        f"scale='min({width},iw)':-2",
        "-q:v",
        "3",
        "-y",
        str(out_path),
    ]
    try:
        proc = run(cmd, timeout=120)
    except Exception:
        return None
    if proc.returncode != 0 or not out_path.is_file() or out_path.stat().st_size == 0:
        return None
    return out_path


def python_exe() -> str:
    """The interpreter running the backend (children must match the venv)."""
    return sys.executable


def describe_ffmpeg() -> dict[str, Any]:
    exe = ffmpeg_path()
    return {
        "available": bool(exe),
        "path": exe,
        "source": ffmpeg_source(),
    }
