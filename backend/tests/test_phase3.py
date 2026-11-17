"""Phase 3: multi-frame analysis, prompt/response log and scene assets."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import config
from core import jobs, prompt_logger
from providers.base import analyze_prompt, scene_input_images


# --------------------------------------------------------------------------
# prompt_logger
# --------------------------------------------------------------------------
def test_log_event_writes_jsonl_under_data_logs(env):
    entry = prompt_logger.log_event(
        "p_test",
        "scene_001",
        "analyze",
        "agy",
        prompt_sent="hello prompt",
        raw_response='{"prompt": "x"}',
        input_images=["/tmp/a.jpg"],
        parsed={"prompt": "x"},
        duration_ms=1234,
        status="ok",
    )
    path = prompt_logger.log_path("p_test")
    assert path == config.get_data_dir() / "logs" / "p_test.jsonl"
    assert path.is_file()

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    stored = json.loads(lines[0])
    assert stored["scene_id"] == "scene_001"
    assert stored["action"] == "analyze"
    assert stored["engine"] == "agy"
    assert stored["prompt_sent"] == "hello prompt"
    assert stored["input_images"] == ["/tmp/a.jpg"]
    assert stored["duration_ms"] == 1234
    assert stored["status"] == "ok"
    assert stored["timestamp"] == entry["timestamp"]


def test_read_logs_returns_newest_first(env):
    for index in range(3):
        prompt_logger.log_event(
            "p_test", f"scene_00{index}", "generate", "codex", prompt_sent=f"p{index}"
        )
    logs = prompt_logger.read_logs("p_test")
    assert [item["scene_id"] for item in logs] == ["scene_002", "scene_001", "scene_000"]


def test_read_logs_limit_and_missing_file(env):
    for index in range(5):
        prompt_logger.log_event("p_test", f"scene_{index}", "analyze", "agy")
    assert len(prompt_logger.read_logs("p_test", limit=2)) == 2
    assert prompt_logger.read_logs("p_other") == []


def test_log_event_records_errors(env):
    prompt_logger.log_event(
        "p_test", "scene_001", "generate", "agy", status="error", error="boom"
    )
    entry = prompt_logger.read_logs("p_test")[0]
    assert entry["status"] == "error"
    assert entry["error"] == "boom"


def test_log_event_truncates_huge_text(env):
    prompt_logger.log_event("p_test", "scene_001", "analyze", "agy", raw_response="x" * 50000)
    entry = prompt_logger.read_logs("p_test")[0]
    assert len(entry["raw_response"]) < 50000
    assert "truncated" in entry["raw_response"]


def test_log_rejects_path_traversal(env):
    with pytest.raises(prompt_logger.LogError):
        prompt_logger.log_event("../evil", "scene_001", "analyze", "agy")


def test_clear_logs(env):
    prompt_logger.log_event("p_test", "scene_001", "analyze", "agy")
    prompt_logger.clear_logs("p_test")
    assert prompt_logger.read_logs("p_test") == []


# --------------------------------------------------------------------------
# Multi-frame analyze prompt
# --------------------------------------------------------------------------
@pytest.fixture()
def frames(tmp_path):
    first = tmp_path / "first.jpg"
    last = tmp_path / "last.jpg"
    sheet = tmp_path / "sheet.jpg"
    for path in (first, last, sheet):
        path.write_bytes(b"\xff\xd8jpeg")
    return {"keyframe": str(first), "last_keyframe": str(last), "sheet": str(sheet)}


def test_scene_input_images_lists_all_three(frames):
    labels = [label for label, _ in scene_input_images(frames)]
    assert labels == [
        "First Frame",
        "Last Frame",
        "Contact Sheet (frames across the whole shot)",
    ]


def test_scene_input_images_skips_missing_files(frames):
    scene = {"keyframe": frames["keyframe"], "last_keyframe": "/nope/missing.jpg"}
    assert [label for label, _ in scene_input_images(scene)] == ["First Frame"]


def test_analyze_prompt_names_every_frame(frames):
    text = analyze_prompt(
        {"index": 1, "start_time": 0.0, "end_time": 3.0, "duration": 3.0, **frames},
        {"video_name": "clip.mp4"},
    )
    assert "First Frame:" in text
    assert "Last Frame:" in text
    assert "Contact Sheet" in text
    assert frames["last_keyframe"] in text
    assert "difference between" in text


def test_analyze_prompt_without_images_has_no_image_block():
    text = analyze_prompt({"index": 1, "duration": 3.0}, {})
    assert "Read these image files" not in text


def test_video_prompt_instructions_are_flow_specific():
    text = analyze_prompt(
        {"index": 1, "duration": 3.0},
        {"video_prompt_only": True, "video_model": "veo_3_1_lite"},
    )
    assert "25-45 words" in text
    assert "Veo 3.1" in text
    assert "ONE main action" in text
    assert "ONE camera move" in text


# --------------------------------------------------------------------------
# Scene assets: contact sheet is stored per scene
# --------------------------------------------------------------------------
def test_build_scenes_stores_sheet_and_frames(env):
    breakdown_dir = config.get_breakdowns_dir() / "p_test"
    shots_dir = breakdown_dir / "shots"
    shots_dir.mkdir(parents=True, exist_ok=True)
    for name in ("shot_001.jpg", "shot_001_first.jpg", "shot_001_last.jpg"):
        (shots_dir / name).write_bytes(b"\xff\xd8jpeg")

    breakdown = {
        "shots": [
            {
                "index": 1,
                "start": 0.0,
                "end": 3.0,
                "duration": 3.0,
                "assets": {
                    "sheet": "shots/shot_001.jpg",
                    "first_frame": "shots/shot_001_first.jpg",
                    "last_frame": "shots/shot_001_last.jpg",
                },
            }
        ]
    }

    shots, scenes = jobs._build_scenes(
        "p_test", breakdown_dir, breakdown, Path("dummy.mp4"), 10.0
    )
    assert len(scenes) == 1
    scene = scenes[0]
    assert scene["keyframe"].endswith("shot_001_first.jpg")
    assert scene["last_keyframe"].endswith("shot_001_last.jpg")
    assert scene["sheet"].endswith("shot_001.jpg")
    assert shots[0]["sheet"].endswith("shot_001.jpg")


# --------------------------------------------------------------------------
# Endpoint
# --------------------------------------------------------------------------
def test_logs_endpoint(client, env):
    from core import store

    project = store.create(filename="demo.mp4", video_path="", size_bytes=1)
    prompt_logger.log_event(
        project["id"], "scene_001", "analyze", "agy", prompt_sent="p", raw_response="r"
    )
    response = client.get(f"/api/projects/{project['id']}/logs")
    assert response.status_code == 200
    logs = response.json()["logs"]
    assert len(logs) == 1
    assert logs[0]["prompt_sent"] == "p"


def test_logs_endpoint_404_for_unknown_project(client):
    assert client.get("/api/projects/p_missing/logs").status_code == 404
