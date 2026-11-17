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


def extract_interval_frames(
    video: str | Path,
    start_seconds: float,
    end_seconds: float,
    out_dir: str | Path,
    interval: float = 0.5,
    max_frames: int = 12,
    width: int = 960,
) -> list[tuple[float, str]]:
    """Extract evenly spaced frames across ``[start_seconds, end_seconds]``.

    Returns ``[(offset_seconds, image_path), ...]`` capped at ``max_frames``.
    """
    start = max(0.0, float(start_seconds))
    end = max(start, float(end_seconds))
    duration = end - start
    if duration <= 0.05:
        timestamps = [start]
    else:
        step = max(0.2, float(interval))
        count = int(duration / step) + 1
        if count > max_frames:
            step = duration / max(1, max_frames - 1)
            count = max_frames
        timestamps = [min(end - 0.03, start + idx * step) for idx in range(count)]
        if end - timestamps[-1] > 0.15 and len(timestamps) < max_frames:
            timestamps.append(max(start, end - 0.03))

    out_path_dir = Path(out_dir)
    out_path_dir.mkdir(parents=True, exist_ok=True)
    results: list[tuple[float, str]] = []
    for idx, ts in enumerate(timestamps, start=1):
        offset = round(max(0.0, ts - start), 2)
        dest = out_path_dir / f"frame_{idx:02d}_{offset:.2f}s.jpg"
        extracted = extract_frame(video, ts, dest, width=width)
        if extracted is not None:
            results.append((offset, str(extracted)))
    return results


def cut_scene_clip(
    video: str | Path,
    start_seconds: float,
    end_seconds: float,
    out_path: str | Path,
) -> Path | None:
    """Cut a frame-accurate MP4 clip for ``[start_seconds, end_seconds]`` on demand."""
    exe = ffmpeg_path()
    if not exe:
        return None
    start = max(0.0, float(start_seconds))
    duration = max(0.25, float(end_seconds) - start)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(".tmp.mp4")

    cmd = [
        exe,
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(video),
        "-t",
        f"{duration:.3f}",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        "-y",
        str(tmp_path),
    ]
    try:
        proc = run(cmd, timeout=120)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        return None
    if proc.returncode != 0 or not tmp_path.is_file() or tmp_path.stat().st_size == 0:
        tmp_path.unlink(missing_ok=True)
        return None
    os.replace(tmp_path, out_path)
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
