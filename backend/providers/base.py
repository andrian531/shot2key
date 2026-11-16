"""Provider contracts shared by the API and CLI engines."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


class ProviderError(RuntimeError):
    """A provider could not produce a result (missing key, CLI failure, ...)."""


@dataclass
class SceneAnalysis:
    """What an analyzer returns for one scene."""

    description: str = ""
    prompt: str = ""
    camera: str = ""
    lighting: str = ""
    raw: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "prompt": self.prompt,
            "camera": self.camera,
            "lighting": self.lighting,
        }


class Analyzer(Protocol):
    name: str

    async def analyze(self, scene: dict[str, Any], context: dict[str, Any]) -> SceneAnalysis: ...


class ImageGenerator(Protocol):
    name: str

    async def generate(self, scene: dict[str, Any], out_path: Path) -> Path: ...


# --------------------------------------------------------------------------
# Prompt building
# --------------------------------------------------------------------------
ANALYZE_SYSTEM = (
    "You are a film storyboard analyst. You look at one reference frame from a "
    "video scene and describe it precisely enough that an image model can "
    "recreate the same frame."
)

ANALYZE_INSTRUCTIONS = """\
Return ONLY a JSON object, no prose, no markdown fence, with exactly these keys:
{
  "description": "2-4 sentences describing subject, setting, action, composition and colour",
  "prompt": "a single dense image-generation prompt (max 90 words) that would recreate this frame: subject, wardrobe, props, setting, framing, lens, lighting, colour grade, mood",
  "camera": "shot size + angle + lens, e.g. 'medium close-up, eye level, 50mm'",
  "lighting": "lighting setup and colour temperature in a few words"
}
Write the values in English. Do not invent text overlays or logos."""


def analyze_prompt(scene: dict[str, Any], context: dict[str, Any]) -> str:
    """Text prompt handed to a CLI agent or an API model for one scene."""
    lines = [
        ANALYZE_SYSTEM,
        "",
        f"Scene {scene.get('index')} of the storyboard.",
        f"Time range: {scene.get('start_time')}s - {scene.get('end_time')}s "
        f"({scene.get('duration')}s).",
    ]
    if context.get("video_name"):
        lines.append(f"Source video: {context['video_name']}.")
    if context.get("shot_count"):
        lines.append(f"The scene covers {context['shot_count']} original shot(s).")
    if context.get("previous_prompt"):
        lines.append(
            "The previous scene's prompt was: "
            f"{context['previous_prompt'][:400]}. Keep characters and wardrobe consistent."
        )
    keyframe = scene.get("keyframe")
    if keyframe:
        lines.append(f"Reference frame file: {keyframe}")
        lines.append("Read that image file before answering.")
    lines += ["", ANALYZE_INSTRUCTIONS]
    return "\n".join(lines)


IMAGE_INSTRUCTIONS = """\
Generate ONE still image that matches the prompt below. It is a keyframe for a
video scene, so it must look like a frame from the finished film: correct
framing, lighting and colour grade, no text, no watermark, no collage, no
borders, no UI.

Save the image as a PNG file at exactly this path:
{out_path}

Use your image generation tool, then copy or move the result to that path.
Reply with only the absolute file path when the file exists."""


def image_prompt(scene: dict[str, Any], out_path: Path) -> str:
    prompt = (scene.get("prompt") or scene.get("description") or "").strip()
    if not prompt:
        raise ProviderError(
            f"Scene {scene.get('id')} belum punya prompt. Jalankan Analyze dulu atau isi prompt manual."
        )
    reference = scene.get("keyframe")
    head = f"Scene {scene.get('index')} ({scene.get('duration')}s)."
    if reference:
        head += f" Reference frame (for composition and colour only): {reference}"
    return "\n".join(
        [
            head,
            "",
            "PROMPT:",
            prompt,
            "",
            IMAGE_INSTRUCTIONS.format(out_path=str(out_path)),
        ]
    )


# --------------------------------------------------------------------------
# Tolerant JSON extraction (CLI agents like to wrap answers in prose)
# --------------------------------------------------------------------------
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> dict[str, Any]:
    """Pull the first JSON object out of an agent's answer."""
    if not text:
        raise ProviderError("Provider mengembalikan jawaban kosong.")

    candidates: list[str] = []
    for match in _FENCE.finditer(text):
        candidates.append(match.group(1).strip())
    candidates.append(text.strip())

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    start = text.find("{")
    while start != -1:
        depth = 0
        for position in range(start, len(text)):
            char = text[position]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    chunk = text[start : position + 1]
                    try:
                        parsed = json.loads(chunk)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)

    raise ProviderError(f"Jawaban provider bukan JSON yang valid: {text[:200]}")


def analysis_from_payload(payload: dict[str, Any], raw: str = "") -> SceneAnalysis:
    def pick(*keys: str) -> str:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    description = pick("description", "visual_description", "scene", "summary")
    prompt = pick("prompt", "image_prompt", "generation_prompt")
    if not prompt and description:
        prompt = description
    if not description and prompt:
        description = prompt
    if not prompt:
        raise ProviderError("Provider tidak mengembalikan prompt.")
    return SceneAnalysis(
        description=description,
        prompt=prompt,
        camera=pick("camera", "camera_notes", "shot"),
        lighting=pick("lighting", "light"),
        raw=raw,
    )
