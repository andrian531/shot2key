"""Phase 5: model-specific video prompt rules and lazy on-demand scene clip endpoint."""

from __future__ import annotations

from pathlib import Path

from core import media, store
from providers.base import analysis_from_payload, analyze_prompt
from providers.video_models import build_model_rules_text, list_video_models


def test_video_models_list_and_rea_prompting_rules():
    models = list_video_models()
    ids = {m["id"] for m in models}
    assert {"omni_1_2", "veo_3_1_lite", "seedance_2_0", "minimax", "kling"} <= ids

    omni_rules = build_model_rules_text("omni_1_2", 3.33)
    assert "In a single continuous shot" in omni_rules
    assert "gemini-omni-flash" in omni_rules

    seedance_rules = build_model_rules_text("seedance_2_0", 4.0)
    assert "Seedance 2.0" in seedance_rules


def test_analyze_prompt_video_prompt_only_mode():
    scene = {
        "id": "scene_001",
        "index": 1,
        "start_time": 0.0,
        "end_time": 3.5,
        "duration": 3.5,
        "description": "A skater rides down a sloped street.",
        "camera": "wide tracking, 28mm",
        "lighting": "overcast daylight",
        "prompt": "First still.",
        "last_prompt": "Last still.",
        "detected_characters": [{"slot": "Char_1", "description": "pink-haired skater"}],
        "deep_timeline": [
            {
                "time": "0.0s",
                "action": "crouching",
                "expression": "focused",
                "camera": "wide",
                "background": "alley",
            }
        ],
    }
    text = analyze_prompt(scene, {"video_prompt_only": True, "video_model": "veo_3_1_lite"})
    assert "Veo 3.1" in text
    assert "Deep Timeline" in text
    assert "pink-haired skater" in text
    assert '{"video_prompt": "..."}' in text

    parsed = analysis_from_payload({"video_prompt": "Wide tracking shot of [Char_1] riding downhill."})
    assert parsed.video_prompt.startswith("Wide tracking shot")


def test_system_status_includes_video_models(client):
    resp = client.get("/api/system/status")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data.get("video_models"), list)
    assert len(data["video_models"]) >= 5


def test_video_prompt_endpoint_validation_and_job(client, monkeypatch, tmp_path: Path):
    from core import jobs

    started: list[tuple[str, str, str, str]] = []
    monkeypatch.setattr(
        jobs,
        "start_video_prompt",
        lambda pid, sid, model, engine: started.append((pid, sid, model, engine)),
    )
    project = store.create("clip.mp4", str(tmp_path / "clip.mp4"), size_bytes=10)
    store.mutate(
        project["id"],
        lambda p: p.update(
            status="ready",
            scenes=[{"id": "scene_001", "index": 1, "start_time": 0.0, "end_time": 3.0, "duration": 3.0}],
        ),
    )

    bad = client.post(
        f"/api/projects/{project['id']}/scenes/scene_001/video-prompt",
        json={"model": "unknown_model", "engine": "agy"},
    )
    assert bad.status_code == 400

    ok = client.post(
        f"/api/projects/{project['id']}/scenes/scene_001/video-prompt",
        json={"model": "seedance_2_0", "engine": "agy"},
    )
    assert ok.status_code == 200
    assert started == [(project["id"], "scene_001", "seedance_2_0", "agy")]


def test_lazy_scene_clip_cuts_once_and_caches(client, monkeypatch, tmp_path: Path):
    src = tmp_path / "source.mp4"
    src.write_bytes(b"fake-source-mp4")
    project = store.create("source.mp4", str(src), size_bytes=15)
    store.mutate(
        project["id"],
        lambda p: p.update(
            status="ready",
            scenes=[{"id": "scene_001", "index": 1, "start_time": 1.0, "end_time": 4.0, "duration": 3.0}],
        ),
    )

    calls: list[Path] = []

    def fake_cut(video, start, end, out_path):
        calls.append(Path(out_path))
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_bytes(b"ftypmp42-fake-clip")
        return Path(out_path)

    monkeypatch.setattr(media, "cut_scene_clip", fake_cut)

    r1 = client.get(f"/api/projects/{project['id']}/scenes/scene_001/clip")
    assert r1.status_code == 200
    assert r1.content == b"ftypmp42-fake-clip"
    assert len(calls) == 1

    # Second request uses the cached clip without invoking ffmpeg again.
    r2 = client.get(f"/api/projects/{project['id']}/scenes/scene_001/clip?download=1")
    assert r2.status_code == 200
    assert "attachment" in r2.headers.get("content-disposition", "")
    assert len(calls) == 1
