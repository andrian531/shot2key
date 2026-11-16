"""Phase 2: dual prompts, last frame, audio stems and the HTML report."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

import config
from core import exporter, store
from providers.base import (
    analysis_from_payload,
    analyze_prompt,
    resolve_scene_prompt,
    resolve_video_prompt,
)


# --------------------------------------------------------------------------
# Providers: dual prompt
# --------------------------------------------------------------------------
def test_analysis_payload_keeps_both_prompts():
    result = analysis_from_payload(
        {
            "description": "A woman walks into a kitchen.",
            "prompt": "still frame, [Char_1] in a kitchen, morning light",
            "video_prompt": "she walks in, camera pushes forward slowly",
            "camera": "medium, eye level",
            "lighting": "soft window light",
        }
    )
    assert result.prompt.startswith("still frame")
    assert result.video_prompt == "she walks in, camera pushes forward slowly"
    assert result.to_dict()["video_prompt"] == result.video_prompt


def test_analysis_payload_without_video_prompt_is_empty():
    result = analysis_from_payload({"description": "x", "prompt": "y"})
    assert result.video_prompt == ""


def test_analyze_prompt_mentions_motion_and_duration():
    text = analyze_prompt(
        {"index": 2, "start_time": 3.0, "end_time": 6.5, "duration": 3.5},
        {"video_name": "clip.mp4"},
    )
    assert "video_prompt" in text
    assert "3.50" in text
    assert "Google Flow" in text


def test_video_prompt_resolves_character_placeholders():
    scene = {
        "id": "scene_001",
        "prompt": "still frame of [Char_1] in a kitchen",
        "video_prompt": "[Char_1] turns and walks away",
        "replace_characters": True,
        "character_mappings": {"Char_1": {"character_id": "char_1", "costume_id": "cos_1"}},
    }
    lookup = {
        "char_1": {
            "name": "Alya",
            "appearance": "young woman, black hair",
            "costumes": [{"id": "cos_1", "name": "Streetwear", "description": "black hoodie"}],
            "reference_image": None,
        }
    }
    assert resolve_video_prompt(scene, lookup) == "Alya, young woman, black hair, wearing black hoodie turns and walks away"
    # the image prompt keeps the style suffix, the motion prompt does not
    image_prompt, _ = resolve_scene_prompt(scene, "cinematic", lookup)
    assert "Style: cinematic" in image_prompt


def test_video_prompt_empty_when_not_analyzed():
    assert resolve_video_prompt({"id": "scene_001"}) == ""


# --------------------------------------------------------------------------
# Fixtures: a project with scenes, stems and a report on disk
# --------------------------------------------------------------------------
@pytest.fixture()
def project_with_assets(env):
    breakdown_dir = config.get_breakdowns_dir() / "p_test"
    (breakdown_dir / "stems").mkdir(parents=True, exist_ok=True)
    (breakdown_dir / "stems" / "original.wav").write_bytes(b"RIFF0000WAVE")
    (breakdown_dir / "stems" / "vocals.wav").write_bytes(b"RIFF0000WAVE")
    (breakdown_dir / "report.html").write_text("<html><body>report</body></html>", encoding="utf-8")

    scene_dir = config.get_outputs_dir() / "p_test" / "scenes"
    scene_dir.mkdir(parents=True, exist_ok=True)
    first = scene_dir / "scene_001_ref.jpg"
    last = scene_dir / "scene_001_last_ref.jpg"
    first.write_bytes(b"\xff\xd8first")
    last.write_bytes(b"\xff\xd8last")

    project = store.create(filename="demo.mp4", video_path="", size_bytes=10)
    scenes = [
        {
            "id": "scene_001",
            "index": 1,
            "start_time": 0.0,
            "end_time": 3.0,
            "duration": 3.0,
            "shot_indices": [1],
            "is_split": False,
            "keyframe": str(first),
            "last_keyframe": str(last),
            "description": "A kitchen.",
            "prompt": "still frame of a kitchen",
            "video_prompt": "camera pushes in slowly",
            "camera": "wide",
            "lighting": "soft",
            "engine": "agy",
            "image_path": None,
            "image_status": "idle",
            "image_error": None,
            "analysis_error": None,
        }
    ]

    def apply(item: dict) -> None:
        item["status"] = "ready"
        item["scenes"] = scenes
        item["shots"] = [{"index": 1, "start": 0.0, "end": 3.0, "duration": 3.0}]
        item["source"] = {"duration": 3.0, "width": 1920, "height": 1080, "fps": 30.0}
        item["breakdown_dir"] = str(breakdown_dir)
        item["audio_stems"] = ["original", "vocals"]
        item["report"] = str(breakdown_dir / "report.html")

    return store.mutate(project["id"], apply)


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------
def test_last_keyframe_endpoint(client, project_with_assets):
    response = client.get(f"/api/projects/{project_with_assets['id']}/scenes/scene_001/last-keyframe")
    assert response.status_code == 200
    assert response.content == b"\xff\xd8last"


def test_last_keyframe_404_when_missing(client, project_with_assets):
    def clear(item: dict) -> None:
        item["scenes"][0]["last_keyframe"] = None

    store.mutate(project_with_assets["id"], clear)
    response = client.get(f"/api/projects/{project_with_assets['id']}/scenes/scene_001/last-keyframe")
    assert response.status_code == 404


def test_patch_scene_video_prompt(client, project_with_assets):
    response = client.patch(
        f"/api/projects/{project_with_assets['id']}/scenes/scene_001",
        json={"video_prompt": "she turns to camera"},
    )
    assert response.status_code == 200
    assert response.json()["scenes"][0]["video_prompt"] == "she turns to camera"
    assert response.json()["scenes"][0]["prompt"] == "still frame of a kitchen"


def test_audio_stem_endpoint(client, project_with_assets):
    response = client.get(f"/api/projects/{project_with_assets['id']}/audio/original")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")

    download = client.get(f"/api/projects/{project_with_assets['id']}/audio/vocals?download=1")
    assert "attachment" in download.headers["content-disposition"]


def test_audio_stem_unknown_and_missing(client, project_with_assets):
    assert client.get(f"/api/projects/{project_with_assets['id']}/audio/drums").status_code == 400
    assert client.get(f"/api/projects/{project_with_assets['id']}/audio/music").status_code == 404


def test_report_endpoint(client, project_with_assets):
    response = client.get(f"/api/projects/{project_with_assets['id']}/report")
    assert response.status_code == 200
    assert "report" in response.text


def test_report_404_when_missing(client, project_with_assets):
    Path(project_with_assets["report"]).unlink()
    assert client.get(f"/api/projects/{project_with_assets['id']}/report").status_code == 404


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------
def test_export_contains_both_prompts_and_last_frame(project_with_assets):
    payload = exporter.build_zip(project_with_assets)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = set(archive.namelist())
        assert "reference/scene_001_last.jpg" in names
        assert "stems/original.wav" in names
        assert "stems/vocals.wav" in names

        prompts = json.loads(archive.read("prompts.json"))
        scene = prompts["scenes"][0]
        assert scene["image_prompt"] == "still frame of a kitchen"
        assert scene["video_prompt"] == "camera pushes in slowly"
        assert scene["last_frame"] == "reference/scene_001_last.jpg"

        video_md = archive.read("VIDEO.md").decode("utf-8")
        assert "Image Prompt" in video_md
        assert "Video Motion Prompt" in video_md
        assert "camera pushes in slowly" in video_md


def test_settings_accepts_max_scene_seconds(client):
    response = client.put("/api/settings", json={"max_scene_seconds": 5})
    assert response.status_code == 200
    assert response.json()["settings"]["max_scene_seconds"] == 5.0

    # out-of-range values are ignored, not stored
    client.put("/api/settings", json={"max_scene_seconds": 999})
    assert client.get("/api/settings").json()["settings"]["max_scene_seconds"] == 5.0
