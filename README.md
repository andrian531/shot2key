# Shot2Key

Local GUI studio that turns a reference video into a **scene-by-scene storyboard** (one scene per shot, each ≤ 10 s), analyzes frames & expressions, generates **First & Last Keyframe prompts/images** via local AI CLIs (`agy` / `codex`), and crafts **model-specific Video Motion Prompts** for Google Flow (`Omni 1.2 Flash`, `Veo 3.1 - Lite`), `Seedance 2.0`, `MiniMax`, and `Kling AI`.

Video decomposition and vendor prompting specifications are powered by [`JuneYaooo/rea-video`](https://github.com/JuneYaooo/rea-video) (**Apache-2.0**) — used as an installed dependency, not vendored code.

---

## Prerequisites

| Tool | Why | Install |
|---|---|---|
| Python 3.10+ | backend + `rea-video` | https://www.python.org/downloads/ |
| Node.js 18+ | frontend | https://nodejs.org/ |
| `agy` CLI | keyframe generation / analysis | PowerShell: `irm https://antigravity.google/cli/install.ps1 \| iex` — docs: https://antigravity.google/docs/cli/reference |
| `codex` CLI | keyframe generation / analysis | `npm install -g @openai/codex@latest` — repo: https://github.com/openai/codex |

`start.bat` **checks both CLIs first** and stops with the exact install command + official URL if one is missing. To run with only one of them:

```bat
set SHOT2KEY_REQUIRE_CLI=agy
start.bat
```

`ffmpeg` does **not** need to be installed manually: `imageio-ffmpeg` ships a static build inside `backend/.venv`, and the launcher puts it on the backend's `PATH` (and in `SHOT2KEY_FFMPEG`).

---

## Quick Start

```bat
start.bat      :: installs .venv + npm deps on first run, then opens the browser
stop.bat       :: stops backend (8000) and frontend (5173)
```

The launcher creates `backend/.venv`, installs `backend/requirements.txt`, runs `npm install` in `frontend/` when `node_modules` is missing, starts FastAPI (`:8000`) and Vite (`:5173`), and opens `http://localhost:5173`.

---

## Workflow

1. **Upload** `.mp4 / .mov / .mkv` → stored locally in `backend/uploads/`.
2. **Decompose** runs `rea-video decompose` in a background job (extracting shots, first/last frames, contact sheets, separated audio stems `original/vocals/music/effects`, subtitles, and `report.html`).
3. **Per-Shot Splitting** keeps **one scene per shot** — shots are never merged, so a 3 s shot stays a 3 s scene. Only shots longer than `max_scene_seconds` (default 10, configurable `5 / 8 / 10` in Settings) are split evenly with fresh edge frames extracted.
4. **Analyze (and Optional Deep Analyze 0.5 s)** sends First Frame + Last Frame + Contact Sheet (or frames sampled every 0.5 s in Deep Analyze) to `agy` / `codex` and stores `description`, **First Keyframe Prompt**, **Last Keyframe Prompt**, camera/lighting notes, `detected_characters`, and `deep_timeline`.
5. **Inline Scene Clip Player** displays a 16:9 poster per scene and cuts/plays the exact scene MP4 lazily via `ffmpeg` **only when Play is clicked** (cached under `outputs/{id}/clips/`).
6. **Replace Karakter Toggle** switches cleanly between natural descriptions (default, safe to copy directly to Google Flow) and `[Char_1]`, `[Char_2]` placeholder tags for manual character swapping in Flow.
7. **Image Keyframe Generation (Optional)** generates new First and/or Last Keyframe PNGs directly via `agy` / `codex` — or you can copy the two Image Prompts to external generators like ChatGPT / Midjourney / Nano Banana.
8. **Model-Specific Video Motion Prompt** starts empty by default; choose your target model (`Omni 1.2 Flash`, `Veo 3.1 - Lite`, `Seedance 2.0`, `MiniMax`, `Kling`) and click **Generate Prompt** to format the stored scene & deep-timeline data using that model's prompting rules.
9. **Logs & Export ZIP** inspect every prompt/response in `data/logs/{project_id}.jsonl` via the **Logs** panel, or export a ZIP containing `keyframes/*.png`, `reference/*.jpg`, `prompts.json`, `VIDEO.md`, `storyboard.json`, `stems/*.wav`, and subtitles.

---

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/system/status` | readiness of `rea-video`, `ffmpeg`, `agy`, `codex`, `video_models` |
| POST | `/api/projects/upload` | upload a video, start decompose |
| GET | `/api/projects` | list projects |
| GET | `/api/projects/{id}` | project + shots + scenes + progress |
| POST | `/api/projects/{id}/analyze` | `{engine: agy\|codex\|gemini\|openai}` |
| POST | `/api/projects/{id}/scenes/{scene_id}/deep-analyze` | extract frames every 0.5 s for detailed timeline + prompts |
| POST | `/api/projects/{id}/scenes/{scene_id}/video-prompt` | generate model-specific video prompt (`omni_1_2`, `veo_3_1_lite`, `seedance_2_0`, `minimax`, `kling`) |
| PATCH | `/api/projects/{id}/scenes/{scene_id}` | edit prompts, description, or `replace_characters` |
| GET | `/api/projects/{id}/scenes/{scene_id}/clip` | lazy on-demand `ffmpeg` scene clip (`?download=1`) |
| GET | `/api/projects/{id}/scenes/{scene_id}/keyframe` | reference First Frame |
| GET | `/api/projects/{id}/scenes/{scene_id}/last-keyframe` | reference Last Frame |
| POST | `/api/projects/{id}/scenes/{scene_id}/generate` | `{engine: agy\|codex, target: first\|last\|both}` |
| GET | `/api/projects/{id}/scenes/{scene_id}/image` | generated First Keyframe PNG |
| GET | `/api/projects/{id}/scenes/{scene_id}/last-image` | generated Last Keyframe PNG |
| POST | `/api/projects/{id}/generate-all` | queue scenes that have a prompt |
| GET | `/api/projects/{id}/audio/{stem}` | `original` / `vocals` / `music` / `effects` |
| GET | `/api/projects/{id}/report` | `rea-video` `report.html` |
| GET | `/api/projects/{id}/logs` | prompt/response log (JSONL, newest first) |
| GET | `/api/projects/{id}/export` | ZIP bundle |
| GET/PUT | `/api/settings` | default CLI engines, `max_scene_seconds`, `auto_analyze`, `default_style_prompt` |

---

## Layout

```text
shot2key/
├── backend/
│   ├── core/        # store, decomposer (rea-video), scene_splitter, media, jobs, prompt_logger, exporter
│   ├── providers/   # CLI (agy/codex), API (gemini/openai-compatible), video_models (rea-video rules)
│   ├── routers/     # system, projects, settings, characters
│   ├── tests/       # pytest: scene_splitter, API, phase2–phase5
│   └── main.py
├── frontend/        # Vite + React + TypeScript + Tailwind
│   └── src/
│       ├── router/  # / , /projects/:id , /settings
│       ├── views/   # LibraryView, ProjectView, SettingsView
│       ├── components/  # SystemStatusBar, UploadPanel, Storyboard (sidebar timeline), SceneCard
│       └── state/   # AppContext
├── docs/            # PLAN.md, PHASE2–5 plans, DESIGN.md, DECISIONS.md (git-ignored)
├── launcher.py      # prerequisite checks, venv/npm setup, ffmpeg, run + open browser
├── start.bat        # Windows entry point
└── stop.bat
```

---

## Tests

```bat
cd backend
.venv\Scripts\python.exe -m pytest
```

Covers per-shot splitting (no merging, splitting, contiguity, edge durations), First/Last/Video prompts, `Replace Karakter` modes, `Deep Analyze` interval frames, model-specific video prompt generation, lazy clip caching, audio/report/log endpoints, and the export bundle.

---

## Skills, Credits & License

Shot2Key is a local GUI & orchestration layer built on top of open-source tools and agent skills:

| Project / Skill | Role in Shot2Key | License | Repository |
|---|---|---|---|
| **rea-video** | Core video decomposition (`decompose`, `breakdown.json`, audio stems, subtitles, `report.html`) and built-in model prompting specifications (`capabilities/prompting.yaml` for Omni, Veo, Seedance, MiniMax, Kling) | Apache-2.0 | https://github.com/JuneYaooo/rea-video |
| **anti-slop** (`antislop`, `antislop-ui`, `antislop-human`) | UI audit & anti-slop design filter applied to the Cutroom Studio interface (contrast, layout hierarchy, typography, zero decorative emoji) | Open Source | https://github.com/miqdadbadjuber/anti-slop |
| **video-prompting-skill** | Reference patterns for multi-model video prompting (`Veo`, `Seedance`, `MiniMax`, `LTX`) and First/Last frame consistency | Open Source | https://github.com/Square-Zero-Labs/video-prompting-skill |
| **veo-tools** | Reference workflow & anti-slop guardrails for Google Veo 3.1 prompting | Open Source | https://github.com/kdowswell/veo-tools |

No `rea-video` source code is copied or modified; Shot2Key depends on the installed `rea-video` package and its published outputs.
