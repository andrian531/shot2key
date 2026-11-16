"""Export bundle: keyframes + prompts + VIDEO.md + subtitles, as one ZIP."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Any

import config


def _fmt_time(seconds: float | None) -> str:
    value = float(seconds or 0.0)
    minutes, secs = divmod(value, 60)
    return f"{int(minutes):02d}:{secs:05.2f}"


def build_video_md(project: dict[str, Any]) -> str:
    """Human/agent readable storyboard, one section per scene."""
    source = project.get("source") or {}
    lines = [
        f"# {project.get('filename')} — Shot2Key storyboard",
        "",
        f"- Project: `{project.get('id')}`",
        f"- Duration: {_fmt_time(source.get('duration'))} "
        f"({source.get('duration')}s)",
        f"- Resolution: {source.get('width')}x{source.get('height')} @ {source.get('fps')} fps",
        f"- Scenes: {len(project.get('scenes') or [])} (max {config.MAX_SCENE_SECONDS:g}s each)",
        "",
        "Each scene below is a keyframe plus the prompt that recreates it. "
        "Feed the image and the prompt to an image-to-video model (Google Flow, Kling, ...).",
        "",
    ]

    for scene in project.get("scenes") or []:
        lines += [
            f"## Scene {scene.get('index')} — {_fmt_time(scene.get('start_time'))} → "
            f"{_fmt_time(scene.get('end_time'))} ({scene.get('duration')}s)",
            "",
        ]
        if scene.get("description"):
            lines += [scene["description"], ""]
        if scene.get("camera") or scene.get("lighting"):
            lines.append(
                f"**Camera:** {scene.get('camera') or '—'}  \n"
                f"**Lighting:** {scene.get('lighting') or '—'}"
            )
            lines.append("")
        lines += ["**Prompt**", "", "```text", (scene.get("prompt") or "").strip(), "```", ""]
        if scene.get("image_path"):
            lines += [f"Keyframe: `keyframes/{scene.get('id')}.png`", ""]
        if scene.get("keyframe"):
            lines += [f"Reference frame: `reference/{scene.get('id')}.jpg`", ""]

    return "\n".join(lines).rstrip() + "\n"


def build_prompts_json(project: dict[str, Any]) -> str:
    payload = {
        "project_id": project.get("id"),
        "filename": project.get("filename"),
        "source": project.get("source") or {},
        "max_scene_seconds": config.MAX_SCENE_SECONDS,
        "scenes": [
            {
                "id": scene.get("id"),
                "index": scene.get("index"),
                "start_time": scene.get("start_time"),
                "end_time": scene.get("end_time"),
                "duration": scene.get("duration"),
                "shot_indices": scene.get("shot_indices"),
                "description": scene.get("description"),
                "prompt": scene.get("prompt"),
                "camera": scene.get("camera"),
                "lighting": scene.get("lighting"),
                "engine": scene.get("engine"),
                "keyframe": f"keyframes/{scene.get('id')}.png"
                if scene.get("image_path")
                else None,
            }
            for scene in project.get("scenes") or []
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_zip(project: dict[str, Any]) -> bytes:
    """Assemble the export bundle in memory."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("prompts.json", build_prompts_json(project))
        archive.writestr("VIDEO.md", build_video_md(project))
        archive.writestr(
            "storyboard.json",
            json.dumps(
                {
                    "shots": project.get("shots") or [],
                    "scenes": project.get("scenes") or [],
                },
                ensure_ascii=False,
                indent=2,
            ),
        )

        for scene in project.get("scenes") or []:
            image_path = scene.get("image_path")
            if image_path and Path(image_path).is_file():
                archive.write(image_path, f"keyframes/{scene.get('id')}.png")
            reference = scene.get("keyframe")
            if reference and Path(reference).is_file():
                suffix = Path(reference).suffix or ".jpg"
                archive.write(reference, f"reference/{scene.get('id')}{suffix}")

        for key, path in (project.get("subtitles") or {}).items():
            file_path = Path(path)
            if file_path.is_file():
                name = "subtitles.srt" if key == "srt" else "overlays.ass"
                archive.write(file_path, name)

    return buffer.getvalue()


def export_filename(project: dict[str, Any]) -> str:
    stem = Path(str(project.get("filename") or "shot2key")).stem
    safe = "".join(char if char.isalnum() or char in "-_" else "_" for char in stem)[:60]
    return f"{safe or 'shot2key'}_storyboard.zip"
