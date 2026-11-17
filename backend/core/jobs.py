"""Background jobs: decompose, analyze and keyframe generation.

Everything blocking (rea-video, CLI agents) runs in a worker thread via
``asyncio.to_thread`` so the FastAPI event loop keeps answering the UI's polls.
Image generation is capped by a semaphore because each call spawns a full agent
CLI process.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Iterable

import config
from core import decomposer, media, prompt_logger, store
from core import settings as settings_store
from core.scene_splitter import Scene, split_scenes
from providers import registry
from providers.base import ProviderError, analyze_prompt, scene_input_images
from providers.video_models import DEFAULT_VIDEO_MODEL

logger = logging.getLogger(__name__)

_TASKS: dict[str, asyncio.Task] = {}
_IMAGE_SEM: asyncio.Semaphore | None = None


def _semaphore() -> asyncio.Semaphore:
    global _IMAGE_SEM
    if _IMAGE_SEM is None:
        _IMAGE_SEM = asyncio.Semaphore(max(1, config.IMAGE_CONCURRENCY))
    return _IMAGE_SEM


def _spawn(key: str, coro) -> None:
    """Keep a reference to the task so it is not garbage collected."""
    task = asyncio.create_task(coro)
    _TASKS[key] = task

    def _done(finished: asyncio.Task) -> None:
        _TASKS.pop(key, None)
        if finished.cancelled():
            return
        error = finished.exception()
        if error is not None:
            logger.exception("Job %s gagal", key, exc_info=error)

    task.add_done_callback(_done)


async def shutdown() -> None:
    for task in list(_TASKS.values()):
        task.cancel()
    if _TASKS:
        await asyncio.gather(*_TASKS.values(), return_exceptions=True)
    _TASKS.clear()


def is_running(project_id: str) -> bool:
    return any(key.startswith(project_id) for key in _TASKS)


# --------------------------------------------------------------------------
# Decompose
# --------------------------------------------------------------------------
def _scene_id(index: int) -> str:
    return f"scene_{index:03d}"


def _build_scenes(
    project_id: str,
    breakdown_dir: Path,
    breakdown: dict[str, Any],
    video_path: Path,
    max_seconds: float | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Turn a breakdown into shots + scenes, extracting split-scene frames."""
    shots: list[dict[str, Any]] = []
    for shot in breakdown.get("shots") or []:
        keyframe = decomposer.shot_keyframe(breakdown_dir, shot)
        last_keyframe = decomposer.shot_last_keyframe(breakdown_dir, shot)
        sheet = decomposer.shot_sheet(breakdown_dir, shot)
        shots.append(
            {
                "index": shot.get("index"),
                "start": shot.get("start"),
                "end": shot.get("end"),
                "duration": shot.get("duration"),
                "keyframe": str(keyframe) if keyframe else None,
                "last_keyframe": str(last_keyframe) if last_keyframe else None,
                "sheet": str(sheet) if sheet else None,
            }
        )

    scenes: list[Scene] = split_scenes(
        shots, max_seconds=max_seconds or config.MAX_SCENE_SECONDS
    )
    scene_dir = config.get_outputs_dir() / project_id / "scenes"
    scene_dir.mkdir(parents=True, exist_ok=True)

    by_index = {shot["index"]: shot for shot in shots}
    payload: list[dict[str, Any]] = []
    for scene in scenes:
        scene_id = _scene_id(scene.index)
        shot = by_index.get(scene.keyframe_shot_index) or {}
        keyframe = shot.get("keyframe")
        last_keyframe = shot.get("last_keyframe")
        sheet = shot.get("sheet")

        # A split piece starts/ends mid-shot: the shot's own first/last frames
        # are the wrong reference, so cut fresh ones at the scene's edges.
        if scene.is_split and shot:
            shot_start = float(shot.get("start") or 0.0)
            shot_end = float(shot.get("end") or 0.0)
            if scene.start_time - shot_start > 0.05:
                extracted = media.extract_frame(
                    video_path,
                    scene.start_time,
                    scene_dir / f"{scene_id}_ref.jpg",
                )
                if extracted is not None:
                    keyframe = str(extracted)
            if shot_end - scene.end_time > 0.05:
                extracted_last = media.extract_frame(
                    video_path,
                    max(scene.start_time, scene.end_time - 0.05),
                    scene_dir / f"{scene_id}_last_ref.jpg",
                )
                if extracted_last is not None:
                    last_keyframe = str(extracted_last)

        payload.append(
            {
                "id": scene_id,
                "index": scene.index,
                "start_time": scene.start_time,
                "end_time": scene.end_time,
                "duration": scene.duration,
                "shot_indices": scene.shot_indices,
                "is_split": scene.is_split,
                "keyframe": keyframe,
                "last_keyframe": last_keyframe,
                "sheet": sheet,
                "description": "",
                "prompt": "",
                "last_prompt": "",
                "video_prompt": "",
                "video_model": DEFAULT_VIDEO_MODEL,
                "video_prompt_generating": False,
                "camera": "",
                "lighting": "",
                "detected_characters": [],
                "deep_timeline": [],
                "deep_analyzing": False,
                "replace_characters": False,
                "character_mappings": {},
                "engine": None,
                "image_path": None,
                "image_status": "idle",
                "image_error": None,
                "last_image_path": None,
                "last_image_status": "idle",
                "last_image_error": None,
                "analysis_error": None,
            }
        )
    return shots, payload


async def _run_decompose(project_id: str) -> None:
    project = store.load(project_id)
    video_path = Path(project["video_path"])
    breakdown_dir = config.get_breakdowns_dir() / project_id

    store.update(project_id, status="decomposing", error=None)
    store.set_progress(project_id, "decomposing", 2, "Menyiapkan rea-video...")

    def on_progress(percent: int, message: str) -> None:
        store.set_progress(project_id, "decomposing", percent, message)

    values = settings_store.load()
    try:
        breakdown = await asyncio.to_thread(
            decomposer.decompose,
            video_path,
            breakdown_dir,
            on_progress,
            str(values.get("rea_video_lang") or "en"),
            bool(values.get("rea_video_vlm")),
        )
    except Exception as exc:  # noqa: BLE001 - surfaced to the UI
        logger.exception("decompose gagal untuk %s", project_id)
        store.mutate(
            project_id,
            lambda p: p.update(
                status="failed",
                error=str(exc),
                progress={"stage": "failed", "percent": 0, "message": str(exc)[:300]},
            ),
        )
        return

    max_seconds = float(values.get("max_scene_seconds") or config.MAX_SCENE_SECONDS)
    store.set_progress(
        project_id, "splitting", 97, f"Membuat scene per shot (maks {max_seconds:g} detik)..."
    )
    shots, scenes = await asyncio.to_thread(
        _build_scenes, project_id, breakdown_dir, breakdown, video_path, max_seconds
    )

    source = breakdown.get("source") or {}
    subtitles = {
        key: str(path) for key, path in decomposer.packaging_files(breakdown_dir).items()
    }

    def apply(project: dict[str, Any]) -> None:
        project.update(
            status="ready",
            error=None,
            shots=shots,
            scenes=scenes,
            source={
                "duration": source.get("duration"),
                "width": source.get("width"),
                "height": source.get("height"),
                "fps": source.get("fps"),
                "has_audio": source.get("has_audio"),
            },
            breakdown_dir=str(breakdown_dir),
            subtitles=subtitles,
            audio_stems=decomposer.audio_stems(breakdown_dir),
            report=(
                str(report) if (report := decomposer.report_path(breakdown_dir)) else None
            ),
            progress={
                "stage": "ready",
                "percent": 100,
                "message": f"{len(scenes)} scene siap",
            },
        )

    store.mutate(project_id, apply)

    if bool(values.get("auto_analyze", True)) and scenes:
        default_engine = str(values.get("default_analyzer") or "agy")
        if default_engine in config.ANALYZER_ENGINES:
            start_analyze(project_id, default_engine)


def start_decompose(project_id: str) -> None:
    _spawn(f"{project_id}:decompose", _run_decompose(project_id))


# --------------------------------------------------------------------------
# Analyze
# --------------------------------------------------------------------------
def _context(project: dict[str, Any], scene: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "video_name": project.get("filename"),
        "shot_count": len(scene.get("shot_indices") or []),
        "previous_prompt": (previous or {}).get("prompt") or "",
        "workdir": str(config.get_data_dir()),
    }


async def _run_analyze(project_id: str, engine: str, scene_ids: Iterable[str] | None) -> None:
    project = store.load(project_id)
    analyzer = registry.analyzer(engine)

    wanted = set(scene_ids) if scene_ids else None
    targets = [
        scene
        for scene in project.get("scenes") or []
        if wanted is None or scene.get("id") in wanted
    ]
    if not targets:
        store.mutate(
            project_id,
            lambda p: p.update(
                analysis={"engine": engine, "status": "failed", "error": "Tidak ada scene untuk dianalisis."}
            ),
        )
        return

    store.mutate(
        project_id,
        lambda p: p.update(
            analysis={
                "engine": engine,
                "status": "running",
                "error": None,
                "done": 0,
                "total": len(targets),
            }
        ),
    )

    previous: dict[str, Any] | None = None
    done = 0
    failures: list[str] = []

    for scene in targets:
        context = _context(project, scene, previous)
        images = [path for _, path in scene_input_images(scene)]
        started = time.perf_counter()
        try:
            result = await analyzer.analyze(scene, context)
        except (ProviderError, Exception) as exc:  # noqa: BLE001
            failures.append(f"{scene.get('id')}: {exc}")
            prompt_logger.log_event(
                project_id,
                scene.get("id"),
                "analyze",
                engine,
                prompt_sent=analyze_prompt(scene, context),
                raw_response="",
                input_images=images,
                duration_ms=int((time.perf_counter() - started) * 1000),
                status="error",
                error=str(exc)[:2000],
            )
            store.mutate(
                project_id,
                lambda p, sid=scene.get("id"), msg=str(exc): _patch_scene(
                    p, sid, analysis_error=msg[:500]
                ),
            )
        else:
            payload = result.to_dict()
            prompt_logger.log_event(
                project_id,
                scene.get("id"),
                "analyze",
                engine,
                prompt_sent=result.prompt_sent or analyze_prompt(scene, context),
                raw_response=result.raw,
                input_images=images,
                parsed=payload,
                duration_ms=int((time.perf_counter() - started) * 1000),
                status="ok",
            )
            store.mutate(
                project_id,
                lambda p, sid=scene.get("id"), data=payload, eng=engine: _patch_scene(
                    p,
                    sid,
                    description=data["description"],
                    prompt=data["prompt"],
                    last_prompt=data.get("last_prompt") or "",
                    camera=data["camera"],
                    lighting=data["lighting"],
                    detected_characters=data.get("characters") or [],
                    engine=eng,
                    analysis_error=None,
                ),
            )
            previous = {"prompt": payload["prompt"]}
        done += 1
        store.mutate(
            project_id,
            lambda p, d=done, t=len(targets): p["analysis"].update(done=d, total=t),
        )

    status = "completed" if not failures else ("failed" if len(failures) == len(targets) else "partial")
    store.mutate(
        project_id,
        lambda p: p["analysis"].update(
            status=status,
            error="; ".join(failures)[:1000] if failures else None,
        ),
    )


def _patch_scene(project: dict[str, Any], scene_id: str | None, **fields: Any) -> None:
    scene = store.find_scene(project, scene_id or "")
    if scene is not None:
        scene.update(fields)


def start_analyze(project_id: str, engine: str, scene_ids: Iterable[str] | None = None) -> None:
    _spawn(f"{project_id}:analyze", _run_analyze(project_id, engine, scene_ids))


async def _run_deep_analyze(project_id: str, scene_id: str, engine: str) -> None:
    project = store.load(project_id)
    scene = store.find_scene(project, scene_id)
    if scene is None:
        return

    store.mutate(
        project_id,
        lambda p: _patch_scene(
            p,
            scene_id,
            deep_analyzing=True,
            deep_progress={"percent": 20, "message": "Mengekstrak frame tiap 0.5 detik (ffmpeg)..."},
            analysis_error=None,
        ),
    )

    video_path = Path(project.get("video_path") or "")
    deep_dir = config.get_outputs_dir() / project_id / "deep_frames" / scene_id
    deep_frames = await asyncio.to_thread(
        media.extract_interval_frames,
        video_path,
        float(scene.get("start_time") or 0.0),
        float(scene.get("end_time") or 0.0),
        deep_dir,
        0.5,
        12,
    )

    analyzer = registry.analyzer(engine)
    context = _context(project, scene, None)
    if deep_frames:
        context["deep_frames"] = deep_frames
    images = [path for _, path in scene_input_images(scene, context)]
    store.mutate(
        project_id,
        lambda p, cnt=len(images): _patch_scene(
            p,
            scene_id,
            deep_progress={
                "percent": 65,
                "message": f"Menganalisis {cnt} frame (ekspresi, aksi, kamera) dengan {engine}...",
            },
        ),
    )
    started = time.perf_counter()

    try:
        result = await analyzer.analyze(scene, context)
    except (ProviderError, Exception) as exc:  # noqa: BLE001
        prompt_logger.log_event(
            project_id,
            scene_id,
            "deep_analyze",
            engine,
            prompt_sent=analyze_prompt(scene, context),
            raw_response="",
            input_images=images,
            duration_ms=int((time.perf_counter() - started) * 1000),
            status="error",
            error=str(exc)[:2000],
        )
        store.mutate(
            project_id,
            lambda p, msg=str(exc): _patch_scene(
                p,
                scene_id,
                deep_analyzing=False,
                deep_progress=None,
                analysis_error=msg[:500],
            ),
        )
        return

    payload = result.to_dict()
    prompt_logger.log_event(
        project_id,
        scene_id,
        "deep_analyze",
        engine,
        prompt_sent=result.prompt_sent or analyze_prompt(scene, context),
        raw_response=result.raw,
        input_images=images,
        parsed=payload,
        duration_ms=int((time.perf_counter() - started) * 1000),
        status="ok",
    )
    store.mutate(
        project_id,
        lambda p, data=payload, eng=engine: _patch_scene(
            p,
            scene_id,
            description=data["description"],
            prompt=data["prompt"],
            last_prompt=data.get("last_prompt") or "",
            camera=data["camera"],
            lighting=data["lighting"],
            detected_characters=data.get("characters") or [],
            deep_timeline=data.get("deep_timeline") or [],
            deep_analyzing=False,
            deep_progress=None,
            engine=eng,
            analysis_error=None,
        ),
    )


def start_deep_analyze(project_id: str, scene_id: str, engine: str) -> None:
    _spawn(f"{project_id}:deep:{scene_id}", _run_deep_analyze(project_id, scene_id, engine))


async def _run_video_prompt(
    project_id: str, scene_id: str, model_id: str, engine: str
) -> None:
    project = store.load(project_id)
    scene = store.find_scene(project, scene_id)
    if scene is None:
        return

    store.mutate(
        project_id,
        lambda p: _patch_scene(
            p, scene_id, video_prompt_generating=True, video_model=model_id, analysis_error=None
        ),
    )

    analyzer = registry.analyzer(engine)
    context = _context(project, scene, None)
    context["video_prompt_only"] = True
    context["video_model"] = model_id
    images = [path for _, path in scene_input_images(scene)]
    started = time.perf_counter()

    try:
        result = await analyzer.analyze(scene, context)
    except (ProviderError, Exception) as exc:  # noqa: BLE001
        prompt_logger.log_event(
            project_id,
            scene_id,
            f"video_prompt:{model_id}",
            engine,
            prompt_sent=analyze_prompt(scene, context),
            raw_response="",
            input_images=images,
            duration_ms=int((time.perf_counter() - started) * 1000),
            status="error",
            error=str(exc)[:2000],
        )
        store.mutate(
            project_id,
            lambda p, msg=str(exc): _patch_scene(
                p, scene_id, video_prompt_generating=False, analysis_error=msg[:500]
            ),
        )
        return

    prompt_logger.log_event(
        project_id,
        scene_id,
        f"video_prompt:{model_id}",
        engine,
        prompt_sent=result.prompt_sent or analyze_prompt(scene, context),
        raw_response=result.raw,
        input_images=images,
        parsed={"video_model": model_id, "video_prompt": result.video_prompt},
        duration_ms=int((time.perf_counter() - started) * 1000),
        status="ok",
    )
    store.mutate(
        project_id,
        lambda p: _patch_scene(
            p,
            scene_id,
            video_prompt=result.video_prompt or result.prompt,
            video_model=model_id,
            video_prompt_generating=False,
            analysis_error=None,
        ),
    )


def start_video_prompt(project_id: str, scene_id: str, model_id: str, engine: str) -> None:
    _spawn(
        f"{project_id}:vprompt:{scene_id}",
        _run_video_prompt(project_id, scene_id, model_id, engine),
    )


# --------------------------------------------------------------------------
# Keyframe generation
# --------------------------------------------------------------------------
def scene_image_path(project_id: str, scene_id: str, target: str = "first") -> Path:
    suffix = "_last" if target == "last" else ""
    return config.get_outputs_dir() / project_id / "scenes" / f"{scene_id}{suffix}.png"


async def _generate_single_target(
    project_id: str, scene_id: str, engine: str, target: str
) -> bool:
    project = store.load(project_id)
    scene = store.find_scene(project, scene_id)
    if scene is None:
        return False

    is_last = target == "last"
    status_key = "last_image_status" if is_last else "image_status"
    path_key = "last_image_path" if is_last else "image_path"
    err_key = "last_image_error" if is_last else "image_error"

    out_path = scene_image_path(project_id, scene_id, target=target)
    store.mutate(
        project_id,
        lambda p: _patch_scene(p, scene_id, **{status_key: "generating", err_key: None}),
    )

    generator = registry.image_generator(engine)
    images = [path for _, path in scene_input_images(scene)]
    started = time.perf_counter()
    async with _semaphore():
        try:
            await generator.generate(scene, out_path, target=target)
        except TypeError:
            await generator.generate(scene, out_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("generate %s (%s) gagal: %s", scene_id, target, exc)
            prompt_logger.log_event(
                project_id,
                scene_id,
                f"generate_{target}",
                engine,
                prompt_sent=getattr(generator, "last_prompt", ""),
                raw_response="",
                input_images=images,
                duration_ms=int((time.perf_counter() - started) * 1000),
                status="error",
                error=str(exc)[:2000],
            )
            store.mutate(
                project_id,
                lambda p, msg=str(exc): _patch_scene(
                    p, scene_id, **{status_key: "failed", err_key: msg[:500]}
                ),
            )
            return False

    prompt_logger.log_event(
        project_id,
        scene_id,
        f"generate_{target}",
        engine,
        prompt_sent=getattr(generator, "last_prompt", ""),
        raw_response=str(out_path),
        input_images=images,
        parsed={"image_path": str(out_path), "target": target},
        duration_ms=int((time.perf_counter() - started) * 1000),
        status="ok",
    )
    store.mutate(
        project_id,
        lambda p: _patch_scene(
            p,
            scene_id,
            **{
                status_key: "done",
                path_key: str(out_path),
                err_key: None,
                "engine": engine,
            },
        ),
    )
    return True


async def _generate_one(
    project_id: str, scene_id: str, engine: str, target: str = "first"
) -> bool:
    if target == "both":
        ok_first = await _generate_single_target(project_id, scene_id, engine, "first")
        ok_last = await _generate_single_target(project_id, scene_id, engine, "last")
        return ok_first and ok_last
    return await _generate_single_target(project_id, scene_id, engine, target)


async def _run_generate(
    project_id: str, scene_ids: list[str], engine: str, target: str = "first"
) -> None:
    store.mutate(
        project_id,
        lambda p: p.update(
            generation={
                "engine": engine,
                "target": target,
                "status": "running",
                "queued": len(scene_ids),
                "done": 0,
                "failed": 0,
            }
        ),
    )
    for scene_id in scene_ids:
        updates: dict[str, Any] = {}
        if target in ("first", "both"):
            updates.update({"image_status": "queued", "image_error": None})
        if target in ("last", "both"):
            updates.update({"last_image_status": "queued", "last_image_error": None})
        store.mutate(
            project_id,
            lambda p, sid=scene_id, u=updates: _patch_scene(p, sid, **u),
        )

    results = await asyncio.gather(
        *(_generate_one(project_id, scene_id, engine, target=target) for scene_id in scene_ids),
        return_exceptions=True,
    )
    ok = sum(1 for result in results if result is True)
    failed = len(results) - ok

    store.mutate(
        project_id,
        lambda p: p["generation"].update(
            status="completed" if failed == 0 else ("failed" if ok == 0 else "partial"),
            done=ok,
            failed=failed,
        ),
    )


def start_generate(
    project_id: str, scene_ids: list[str], engine: str, target: str = "first"
) -> None:
    _spawn(f"{project_id}:generate", _run_generate(project_id, scene_ids, engine, target=target))
