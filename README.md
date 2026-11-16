# Shot2Key

Local GUI studio that turns a reference video into a **scene-by-scene storyboard** (each scene ≤ 10 s),
writes a ready-to-use image prompt per scene, and generates the **keyframe image** with a local AI CLI
(`agy` / `codex`) or an API provider (Gemini / any [OI]-compatible endpoint).

Video decomposition is powered by [`JuneYaooo/rea-video`](https://github.com/JuneYaooo/rea-video)
(Apache-2.0) — used as an installed dependency, not vendored code.

---

## Prerequisites

| Tool | Why | Install |
|---|---|---|
| Python 3.10+ | backend + rea-video | https://www.python.org/downloads/ |
| Node.js 18+ | frontend | https://nodejs.org/ |
| `agy` CLI | keyframe generation / analysis | PowerShell: `irm https://antigravity.google/cli/install.ps1 \| iex` — docs: https://antigravity.google/docs/cli/reference |
| `codex` CLI | keyframe generation / analysis | `npm install -g @openai/codex@latest` — repo: https://github.com/openai/codex |

`start.bat` **checks both CLIs first** and stops with the exact install command + official URL if one is
missing. To run with only one of them:

```bat
set SHOT2KEY_REQUIRE_CLI=agy
start.bat
```

`ffmpeg` does **not** need to be installed: `imageio-ffmpeg` ships a static build inside
`backend/.venv`, and the launcher puts it on the backend's `PATH` (and in `SHOT2KEY_FFMPEG`).

## Quick start

```bat
start.bat      :: installs .venv + npm deps on first run, then opens the browser
stop.bat       :: stops backend (8000) and frontend (5173)
```

The launcher creates `backend/.venv`, installs `backend/requirements.txt`, runs `npm install` in
`frontend/` when `node_modules` is missing, starts FastAPI (:8000) and Vite (:5173), and opens
http://localhost:5173.

## Flow

1. **Upload** `.mp4/.mov/.mkv` → stored in `backend/uploads/`.
2. **Decompose** runs `rea-video decompose` in a background job; progress is polled through
   `GET /api/projects/{id}`.
3. **Smart scene splitter** groups shots into scenes of at most **10 s** (a 30 s video yields ≥ 3
   scenes). A single shot longer than 10 s is cut into equal pieces, and a fresh reference frame is
   extracted at the piece's own start time.
4. **Analyze** sends each scene's reference frame to the chosen engine and stores description, prompt,
   camera and lighting notes.
5. **Generate** calls `agy` or `codex` per scene (or *Generate All*) with a prompt that names the exact
   output path; results land in `backend/outputs/{project_id}/scenes/`.
6. **Export** downloads a ZIP: `keyframes/*.png`, `reference/*.jpg`, `prompts.json`, `VIDEO.md`,
   `storyboard.json`, plus `subtitles.srt` / `overlays.ass` when rea-video detected captions.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/system/status` | readiness of rea-video, ffmpeg, agy, codex, API keys |
| POST | `/api/projects/upload` | upload a video, start decompose |
| GET | `/api/projects` | list projects |
| GET | `/api/projects/{id}` | project + shots + scenes + progress |
| POST | `/api/projects/{id}/analyze` | `{engine: agy\|codex\|gemini\|openai}` |
| PATCH | `/api/projects/{id}/scenes/{scene_id}` | edit prompt / description |
| POST | `/api/projects/{id}/scenes/{scene_id}/generate` | `{engine: agy\|codex}` |
| POST | `/api/projects/{id}/generate-all` | queue every scene that has a prompt |
| GET | `/api/projects/{id}/export` | ZIP bundle |
| GET/PUT | `/api/settings` | API keys, default engines |

## Layout

```text
shot2key/
├── backend/
│   ├── core/        # store, decomposer (rea-video), scene_splitter, media, jobs, exporter
│   ├── providers/   # CLI (agy/codex) and API (gemini / [OI]-compatible) engines
│   ├── routers/     # system, projects, settings
│   ├── tests/       # pytest: scene splitter + API
│   └── main.py
├── frontend/        # Vite + React + TypeScript + Tailwind
├── docs/            # PLAN.md, DECISIONS.md (git-ignored)
├── launcher.py      # prerequisite checks, venv/npm setup, ffmpeg, run + open browser
├── start.bat        # Windows entry point
└── stop.bat
```

## Tests

```bat
cd backend
.venv\Scripts\python.exe -m pytest
```

Covers the ≤ 10 s guarantee (grouping, splitting, contiguity, edge durations) and the HTTP
surface (status, upload validation, scene editing, export).

## Attribution & license

Video decomposition uses [`JuneYaooo/rea-video`](https://github.com/JuneYaooo/rea-video),
licensed under **Apache-2.0**. Shot2Key only depends on its published CLI and `breakdown.json`
output; no rea-video source is copied or modified.
