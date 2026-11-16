"""API smoke tests: status, upload, scene editing, export."""

from __future__ import annotations

import io
import json
import zipfile

import pytest

from core import store


@pytest.fixture()
def no_decompose(monkeypatch):
    """Upload must not spawn a real rea-video run during tests."""
    from core import jobs

    started: list[str] = []
    monkeypatch.setattr(jobs, "start_decompose", lambda project_id: started.append(project_id))
    return started


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_system_status_reports_every_dependency(client):
    payload = client.get("/api/system/status").json()
    for key in ("rea_video", "ffmpeg", "agy", "codex"):
        assert key in payload
        assert "available" in payload[key]
    assert payload["max_scene_seconds"] == 10.0
    assert set(payload["engines"]["image_engines"]) == {"agy", "codex"}


def test_upload_rejects_unsupported_extension(client):
    response = client.post(
        "/api/projects/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert ".mp4" in response.json()["detail"]


def test_upload_creates_project_and_starts_decompose(client, no_decompose):
    response = client.post(
        "/api/projects/upload",
        files={"file": ("clip.mp4", b"\x00" * 2048, "video/mp4")},
    )
    assert response.status_code == 201
    project = response.json()
    assert project["status"] == "uploaded"
    assert project["filename"] == "clip.mp4"
    assert no_decompose == [project["id"]]

    listed = client.get("/api/projects").json()["projects"]
    assert [item["id"] for item in listed] == [project["id"]]

    fetched = client.get(f"/api/projects/{project['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["size_bytes"] == 2048


def test_unknown_project_returns_404(client):
    assert client.get("/api/projects/p_missing").status_code == 404


def _project_with_scenes() -> dict:
    project = store.create(filename="demo.mp4", video_path="", size_bytes=10)
    scenes = [
        {
            "id": "scene_001",
            "index": 1,
            "start_time": 0.0,
            "end_time": 9.0,
            "duration": 9.0,
            "shot_indices": [1, 2],
            "is_split": False,
            "keyframe": None,
            "description": "A wide shot of a kitchen.",
            "prompt": "wide shot, kitchen, morning light",
            "camera": "wide, eye level",
            "lighting": "soft window light",
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
        item["shots"] = [{"index": 1, "start": 0.0, "end": 9.0, "duration": 9.0}]
        item["source"] = {"duration": 9.0, "width": 1920, "height": 1080, "fps": 30.0}

    return store.mutate(project["id"], apply)


def test_patch_scene_prompt(client):
    project = _project_with_scenes()
    response = client.patch(
        f"/api/projects/{project['id']}/scenes/scene_001",
        json={"prompt": "edited prompt"},
    )
    assert response.status_code == 200
    scene = response.json()["scenes"][0]
    assert scene["prompt"] == "edited prompt"
    assert scene["description"] == "A wide shot of a kitchen."


def test_generate_requires_a_prompt(client):
    project = _project_with_scenes()
    client.patch(f"/api/projects/{project['id']}/scenes/scene_001", json={"prompt": ""})
    response = client.post(
        f"/api/projects/{project['id']}/scenes/scene_001/generate",
        json={"engine": "agy"},
    )
    assert response.status_code == 409


def test_generate_rejects_unknown_engine(client):
    project = _project_with_scenes()
    response = client.post(
        f"/api/projects/{project['id']}/scenes/scene_001/generate",
        json={"engine": "dalle"},
    )
    assert response.status_code == 400


def test_analyze_rejects_unknown_engine(client):
    project = _project_with_scenes()
    response = client.post(
        f"/api/projects/{project['id']}/analyze", json={"engine": "nope"}
    )
    assert response.status_code == 400


def test_analyze_starts_a_background_job(client, monkeypatch):
    """The endpoint must spawn the job on the running loop, not in a threadpool."""
    from core import jobs

    started: list[tuple[str, str]] = []
    monkeypatch.setattr(
        jobs, "start_analyze", lambda pid, engine, scene_ids=None: started.append((pid, engine))
    )
    project = _project_with_scenes()
    response = client.post(f"/api/projects/{project['id']}/analyze", json={"engine": "agy"})
    assert response.status_code == 200
    assert response.json()["status"] == "started"
    assert started == [(project["id"], "agy")]


def test_generate_starts_a_background_job(client, monkeypatch):
    from core import jobs

    started: list[tuple[str, list[str], str]] = []
    monkeypatch.setattr(
        jobs,
        "start_generate",
        lambda pid, scene_ids, engine: started.append((pid, list(scene_ids), engine)),
    )
    project = _project_with_scenes()
    response = client.post(
        f"/api/projects/{project['id']}/scenes/scene_001/generate", json={"engine": "codex"}
    )
    assert response.status_code == 200
    assert started == [(project["id"], ["scene_001"], "codex")]

    response = client.post(
        f"/api/projects/{project['id']}/generate-all", json={"engine": "agy"}
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_export_zip_contains_prompts_and_video_md(client):
    project = _project_with_scenes()
    response = client.get(f"/api/projects/{project['id']}/export")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = set(archive.namelist())
        assert {"prompts.json", "VIDEO.md", "storyboard.json"} <= names
        prompts = json.loads(archive.read("prompts.json"))
        assert prompts["scenes"][0]["prompt"] == "wide shot, kitchen, morning light"
        video_md = archive.read("VIDEO.md").decode("utf-8")
        assert "Scene 1" in video_md
        assert "wide shot, kitchen, morning light" in video_md


def test_settings_roundtrip_masks_secrets(client):
    response = client.put("/api/settings", json={"gemini_api_key": "secret-key"})
    assert response.status_code == 200
    assert response.json()["settings"]["gemini_api_key"] == ""
    assert response.json()["settings"]["gemini_api_key_set"] is True

    status = client.get("/api/system/status").json()
    assert status["api_keys"]["gemini"] is True
