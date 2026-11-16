"""Phase 4: natural vs replace character mode, last keyframe, and deep analyze."""

from __future__ import annotations

import json
from pathlib import Path

from core import exporter, store
from providers.base import (
    analysis_from_payload,
    analyze_prompt,
    image_prompt,
    resolve_scene_prompt,
    resolve_video_prompt,
    scene_input_images,
)


def test_replace_characters_off_uses_natural_description():
    scene = {
        "id": "scene_001",
        "prompt": "Wide shot of [Char_1] riding down the hill.",
        "last_prompt": "Close-up of [Char_1] smiling.",
        "video_prompt": "Medium shot, [Char_1] rides smoothly downhill, slow tracking shot. Audio: wheels rolling.",
        "detected_characters": [
            {"slot": "Char_1", "description": "pink-haired skater in cream jacket"},
        ],
        "replace_characters": False,
    }
    first, _ = resolve_scene_prompt(scene, style_prompt="", target="first")
    last, _ = resolve_scene_prompt(scene, style_prompt="", target="last")
    video = resolve_video_prompt(scene)

    assert "[Char_1]" not in first
    assert "pink-haired skater in cream jacket" in first
    assert "[Char_1]" not in last
    assert "pink-haired skater in cream jacket" in last
    assert "[Char_1]" not in video
    assert "pink-haired skater in cream jacket" in video


def test_replace_characters_on_keeps_tag_without_db_mapping():
    scene = {
        "id": "scene_001",
        "prompt": "Wide shot of [Char_1] riding.",
        "video_prompt": "[Char_1] skates forward, handheld follow.",
        "detected_characters": [
            {"slot": "Char_1", "description": "pink-haired skater"},
        ],
        "replace_characters": True,
        "character_mappings": {},
    }
    first, _ = resolve_scene_prompt(scene, style_prompt="")
    video = resolve_video_prompt(scene)

    assert "[Char_1]" in first
    assert "[Char_1]" in video


def test_image_prompt_last_target_references_last_and_generated_first(tmp_path: Path):
    first_ref = tmp_path / "first_ref.jpg"
    last_ref = tmp_path / "last_ref.jpg"
    gen_first = tmp_path / "scene_001.png"
    for p in (first_ref, last_ref, gen_first):
        p.write_bytes(b"img")

    scene = {
        "id": "scene_001",
        "index": 1,
        "duration": 3.5,
        "prompt": "First pose",
        "last_prompt": "Final close-up smile",
        "keyframe": str(first_ref),
        "last_keyframe": str(last_ref),
        "image_path": str(gen_first),
    }
    out = tmp_path / "scene_001_last.png"
    text = image_prompt(scene, out, target="last")

    assert "[Last Frame]" in text
    assert str(last_ref) in text
    assert str(gen_first) in text
    assert "Final close-up smile" in text


def test_analysis_from_payload_extracts_last_prompt_and_deep_timeline():
    result = analysis_from_payload(
        {
            "description": "Skater rides down street.",
            "prompt": "First frame still.",
            "last_prompt": "Last frame still.",
            "video_prompt": "Skater carves downhill, smooth tracking shot. Audio: wheels.",
            "deep_timeline": [
                {
                    "time": "0.0s",
                    "action": "crouching on board",
                    "expression": "focused",
                    "camera": "wide eye-level",
                    "background": "alley with vending machines",
                }
            ],
        }
    )
    assert result.last_prompt == "Last frame still."
    assert len(result.deep_timeline) == 1
    assert result.deep_timeline[0]["expression"] == "focused"


def test_deep_analyze_prompt_uses_interval_frames(tmp_path: Path):
    f1 = tmp_path / "f1.jpg"
    f2 = tmp_path / "f2.jpg"
    f1.write_bytes(b"1")
    f2.write_bytes(b"2")

    scene = {"id": "scene_001", "index": 1, "start_time": 0.0, "end_time": 1.0, "duration": 1.0}
    context = {"deep_frames": [(0.0, str(f1)), (0.5, str(f2))]}
    images = scene_input_images(scene, context)
    assert [label for label, _ in images] == ["Frame +0.00s", "Frame +0.50s"]

    prompt = analyze_prompt(scene, context)
    assert "Frame +0.00s" in prompt
    assert "Frame +0.50s" in prompt
    assert "deep_timeline" in prompt


def test_deep_analyze_and_last_image_endpoints(client, tmp_path: Path):
    project = store.create("clip.mp4", str(tmp_path / "clip.mp4"), size_bytes=100)
    last_png = tmp_path / "scene_001_last.png"
    last_png.write_bytes(b"\x89PNG\r\n\x1a\n")

    def add_scene(item):
        item["status"] = "ready"
        item["scenes"] = [
            {
                "id": "scene_001",
                "index": 1,
                "start_time": 0.0,
                "end_time": 3.0,
                "duration": 3.0,
                "shot_indices": [1],
                "is_split": False,
                "prompt": "First still",
                "last_prompt": "Last still",
                "video_prompt": "One action, tracking shot.",
                "last_image_path": str(last_png),
                "last_image_status": "done",
            }
        ]

    store.mutate(project["id"], add_scene)

    resp = client.get(f"/api/projects/{project['id']}/scenes/scene_001/last-image")
    assert resp.status_code == 200
    assert resp.content.startswith(b"\x89PNG")

    prompts_data = json.loads(exporter.build_prompts_json(store.load(project["id"])))
    assert prompts_data["scenes"][0]["last_prompt"] == "Last still"
    assert prompts_data["scenes"][0]["last_keyframe"] == "keyframes/scene_001_last.png"
