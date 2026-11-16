"""Export bundle: keyframes + prompts + VIDEO.md + audio stems, as one ZIP."""

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


def _max_seconds(project: dict[str, Any]) -> float:
    return float(project.get("max_scene_seconds") or config.MAX_SCENE_SECONDS)


def build_video_md(project: dict[str, Any]) -> str:
    """Human/agent readable storyboard, one section per scene."""
    source = project.get("source") or {}
    scenes = project.get("scenes") or []
    lines = [
        f"# {project.get('filename')} — Shot2Key storyboard",
        "",
        f"- Project: `{project.get('id')}`",
        f"- Duration: {_fmt_time(source.get('duration'))} ({source.get('duration')}s)",
        f"- Resolution: {source.get('width')}x{source.get('height')} @ {source.get('fps')} fps",
        f"- Scenes: {len(scenes)} (one per shot, max {_max_seconds(project):g}s each)",
        "",
        "Each scene has an **image prompt** (make the still / First Frame) and a "
        "**video motion prompt** (paste into Google Flow / Veo together with the "
        "keyframe). Use `reference/<id>.jpg` as First Frame and "
        "`reference/<id>_last.jpg` as Last Frame when the model supports both.",
        "",
    ]

    for scene in scenes:
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
        lines += [
            "**Image Prompt (keyframe / First Frame)**",
            "",
            "```text",
            (scene.get("prompt") or "").strip(),
            "```",
            "",
            "**Video Motion Prompt (Google Flow / Veo)**",
            "",
            "```text",
            (scene.get("video_prompt") or "").strip(),
            "```",
            "",
        ]
        if scene.get("image_path"):
            lines += [f"Keyframe: `keyframes/{scene.get('id')}.png`", ""]
        if scene.get("keyframe"):
            lines += [f"First frame: `reference/{scene.get('id')}.jpg`", ""]
        if scene.get("last_keyframe"):
            lines += [f"Last frame: `reference/{scene.get('id')}_last.jpg`", ""]

    stems = project.get("audio_stems") or []
    if stems:
        lines += ["## Audio stems", ""]
        lines += [f"- `stems/{stem}.wav`" for stem in stems]
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_prompts_json(project: dict[str, Any]) -> str:
    payload = {
        "project_id": project.get("id"),
        "filename": project.get("filename"),
        "source": project.get("source") or {},
        "max_scene_seconds": _max_seconds(project),
        "scenes": [
            {
                "id": scene.get("id"),
                "index": scene.get("index"),
                "start_time": scene.get("start_time"),
                "end_time": scene.get("end_time"),
                "duration": scene.get("duration"),
                "shot_indices": scene.get("shot_indices"),
                "description": scene.get("description"),
                # ``prompt`` kept for older consumers; ``image_prompt`` is the
                # explicit name used by the Phase 2 UI and docs.
                "prompt": scene.get("prompt"),
                "image_prompt": scene.get("prompt"),
                "video_prompt": scene.get("video_prompt"),
                "camera": scene.get("camera"),
                "lighting": scene.get("lighting"),
                "engine": scene.get("engine"),
                "keyframe": f"keyframes/{scene.get('id')}.png"
                if scene.get("image_path")
                else None,
                "first_frame": f"reference/{scene.get('id')}.jpg"
                if scene.get("keyframe")
                else None,
                "last_frame": f"reference/{scene.get('id')}_last.jpg"
                if scene.get("last_keyframe")
                else None,
            }
            for scene in project.get("scenes") or []
        ],
        "audio_stems": [
            f"stems/{stem}.wav" for stem in (project.get("audio_stems") or [])
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
            last_reference = scene.get("last_keyframe")
            if last_reference and Path(last_reference).is_file():
                suffix = Path(last_reference).suffix or ".jpg"
                archive.write(last_reference, f"reference/{scene.get('id')}_last{suffix}")

        breakdown_dir = Path(project.get("breakdown_dir") or "")
        for stem in project.get("audio_stems") or []:
            stem_path = breakdown_dir / "stems" / f"{stem}.wav"
            if stem_path.is_file():
                archive.write(stem_path, f"stems/{stem}.wav")

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
