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

    # Default Analyze leaves video_prompt out so it stays empty until generated per model.
    default_analyze = analyze_prompt(scene, {})
    assert '"video_prompt"' not in default_analyze

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


def test_partial_replace_slots_naturalizes_unchecked_char():
    from providers.base import resolve_scene_prompt, resolve_video_prompt

    scene = {
        "id": "scene_001",
        "prompt": "[Char_1] skates past [Char_3] holding a camera.",
        "video_prompt": "[Char_1] glides downhill past [Char_3].",
        "detected_characters": [
            {"slot": "Char_1", "description": "pink-haired skater"},
            {"slot": "Char_3", "description": "male camera operator in black"},
        ],
        "replace_characters": True,
        "replace_slots": ["Char_1"],
    }
    first, _ = resolve_scene_prompt(scene, style_prompt="")
    video = resolve_video_prompt(scene)

    assert "[Char_1]" in first
    assert "[Char_3]" not in first
    assert "male camera operator in black" in first
    assert "[Char_1]" in video
    assert "[Char_3]" not in video
    assert "male camera operator in black" in video


def test_video_prompt_respects_replace_characters_and_deep_timeline_background():
    base_scene = {
        "id": "scene_001",
        "index": 1,
        "start_time": 0.0,
        "end_time": 3.0,
        "duration": 3.0,
        "description": "Skater moves down the street.",
        "detected_characters": [
            {"slot": "Char_1", "description": "pink-haired skater"},
            {"slot": "Char_2", "description": "camera operator"},
        ],
        "deep_timeline": [
            {
                "time": "0.5s",
                "action": "pushes off",
                "expression": "smiling",
                "camera": "low tracking",
                "background": "neon storefront",
            }
        ],
        "replace_characters": False,
    }
    off_prompt = analyze_prompt(base_scene, {"video_prompt_only": True, "video_model": "omni_1_2"})
    assert "Character tagging is OFF" in off_prompt
    assert "background=neon storefront" in off_prompt
    assert "0.5s Deep Timeline is provided above" in off_prompt

    on_partial = {**base_scene, "replace_characters": True, "replace_slots": ["Char_1"]}
    on_prompt = analyze_prompt(on_partial, {"video_prompt_only": True, "video_model": "omni_1_2"})
    assert "Character tagging is ON for [Char_1]" in on_prompt


def test_video_prompt_saved_per_model_with_metadata(client, monkeypatch, tmp_path: Path):
    import asyncio
    from core import jobs
    from providers import registry
    from providers.base import SceneAnalysis

    class FakeAnalyzer:
        name = "fake"

        async def analyze(self, scene, context):
            model = context.get("video_model")
            return SceneAnalysis(
                description="d",
                prompt="p",
                video_prompt=f"generated for {model}",
                raw="{}",
            )

    monkeypatch.setattr(registry, "analyzer", lambda engine: FakeAnalyzer())

    project = store.create("clip.mp4", str(tmp_path / "clip.mp4"), size_bytes=10)
    store.mutate(
        project["id"],
        lambda p: p.update(
            status="ready",
            scenes=[
                {
                    "id": "scene_001",
                    "index": 1,
                    "start_time": 0.0,
                    "end_time": 3.0,
                    "duration": 3.0,
                    "description": "d",
                    "prompt": "p",
                    "last_prompt": "",
                    "video_prompt": "",
                    "video_model": "omni_1_2",
                    "video_prompts": {},
                    "deep_timeline": [{"time": "0.0s", "action": "idle"}],
                    "deep_version": 2,
                    "detected_characters": [
                        {"slot": "Char_1", "description": "skater"},
                        {"slot": "Char_2", "description": "friend"},
                    ],
                    "replace_characters": False,
                    "replace_slots": None,
                }
            ],
        ),
    )

    # 1. Generate for omni_1_2 with replace_characters OFF
    asyncio.run(jobs._run_video_prompt(project["id"], "scene_001", "omni_1_2", "agy"))
    loaded = store.load(project["id"])["scenes"][0]
    assert loaded["video_prompts"]["omni_1_2"] == {
        "prompt": "generated for omni_1_2",
        "replace_characters": False,
        "replace_slots": [],
        "used_deep_timeline": True,
        "deep_version": 2,
    }

    # 2. Generate for seedance_2_0 with replace_characters ON (Char_1 only)
    client.patch(
        f"/api/projects/{project['id']}/scenes/scene_001",
        json={"replace_characters": True, "replace_slots": ["Char_1"]},
    )
    asyncio.run(jobs._run_video_prompt(project["id"], "scene_001", "seedance_2_0", "agy"))
    loaded = store.load(project["id"])["scenes"][0]
    assert loaded["video_prompts"]["omni_1_2"]["replace_characters"] is False
    assert loaded["video_prompts"]["seedance_2_0"] == {
        "prompt": "generated for seedance_2_0",
        "replace_characters": True,
        "replace_slots": ["Char_1"],
        "used_deep_timeline": True,
        "deep_version": 2,
    }

    # 3. Manual PATCH keeps per-model prompts isolated
    patch_resp = client.patch(
        f"/api/projects/{project['id']}/scenes/scene_001",
        json={"video_prompt": "edited seedance", "video_model": "seedance_2_0"},
    )
    assert patch_resp.status_code == 200
    scene_after = patch_resp.json()["scenes"][0]
    assert scene_after["video_prompts"]["seedance_2_0"]["prompt"] == "edited seedance"
    assert scene_after["video_prompts"]["omni_1_2"]["prompt"] == "generated for omni_1_2"


def test_cli_list_models_and_model_flags(monkeypatch, tmp_path: Path):
    import json as json_mod
    from types import SimpleNamespace
    from providers import cli_provider

    # agy models parsing
    monkeypatch.setattr(cli_provider, "cli_path", lambda engine: f"/fake/{engine}")
    monkeypatch.setattr(
        cli_provider.subprocess,
        "run",
        lambda *a, **kw: SimpleNamespace(
            returncode=0,
            stdout="Fetching available models...\ngemini-4-argon-medium\tGemini 4 Argon\nclaude-opus-5-5-high\tClaude\n",
            stderr="",
        ),
    )
    assert cli_provider.list_models("agy") == [
        "default",
        "gemini-4-argon-medium",
        "claude-opus-5-5-high",
    ]

    # codex ~/.codex/models_cache.json parsing
    fake_home = tmp_path / "home"
    (fake_home / ".codex").mkdir(parents=True)
    (fake_home / ".codex" / "models_cache.json").write_text(
        json_mod.dumps({"models": [{"slug": "gpt-6.1-sol"}, {"slug": "gpt-5.6-sol"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    assert cli_provider.list_models("codex") == ["default", "gpt-6.1-sol", "gpt-5.6-sol"]

    # Verify --model and -m flags passed only when non-default
    seen_cmds: list[list[str]] = []

    def fake_run(cmd, cwd, timeout, stdin_text=None):
        seen_cmds.append(list(cmd))
        return SimpleNamespace(returncode=0, stdout='{"prompt":"ok"}', stderr="")

    monkeypatch.setattr(cli_provider, "_run", fake_run)
    cli_provider._run_agy("hello", tmp_path, 30, model="gemini-4-argon-medium")
    cli_provider._run_agy("hello", tmp_path, 30, model="default")
    cli_provider._run_codex("hello", tmp_path, 30, model="gpt-6.1-sol")
    cli_provider._run_codex("hello", tmp_path, 30, model="default")

    assert "--model" in seen_cmds[0] and "gemini-4-argon-medium" in seen_cmds[0]
    assert "--model" not in seen_cmds[1]
    assert "-m" in seen_cmds[2] and "gpt-6.1-sol" in seen_cmds[2]
    assert "-m" not in seen_cmds[3]


def test_settings_cli_models_and_fallback_execution(client, monkeypatch):
    import asyncio
    from providers import cli_provider, registry
    from providers.base import ProviderError, SceneAnalysis

    monkeypatch.setattr(cli_provider, "list_models", lambda eng: ["default", f"{eng}-m1"])
    monkeypatch.setattr(cli_provider, "cli_path", lambda eng: f"/bin/{eng}")

    r_models = client.get("/api/settings/cli-models/agy")
    assert r_models.status_code == 200
    assert r_models.json()["models"] == ["default", "agy-m1"]
    assert client.get("/api/settings/cli-models/unknown").status_code == 400

    put_resp = client.put(
        "/api/settings",
        json={
            "default_analyzer": "agy",
            "agy_model": "gemini-4-argon-medium",
            "codex_model": "gpt-6.1-sol",
            "fallback_analyzer": "codex",
            "fallback_model": "gpt-6.1-sol",
        },
    )
    assert put_resp.status_code == 200
    saved = put_resp.json()["settings"]
    assert saved["agy_model"] == "gemini-4-argon-medium"
    assert saved["fallback_analyzer"] == "codex"
    assert saved["fallback_model"] == "gpt-6.1-sol"

    calls: list[tuple[str, str]] = []

    class FakeAnalyzer:
        def __init__(self, engine: str):
            self.engine = engine

        async def analyze(self, scene, context):
            model = context.get("model", "")
            calls.append((self.engine, model))
            if self.engine == "agy":
                raise ProviderError("rate limited")
            return SceneAnalysis(description="ok", prompt="p", raw="{}")

    monkeypatch.setattr(registry, "analyzer", lambda eng: FakeAnalyzer(eng))

    result, used_engine, used_model, fb_reason = asyncio.run(
        registry.run_analyze_with_fallback({"id": "scene_001"}, {}, "agy")
    )
    assert calls == [("agy", "gemini-4-argon-medium"), ("codex", "gpt-6.1-sol")]
    assert used_engine == "codex"
    assert used_model == "gpt-6.1-sol"
    assert fb_reason and "agy (gemini-4-argon-medium)" in fb_reason
    assert result.prompt == "p"


def test_logs_include_provider_model_and_fallback(client, monkeypatch, tmp_path: Path):
    import asyncio
    from core import jobs, prompt_logger
    from providers import registry
    from providers.base import ProviderError, SceneAnalysis

    client.put(
        "/api/settings",
        json={
            "default_analyzer": "agy",
            "agy_model": "gemini-4-argon-medium",
            "fallback_analyzer": "codex",
            "fallback_model": "gpt-6.1-sol",
        },
    )

    project = store.create("clip.mp4", str(tmp_path / "clip.mp4"), size_bytes=10)
    store.mutate(
        project["id"],
        lambda p: p.update(
            status="ready",
            scenes=[
                {
                    "id": "scene_001",
                    "index": 1,
                    "start_time": 0.0,
                    "end_time": 3.0,
                    "duration": 3.0,
                    "description": "",
                    "prompt": "",
                    "last_prompt": "",
                    "video_prompt": "",
                    "camera": "",
                    "lighting": "",
                }
            ],
        ),
    )

    class FallbackAnalyzer:
        def __init__(self, engine: str):
            self.engine = engine

        async def analyze(self, scene, context):
            if self.engine == "agy":
                raise ProviderError("agy quota exceeded")
            return SceneAnalysis(description="d", prompt="p", raw="{}")

    monkeypatch.setattr(registry, "analyzer", lambda eng: FallbackAnalyzer(eng))
    asyncio.run(jobs._run_analyze(project["id"], "agy", None))

    logs = prompt_logger.read_logs(project["id"])
    assert len(logs) == 1
    assert logs[0]["status"] == "ok"
    assert logs[0]["engine"] == "codex"
    assert logs[0]["model"] == "gpt-6.1-sol"
    assert "agy (gemini-4-argon-medium)" in (logs[0]["fallback_from"] or "")

    class AllFailAnalyzer:
        async def analyze(self, scene, context):
            raise ProviderError("timeout")

    monkeypatch.setattr(registry, "analyzer", lambda eng: AllFailAnalyzer())
    asyncio.run(jobs._run_video_prompt(project["id"], "scene_001", "omni_1_2", "agy"))

    logs_after = prompt_logger.read_logs(project["id"])
    assert logs_after[0]["status"] == "error"
    assert logs_after[0]["engine"] == "agy -> codex"
    assert logs_after[0]["model"] == "gemini-4-argon-medium -> gpt-6.1-sol"
