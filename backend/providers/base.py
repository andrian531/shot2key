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
    characters: list[dict[str, str]] = field(default_factory=list)
    raw: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "prompt": self.prompt,
            "camera": self.camera,
            "lighting": self.lighting,
            "characters": self.characters,
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
  "prompt": "a single dense image-generation prompt (max 90 words) that would recreate this frame: subject, wardrobe, props, setting, framing, lens, lighting, colour grade, mood. Whenever a main person appears, refer to them using a placeholder tag like [Char_1], [Char_2] in the prompt.",
  "camera": "shot size + angle + lens, e.g. 'medium close-up, eye level, 50mm'",
  "lighting": "lighting setup and colour temperature in a few words",
  "characters": [
    {"slot": "Char_1", "description": "short role/appearance of this person in the frame"}
  ]
}
Write the values in English. If no people appear, set "characters" to []. Do not invent text overlays or logos."""


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


def resolve_scene_prompt(
    scene: dict[str, Any],
    style_prompt: str = "",
    character_lookup: dict[str, dict[str, Any]] | None = None,
) -> tuple[str, list[tuple[str, str]]]:
    """Resolve character/costume placeholders and append default style prompt.

    Returns ``(resolved_prompt, [(slot, ref_image_path), ...])``.
    """
    prompt = (scene.get("prompt") or scene.get("description") or "").strip()
    if not prompt:
        raise ProviderError(
            f"Scene {scene.get('id')} belum punya prompt. Jalankan Analyze dulu atau isi prompt manual."
        )

    ref_images: list[tuple[str, str]] = []
    if scene.get("replace_characters") and character_lookup:
        mappings = scene.get("character_mappings") or {}
        extra_notes: list[str] = []
        for slot, mapping in mappings.items():
            if not isinstance(mapping, dict):
                continue
            char_id = mapping.get("character_id")
            if not char_id or char_id not in character_lookup:
                continue
            char = character_lookup[char_id]
            costume_desc = ""
            costume_id = mapping.get("costume_id")
            for cos in char.get("costumes") or []:
                if cos.get("id") == costume_id:
                    costume_desc = str(cos.get("description") or cos.get("name") or "").strip()
                    break

            parts = [str(char.get("name") or slot)]
            if char.get("appearance"):
                parts.append(str(char["appearance"]))
            if costume_desc:
                parts.append(f"wearing {costume_desc}")
            replacement = ", ".join(parts)

            tag = f"[{slot}]"
            if tag in prompt:
                prompt = prompt.replace(tag, replacement)
            else:
                extra_notes.append(f"Replace {slot} with: {replacement}.")

            ref_img = char.get("reference_image")
            if ref_img and Path(str(ref_img)).is_file():
                ref_images.append((slot, str(ref_img)))

        if extra_notes:
            prompt = f"{' '.join(extra_notes)} {prompt}"

    clean_style = style_prompt.strip()
    if clean_style and clean_style.lower() not in prompt.lower():
        prompt = f"{prompt.rstrip('. ')}. Style: {clean_style}"

    return prompt, ref_images


def image_prompt(
    scene: dict[str, Any],
    out_path: Path,
    style_prompt: str = "",
    character_lookup: dict[str, dict[str, Any]] | None = None,
) -> str:
    prompt, char_refs = resolve_scene_prompt(scene, style_prompt, character_lookup)
    reference = scene.get("keyframe")
    head = f"Scene {scene.get('index')} ({scene.get('duration')}s)."
    if reference:
        head += f" Reference frame (for composition and colour only): {reference}"
    lines = [head]
    for slot, img_path in char_refs:
        lines.append(
            f"Character reference image for {slot} (match face, hair, and outfit): {img_path}"
        )
    lines += [
        "",
        "PROMPT:",
        prompt,
        "",
        IMAGE_INSTRUCTIONS.format(out_path=str(out_path)),
    ]
    return "\n".join(lines)


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
    raw_chars = payload.get("characters")
    characters: list[dict[str, str]] = []
    if isinstance(raw_chars, list):
        for idx, item in enumerate(raw_chars, start=1):
            if isinstance(item, dict):
                slot = str(item.get("slot") or f"Char_{idx}").strip()
                desc = str(item.get("description") or "").strip()
                if slot:
                    characters.append({"slot": slot, "description": desc})

    return SceneAnalysis(
        description=description,
        prompt=prompt,
        camera=pick("camera", "camera_notes", "shot"),
        lighting=pick("lighting", "light"),
        characters=characters,
        raw=raw,
    )
