"""Model-specific video prompting rules, loaded from rea-video's capabilities/prompting.yaml."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class VideoModelSpec:
    id: str
    label: str
    provider: str
    rea_key: str
    instructions: str


VIDEO_MODELS: tuple[VideoModelSpec, ...] = (
    VideoModelSpec(
        id="omni_1_2",
        label="Omni 1.2 Flash (Google Flow)",
        provider="Google Flow",
        rea_key="gemini-omni-flash",
        instructions=(
            "Target model: Google Flow Omni 1.2 Flash (3-15s continuous shots).\n"
            "- IMPORTANT: Omni cuts scenes automatically unless told otherwise. Always include 'In a single continuous shot, no scene cuts.'\n"
            "- With First + Last frames (3-10s), focus on the sequential transition and motion between them; supports '[0-3s] ... [3-6s] ...' or 'After X seconds, ...' beats.\n"
            "- Describe lighting, camera movement, and sound design ('Sound design: ... No dialogue.' or 'Name says: ...' with colon, no quotes).\n"
            "- Keep recurring people tagged as [Char_1], [Char_2]. Never use AI buzzwords."
        ),
    ),
    VideoModelSpec(
        id="veo_3_1_lite",
        label="Veo 3.1 - Lite (Google Flow)",
        provider="Google Flow",
        rea_key="veo-3.1",
        instructions=(
            "Target model: Google Veo 3.1 Lite.\n"
            "- Length: 25-45 words.\n"
            "- Structure: [Cinematography] + [Subject / Char_1] + [ONE main action] + [Context] + [Style & Ambiance].\n"
            "- In First/Last frame mode, images already define subject, scene, and style — write ONLY the motion/transition, ONE camera move (static, pan, tilt, dolly, truck, handheld, arc), and sound ('SFX: ...' / 'Ambient noise: ...').\n"
            "- Keep recurring people tagged as [Char_1], [Char_2]. No AI buzzwords, no quotes around dialogue (use colon)."
        ),
    ),
    VideoModelSpec(
        id="seedance_2_0",
        label="Seedance 2.0",
        provider="ByteDance Seedance",
        rea_key="seedance-2.0",
        instructions=(
            "Target model: Seedance 2.0.\n"
            "- Structure: Precise subject + motion details + environment + lighting/colour tone + ONE camera movement + visual style + constraints.\n"
            "- IMPORTANT: Do NOT write explicit second timestamps (like '0-3s' or 'at 2.5s') in Seedance 2.0 prompts.\n"
            "- Keep recurring people tagged as [Char_1], [Char_2].\n"
            "- End with constraints: 'No subtitles, no on-screen text, no logo, no watermark.'"
        ),
    ),
    VideoModelSpec(
        id="minimax",
        label="MiniMax (Hailuo)",
        provider="MiniMax",
        rea_key="hailuo-2.3",
        instructions=(
            "Target model: MiniMax / Hailuo image-to-video.\n"
            "- Length: 30-55 words focusing on physical momentum, secondary motion (hair/fabric), and spatial progression from First to Last Frame.\n"
            "- Specify ONE camera movement clearly (e.g., [Tracking shot], [Push in], [Pan left], or [Static shot]).\n"
            "- Keep recurring people tagged as [Char_1], [Char_2]. No AI buzzwords."
        ),
    ),
    VideoModelSpec(
        id="kling",
        label="Kling AI",
        provider="Kuaishou Kling",
        rea_key="kling-4.0",
        instructions=(
            "Target model: Kling AI image-to-video (First/Last frame bridge).\n"
            "- Separate foreground subject motion from background parallax, describe ONE smooth camera trajectory, and write 'No cuts.' if single shot.\n"
            "- Anchor what changes between First and Last Frame while keeping identity/layout stable.\n"
            "- Keep recurring people tagged as [Char_1], [Char_2]. End with 'No text, no watermark.'"
        ),
    ),
)

VIDEO_MODEL_MAP: dict[str, VideoModelSpec] = {spec.id: spec for spec in VIDEO_MODELS}
DEFAULT_VIDEO_MODEL = "omni_1_2"


@lru_cache(maxsize=1)
def _load_rea_prompting() -> dict[str, Any]:
    """Load `capabilities/prompting.yaml` from the installed `rea_video` package."""
    try:
        import rea_video  # type: ignore[import-untyped]

        path = Path(rea_video.__file__).resolve().parent / "capabilities" / "prompting.yaml"
        if path.is_file():
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data.get("models") or {}
    except Exception:
        pass
    return {}


def build_model_rules_text(model_id: str, duration: float) -> str:
    """Combine concise English rules with `rea-video`'s built-in prompting.yaml specs."""
    spec = VIDEO_MODEL_MAP.get(model_id) or VIDEO_MODEL_MAP[DEFAULT_VIDEO_MODEL]
    lines = [spec.instructions.replace("{duration}", f"{duration:.2f}")]

    rea_models = _load_rea_prompting()
    rea_entry = rea_models.get(spec.rea_key)
    if isinstance(rea_entry, dict):
        lines.append("")
        lines.append(f"Reference vendor guide from rea-video ({spec.rea_key}):")
        for key in ("structure", "multi_shot", "frame_mode", "camera", "dialogue", "negatives"):
            val = rea_entry.get(key)
            if isinstance(val, str) and val.strip():
                lines.append(f"- {key}: {val.strip()}")
    return "\n".join(lines)


def list_video_models() -> list[dict[str, str]]:
    return [
        {"id": spec.id, "label": spec.label, "provider": spec.provider}
        for spec in VIDEO_MODELS
    ]


def get_video_model(model_id: str) -> VideoModelSpec | None:
    return VIDEO_MODEL_MAP.get(model_id)
