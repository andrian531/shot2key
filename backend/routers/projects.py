"""Project endpoints: upload, decompose status, analyze, generate, export."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

import config
from core import exporter, jobs, prompt_logger, store
from providers.base import ProviderError

router = APIRouter(prefix="/api/projects", tags=["projects"])

_CHUNK = 1024 * 1024


class AnalyzeRequest(BaseModel):
    engine: str = Field(default="agy")
    scene_ids: list[str] | None = None


class GenerateRequest(BaseModel):
    engine: str = Field(default="agy")
    target: Literal["first", "last", "both"] = "first"


class ScenePatch(BaseModel):
    prompt: str | None = None
    last_prompt: str | None = None
    video_prompt: str | None = None
    description: str | None = None
    camera: str | None = None
    lighting: str | None = None
    replace_characters: bool | None = None
    character_mappings: dict[str, Any] | None = None


class ApplyCharactersRequest(BaseModel):
    character_mappings: dict[str, Any]
    replace_characters: bool = True


def _load(project_id: str) -> dict[str, Any]:
    try:
        return store.load(project_id)
    except store.ProjectNotFound as exc:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan") from exc


def _scene_or_404(project: dict[str, Any], scene_id: str) -> dict[str, Any]:
    scene = store.find_scene(project, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene tidak ditemukan")
    return scene


@router.get("")
def list_projects() -> dict[str, Any]:
    return {"projects": store.list_projects()}


@router.post("/upload", status_code=201)
async def upload(file: UploadFile = File(...)) -> dict[str, Any]:
    filename = Path(file.filename or "video.mp4").name
    suffix = Path(filename).suffix.lower()
    if suffix not in config.ALLOWED_VIDEO_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Format {suffix or '(kosong)'} tidak didukung. Gunakan: "
            + ", ".join(sorted(config.ALLOWED_VIDEO_EXTS)),
        )

    project = store.create(filename=filename, video_path="", size_bytes=0)
    target = config.get_uploads_dir() / f"{project['id']}{suffix}"
    target.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    try:
        with target.open("wb") as handle:
            while chunk := await file.read(_CHUNK):
                written += len(chunk)
                if written > config.MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="File terlalu besar.")
                handle.write(chunk)
    except HTTPException:
        target.unlink(missing_ok=True)
        store.delete(project["id"])
        raise
    except Exception as exc:  # noqa: BLE001
        target.unlink(missing_ok=True)
        store.delete(project["id"])
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan file: {exc}") from exc
    finally:
        await file.close()

    if written == 0:
        target.unlink(missing_ok=True)
        store.delete(project["id"])
        raise HTTPException(status_code=400, detail="File kosong.")

    def apply(item: dict[str, Any]) -> None:
        item["video_path"] = str(target)
        item["size_bytes"] = written
        item["progress"] = {
            "stage": "queued",
            "percent": 1,
            "message": "Video diterima, memulai decompose...",
        }

    project = store.mutate(project["id"], apply)
    jobs.start_decompose(project["id"])
    return project


@router.get("/{project_id}")
def get_project(project_id: str) -> dict[str, Any]:
    return _load(project_id)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str) -> Response:
    project = _load(project_id)
    store.delete(project_id)
    video = Path(project.get("video_path") or "")
    if video.is_file():
        video.unlink(missing_ok=True)
    for directory in (
        config.get_outputs_dir() / project_id,
        config.get_breakdowns_dir() / project_id,
    ):
        if directory.is_dir():
            shutil.rmtree(directory, ignore_errors=True)
    prompt_logger.clear_logs(project_id)
    return Response(status_code=204)


@router.post("/{project_id}/analyze")
async def analyze(project_id: str, body: AnalyzeRequest) -> dict[str, Any]:
    project = _load(project_id)
    if not project.get("scenes"):
        raise HTTPException(status_code=409, detail="Belum ada scene. Tunggu decompose selesai.")
    if body.engine not in config.ANALYZER_ENGINES:
        raise HTTPException(
            status_code=400,
            detail=f"Engine tidak dikenal. Pilih: {', '.join(config.ANALYZER_ENGINES)}",
        )
    if jobs.is_running(f"{project_id}:analyze"):
        raise HTTPException(status_code=409, detail="Analisis masih berjalan.")

    jobs.start_analyze(project_id, body.engine, body.scene_ids)
    return {"status": "started", "engine": body.engine}


@router.patch("/{project_id}/scenes/{scene_id}")
def patch_scene(project_id: str, scene_id: str, body: ScenePatch) -> dict[str, Any]:
    project = _load(project_id)
    _scene_or_404(project, scene_id)

    fields = {key: value for key, value in body.model_dump().items() if value is not None}
    if not fields:
        return project

    def apply(item: dict[str, Any]) -> None:
        scene = store.find_scene(item, scene_id)
        if scene is not None:
            scene.update(fields)

    return store.mutate(project_id, apply)


@router.post("/{project_id}/apply-characters")
def apply_characters(project_id: str, body: ApplyCharactersRequest) -> dict[str, Any]:
    _load(project_id)

    def apply(item: dict[str, Any]) -> None:
        for scene in item.get("scenes") or []:
            detected = scene.get("detected_characters") or []
            slots = {c.get("slot") for c in detected if isinstance(c, dict) and c.get("slot")}
            matched = {
                slot: mapping
                for slot, mapping in body.character_mappings.items()
                if not slots or slot in slots
            }
            if matched:
                existing = dict(scene.get("character_mappings") or {})
                existing.update(matched)
                scene["character_mappings"] = existing
                scene["replace_characters"] = body.replace_characters

    return store.mutate(project_id, apply)


@router.post("/{project_id}/scenes/{scene_id}/deep-analyze")
async def deep_analyze_scene(
    project_id: str, scene_id: str, body: AnalyzeRequest
) -> dict[str, Any]:
    project = _load(project_id)
    _scene_or_404(project, scene_id)
    if body.engine not in config.ANALYZER_ENGINES:
        raise HTTPException(
            status_code=400,
            detail=f"Engine tidak dikenal. Pilih: {', '.join(config.ANALYZER_ENGINES)}",
        )
    if jobs.is_running(f"{project_id}:deep:{scene_id}"):
        raise HTTPException(status_code=409, detail="Deep Analyze sedang berjalan untuk scene ini.")

    jobs.start_deep_analyze(project_id, scene_id, body.engine)
    return {"status": "started", "scene_id": scene_id, "engine": body.engine}


@router.post("/{project_id}/scenes/{scene_id}/generate")
async def generate_scene(project_id: str, scene_id: str, body: GenerateRequest) -> dict[str, Any]:
    project = _load(project_id)
    scene = _scene_or_404(project, scene_id)
    if body.engine not in config.IMAGE_ENGINES:
        raise HTTPException(
            status_code=400,
            detail=f"Engine gambar tidak dikenal. Pilih: {', '.join(config.IMAGE_ENGINES)}",
        )
    has_first = bool((scene.get("prompt") or "").strip())
    has_last = bool((scene.get("last_prompt") or scene.get("prompt") or "").strip())
    if (body.target in ("first", "both") and not has_first) or (
        body.target == "last" and not has_last
    ):
        raise HTTPException(status_code=409, detail="Scene ini belum punya prompt.")

    if body.target == "first":
        jobs.start_generate(project_id, [scene_id], body.engine)
    else:
        jobs.start_generate(project_id, [scene_id], body.engine, target=body.target)
    return {"status": "queued", "scene_id": scene_id, "engine": body.engine, "target": body.target}


@router.post("/{project_id}/generate-all")
async def generate_all(project_id: str, body: GenerateRequest) -> dict[str, Any]:
    project = _load(project_id)
    if body.engine not in config.IMAGE_ENGINES:
        raise HTTPException(
            status_code=400,
            detail=f"Engine gambar tidak dikenal. Pilih: {', '.join(config.IMAGE_ENGINES)}",
        )
    scene_ids = [
        scene["id"]
        for scene in project.get("scenes") or []
        if (scene.get("prompt") or "").strip()
    ]
    if not scene_ids:
        raise HTTPException(
            status_code=409, detail="Belum ada scene dengan prompt. Jalankan Analyze dulu."
        )

    if body.target == "first":
        jobs.start_generate(project_id, scene_ids, body.engine)
    else:
        jobs.start_generate(project_id, scene_ids, body.engine, target=body.target)
    return {"status": "queued", "count": len(scene_ids), "engine": body.engine, "target": body.target}


@router.get("/{project_id}/scenes/{scene_id}/keyframe")
def scene_keyframe(project_id: str, scene_id: str) -> FileResponse:
    project = _load(project_id)
    scene = _scene_or_404(project, scene_id)
    path = Path(scene.get("keyframe") or "")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Keyframe referensi tidak tersedia")
    return FileResponse(path)


@router.get("/{project_id}/scenes/{scene_id}/last-keyframe")
def scene_last_keyframe(project_id: str, scene_id: str) -> FileResponse:
    project = _load(project_id)
    scene = _scene_or_404(project, scene_id)
    path = Path(scene.get("last_keyframe") or "")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Last frame referensi tidak tersedia")
    return FileResponse(path)


@router.get("/{project_id}/scenes/{scene_id}/image")
def scene_image(project_id: str, scene_id: str) -> FileResponse:
    project = _load(project_id)
    scene = _scene_or_404(project, scene_id)
    path = Path(scene.get("image_path") or "")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Gambar belum digenerate")
    return FileResponse(path, headers={"Cache-Control": "no-store"})


@router.get("/{project_id}/scenes/{scene_id}/last-image")
def scene_last_image(project_id: str, scene_id: str) -> FileResponse:
    project = _load(project_id)
    scene = _scene_or_404(project, scene_id)
    path = Path(scene.get("last_image_path") or "")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Gambar last keyframe belum digenerate")
    return FileResponse(path, headers={"Cache-Control": "no-store"})


AUDIO_STEMS = ("original", "vocals", "music", "effects")


@router.get("/{project_id}/audio/{stem}")
def project_audio(project_id: str, stem: str, download: bool = False) -> FileResponse:
    """Serve one separated audio stem produced by rea-video."""
    project = _load(project_id)
    if stem not in AUDIO_STEMS:
        raise HTTPException(
            status_code=400, detail=f"Stem tidak dikenal. Pilih: {', '.join(AUDIO_STEMS)}"
        )
    breakdown_dir = Path(project.get("breakdown_dir") or "")
    path = breakdown_dir / "stems" / f"{stem}.wav"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Stem {stem} tidak tersedia")
    headers = {"Cache-Control": "no-store"}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{stem}.wav"'
    return FileResponse(path, media_type="audio/wav", headers=headers)


@router.get("/{project_id}/report")
def project_report(project_id: str) -> FileResponse:
    """Open rea-video's HTML report in a new tab."""
    project = _load(project_id)
    breakdown_dir = Path(project.get("breakdown_dir") or "")
    path = breakdown_dir / "report.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="report.html tidak tersedia")
    return FileResponse(path, media_type="text/html")


@router.get("/{project_id}/logs")
def project_logs(project_id: str, limit: int = 200) -> dict[str, Any]:
    """Prompt/response log for this project, newest first."""
    _load(project_id)
    return {"logs": prompt_logger.read_logs(project_id, limit=limit)}


@router.get("/{project_id}/export")
def export(project_id: str) -> Response:
    project = _load(project_id)
    if not project.get("scenes"):
        raise HTTPException(status_code=409, detail="Belum ada scene untuk diekspor.")
    try:
        payload = exporter.build_zip(project)
    except ProviderError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    filename = exporter.export_filename(project)
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
