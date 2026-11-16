"""Shot2Key backend entrypoint.

Run from the ``backend`` directory:

    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import config
from core import jobs
from routers import characters, projects, settings, system

__version__ = "0.1.0"

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    config.ensure_dirs()
    yield
    await jobs.shutdown()


app = FastAPI(
    title="Shot2Key API",
    description="Storyboard & keyframe generator on top of rea-video.",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(projects.router)
app.include_router(settings.router)
app.include_router(characters.router)


@app.get("/api/health")
def health() -> dict[str, object]:
    return {"status": "ok", "version": __version__, "data_dir": str(config.get_data_dir())}


# Production mode: serve the built SPA from the same port as the API.
if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
