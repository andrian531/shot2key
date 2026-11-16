"""Character & costume database endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from core import characters as char_store

router = APIRouter(prefix="/api/characters", tags=["characters"])


class CostumePayload(BaseModel):
    id: str | None = None
    name: str = ""
    description: str = ""


class CharacterCreate(BaseModel):
    name: str
    appearance: str = ""
    costumes: list[CostumePayload] = Field(default_factory=list)


class CharacterUpdate(BaseModel):
    name: str | None = None
    appearance: str | None = None
    costumes: list[CostumePayload] | None = None


@router.get("")
def list_characters() -> dict[str, Any]:
    return {"characters": char_store.list_characters()}


@router.post("", status_code=201)
def create_character(body: CharacterCreate) -> dict[str, Any]:
    try:
        item = char_store.create_character(
            name=body.name,
            appearance=body.appearance,
            costumes=[c.model_dump() for c in body.costumes],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"character": item}


@router.put("/{char_id}")
def update_character(char_id: str, body: CharacterUpdate) -> dict[str, Any]:
    try:
        item = char_store.update_character(
            char_id,
            name=body.name,
            appearance=body.appearance,
            costumes=[c.model_dump() for c in body.costumes] if body.costumes is not None else None,
        )
    except char_store.CharacterNotFound as exc:
        raise HTTPException(status_code=404, detail="Karakter tidak ditemukan") from exc
    return {"character": item}


@router.delete("/{char_id}", status_code=204)
def delete_character(char_id: str) -> Response:
    try:
        char_store.delete_character(char_id)
    except char_store.CharacterNotFound as exc:
        raise HTTPException(status_code=404, detail="Karakter tidak ditemukan") from exc
    return Response(status_code=204)


@router.post("/{char_id}/image")
async def upload_character_image(char_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    suffix = Path(file.filename or "ref.png").suffix.lower() or ".png"
    content = await file.read()
    await file.close()
    if not content:
        raise HTTPException(status_code=400, detail="File gambar kosong.")
    try:
        item = char_store.set_reference_image(char_id, suffix, content)
    except char_store.CharacterNotFound as exc:
        raise HTTPException(status_code=404, detail="Karakter tidak ditemukan") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"character": item}


@router.get("/{char_id}/image")
def get_character_image(char_id: str) -> FileResponse:
    try:
        item = char_store.get_character(char_id)
    except char_store.CharacterNotFound as exc:
        raise HTTPException(status_code=404, detail="Karakter tidak ditemukan") from exc
    ref = item.get("reference_image")
    if not ref or not Path(ref).is_file():
        raise HTTPException(status_code=404, detail="Gambar referensi belum ada")
    return FileResponse(ref)
