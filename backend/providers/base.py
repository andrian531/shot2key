"""Provider contracts shared by the API and CLI engines."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from providers.video_models import build_model_rules_text, get_video_model


class ProviderError(RuntimeError):
    """A provider could not produce a result (missing key, CLI failure, ...)."""


@dataclass
class SceneAnalysis:
    """What an analyzer returns for one scene."""

    description: str = ""
    #: Dense image prompt for the still keyframe (Google Flow "First Frame").
    prompt: str = ""
    #: Dense image prompt for the closing keyframe (Google Flow "Last Frame").
    last_prompt: str = ""
    #: Motion prompt for image-to-video (Omni 1.2 Flash / Veo 3.1 Lite).
    video_prompt: str = ""
    camera: str = ""
    lighting: str = ""
    characters: list[dict[str, str]] = field(default_factory=list)
    deep_timeline: list[dict[str, str]] = field(default_factory=list)
    raw: str = ""
    #: The exact prompt handed to the engine (logged for inspection).
    prompt_sent: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "prompt": self.prompt,
            "last_prompt": self.last_prompt,
            "video_prompt": self.video_prompt,
            "camera": self.camera,
            "lighting": self.lighting,
            "characters": self.characters,
            "deep_timeline": self.deep_timeline,
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
  "prompt": "a dense IMAGE prompt (max 90 words) for the First Frame: shot size, subject, wardrobe, props, setting, lens (e.g. 35mm), lighting, colour grade. Never use AI buzzwords (hyperrealistic, photorealistic, 8k, masterpiece). Refer to recurring people with [Char_1], [Char_2].",
  "last_prompt": "a dense IMAGE prompt (max 90 words) for the Last Frame, keeping the same [Char_1], [Char_2] identity, wardrobe and setting while reflecting the final pose, expression and framing at the end of the shot. No AI buzzwords.",
  "video_prompt": "a MOTION prompt of 25-45 words tuned for Google Flow (Omni 1.2 Flash / Veo 3.1 Lite) for a {duration}-second continuous shot. Follow this order: [Shot type], [Char_1/subject] performs ONE main action flowing from First Frame to Last Frame, [ONE clear camera move such as slow push-in, lateral tracking, pan left/right, handheld follow, or locked-off], [brief mood/light]. Audio: [short ambient or SFX cue]. Never use AI buzzwords, cuts, or stacked multi-actions.",
  "camera": "shot size + angle + lens, e.g. 'medium close-up, eye level, 50mm'",
  "lighting": "lighting setup and colour temperature in a few words",
  "characters": [
    {"slot": "Char_1", "description": "concise visual description of this person (age, hair, outfit)"}
  ]
}
Write the values in English. If no people appear, set "characters" to []. Do not invent text overlays or logos."""

DEEP_ANALYZE_EXTRA = """\
You are also given sequential frames sampled every ~0.5s across this scene.
Also include a "deep_timeline" key in the JSON object:
  "deep_timeline": [
    {"time": "0.0s", "action": "body pose / movement", "expression": "facial expression or gaze", "camera": "framing / motion", "background": "key background change"}
  ]
Use those frame-by-frame observations to make "prompt" (First Frame), "last_prompt" (Last Frame), and "video_prompt" maximally accurate in expression, gesture, and camera path."""


#: Scene fields that hold a reference image, in the order the model should read them.
SCENE_IMAGE_FIELDS: tuple[tuple[str, str], ...] = (
    ("keyframe", "First Frame"),
    ("last_keyframe", "Last Frame"),
    ("sheet", "Contact Sheet (frames across the whole shot)"),
)


def scene_input_images(
    scene: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> list[tuple[str, str]]:
    """Reference images for a scene as ``[(label, path), ...]``."""
    deep_frames = (context or {}).get("deep_frames") or []
    if deep_frames:
        found_deep: list[tuple[str, str]] = []
        for offset, img_path in deep_frames:
            path = Path(str(img_path))
            if path.is_file():
                found_deep.append((f"Frame +{float(offset):.2f}s", str(path)))
        if found_deep:
            return found_deep

    found: list[tuple[str, str]] = []
    for field_name, label in SCENE_IMAGE_FIELDS:
        value = scene.get(field_name)
        if not value:
            continue
        path = Path(str(value))
        if path.is_file():
            found.append((label, str(path)))
    return found


def analyze_prompt(scene: dict[str, Any], context: dict[str, Any]) -> str:
    """Text prompt handed to a CLI agent or an API model for one scene."""
    if context.get("video_prompt_only"):
        return _video_prompt_for_model(scene, context)

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
    images = scene_input_images(scene, context)
    if images:
        lines.append("")
        lines.append("Read these image files before answering:")
        for label, path in images:
            lines.append(f"- {label}: {path}")
        if len(images) > 1:
            lines.append(
                "Compare the frames from start to end (the difference between them "
                "is the motion the video prompt must describe): capture the real motion, "
                "expression shifts, and camera path."
            )
    duration = scene.get("duration") or 0
    lines += ["", ANALYZE_INSTRUCTIONS.replace("{duration}", f"{float(duration):.2f}")]
    if context.get("deep_frames"):
        lines += ["", DEEP_ANALYZE_EXTRA]
    return "\n".join(lines)


def _video_prompt_for_model(scene: dict[str, Any], context: dict[str, Any]) -> str:
    model_id = str(context.get("video_model") or "omni_1_2")
    spec = get_video_model(model_id)
    duration = float(scene.get("duration") or 0)
    lines = [
        "You are an expert AI video prompt engineer.",
        f"Convert the stored scene data below into a single production-ready video prompt for {spec.label if spec else model_id}.",
        "",
        f"Scene {scene.get('index')} | Duration: {duration:.2f}s "
        f"({scene.get('start_time')}s - {scene.get('end_time')}s).",
    ]
    if scene.get("description"):
        lines.append(f"Scene description: {scene['description']}")
    if scene.get("camera"):
        lines.append(f"Camera: {scene['camera']}")
    if scene.get("lighting"):
        lines.append(f"Lighting: {scene['lighting']}")
    if scene.get("prompt"):
        lines.append(f"First Frame summary: {scene['prompt']}")
    if scene.get("last_prompt"):
        lines.append(f"Last Frame summary: {scene['last_prompt']}")
    chars = scene.get("detected_characters") or []
    if chars:
        lines.append("Detected characters:")
        for c in chars:
            if isinstance(c, dict) and c.get("slot"):
                lines.append(f"- [{c['slot']}]: {c.get('description', '')}")
    timeline = scene.get("deep_timeline") or []
    if timeline:
        lines.append("Deep Timeline (0.5s beats):")
        for beat in timeline:
            if isinstance(beat, dict):
                lines.append(
                    f"- {beat.get('time', '')}: action={beat.get('action', '')}; "
                    f"expression={beat.get('expression', '')}; camera={beat.get('camera', '')}"
                )
    images = scene_input_images(scene)
    if images:
        lines.append("")
        lines.append("Reference frames (for visual verification if accessible):")
        for label, path in images[:2]:
            lines.append(f"- {label}: {path}")
    if spec:
        lines += [
            "",
            "MODEL-SPECIFIC PROMPTING RULES:",
            build_model_rules_text(model_id, duration),
        ]
    lines += [
        "",
        'Return ONLY a JSON object, no prose, no markdown fence: {"video_prompt": "..."}',
        "Write the value in English.",
    ]
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


def _naturalize_placeholders(text: str, scene: dict[str, Any]) -> str:
    """Replace ``[Char_N]`` tags with natural descriptions from ``detected_characters``."""
    for item in scene.get("detected_characters") or []:
        if not isinstance(item, dict):
            continue
        slot = str(item.get("slot") or "").strip()
        desc = str(item.get("description") or "").strip()
        if not slot or not desc:
            continue
        text = text.replace(f"[{slot}]", desc)
    return text


def _apply_character_replacements(
    text: str,
    scene: dict[str, Any],
    character_lookup: dict[str, dict[str, Any]] | None,
) -> tuple[str, list[tuple[str, str]]]:
    """Resolve ``[Char_1]`` tags based on ``replace_characters``.

    - When ``replace_characters`` is False: swap ``[Char_N]`` for natural
      descriptions from ``detected_characters`` so raw tags never leak.
    - When ``replace_characters`` is True: keep ``[Char_N]`` tags (or swap
      mapped Character Cards if any exist in ``character_lookup``).
    """
    ref_images: list[tuple[str, str]] = []
    if not scene.get("replace_characters"):
        return _naturalize_placeholders(text, scene), ref_images

    if not character_lookup:
        return text, ref_images

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
        if tag in text:
            text = text.replace(tag, replacement)
        else:
            extra_notes.append(f"Replace {slot} with: {replacement}.")

        ref_img = char.get("reference_image")
        if ref_img and Path(str(ref_img)).is_file():
            ref_images.append((slot, str(ref_img)))

    if extra_notes:
        text = f"{' '.join(extra_notes)} {text}"

    return text, ref_images


def resolve_scene_prompt(
    scene: dict[str, Any],
    style_prompt: str = "",
    character_lookup: dict[str, dict[str, Any]] | None = None,
    target: str = "first",
) -> tuple[str, list[tuple[str, str]]]:
    """Resolve character/costume placeholders and append default style prompt.

    Returns ``(resolved_prompt, [(slot, ref_image_path), ...])``.
    """
    if target == "last":
        prompt = (
            scene.get("last_prompt")
            or scene.get("prompt")
            or scene.get("description")
            or ""
        ).strip()
    else:
        prompt = (scene.get("prompt") or scene.get("description") or "").strip()
    if not prompt:
        raise ProviderError(
            f"Scene {scene.get('id')} belum punya prompt. Jalankan Analyze dulu atau isi prompt manual."
        )

    prompt, ref_images = _apply_character_replacements(prompt, scene, character_lookup)

    clean_style = style_prompt.strip()
    if clean_style and clean_style.lower() not in prompt.lower():
        prompt = f"{prompt.rstrip('. ')}. Style: {clean_style}"

    return prompt, ref_images


def resolve_video_prompt(
    scene: dict[str, Any],
    character_lookup: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Resolve ``[Char_N]`` placeholders in the motion prompt (no style suffix)."""
    text = (scene.get("video_prompt") or "").strip()
    if not text:
        return ""
    text, _ = _apply_character_replacements(text, scene, character_lookup)
    return text


def image_prompt(
    scene: dict[str, Any],
    out_path: Path,
    style_prompt: str = "",
    character_lookup: dict[str, dict[str, Any]] | None = None,
    target: str = "first",
) -> str:
    prompt, char_refs = resolve_scene_prompt(
        scene, style_prompt, character_lookup, target=target
    )
    if target == "last":
        reference = scene.get("last_keyframe") or scene.get("keyframe")
        frame_label = "Last Frame"
    else:
        reference = scene.get("keyframe")
        frame_label = "First Frame"

    head = f"Scene {scene.get('index')} ({scene.get('duration')}s) [{frame_label}]."
    if reference:
        head += f" Reference frame (for composition and colour only): {reference}"
    lines = [head]
    if target == "last" and scene.get("image_path") and Path(str(scene["image_path"])).is_file():
        lines.append(
            f"Generated First Keyframe (keep character, wardrobe and lighting consistent with this image): {scene['image_path']}"
        )
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
    video_prompt = pick("video_prompt", "motion_prompt", "video", "motion")
    if not prompt and description:
        prompt = description
    if not description and prompt:
        description = prompt
    if not prompt and not video_prompt:
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

    raw_timeline = payload.get("deep_timeline")
    deep_timeline: list[dict[str, str]] = []
    if isinstance(raw_timeline, list):
        for item in raw_timeline:
            if not isinstance(item, dict):
                continue
            deep_timeline.append(
                {
                    "time": str(item.get("time") or "").strip(),
                    "action": str(item.get("action") or "").strip(),
                    "expression": str(item.get("expression") or "").strip(),
                    "camera": str(item.get("camera") or "").strip(),
                    "background": str(item.get("background") or "").strip(),
                }
            )

    return SceneAnalysis(
        description=description,
        prompt=prompt,
        last_prompt=pick("last_prompt", "last_image_prompt", "end_prompt"),
        video_prompt=video_prompt,
        camera=pick("camera", "camera_notes", "shot"),
        lighting=pick("lighting", "light"),
        characters=characters,
        deep_timeline=deep_timeline,
        raw=raw,
    )
