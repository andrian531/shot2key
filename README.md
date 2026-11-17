# Shot2Key

**Turn any reference video into scene-by-scene keyframe prompts and model-tuned motion prompts — running locally on the Google AI and Codex subscriptions you already pay for.**

Most video-breakdown workflows force you to wire up pay-as-you-go vision APIs before you can recreate a single shot. Shot2Key keeps everything on your machine: [`JuneYaooo/rea-video`](https://github.com/JuneYaooo/rea-video) handles shot detection, audio stem separation, and reference frames locally, while your logged-in **`agy` CLI** (Google AI subscription) and **`codex` CLI** (ChatGPT / Codex) handle scene analysis, 0.5-second expression breakdowns, and model-tuned **First/Last Frame** and **Video Motion** prompts ready for Google Flow and other AI video generators.

### Why Creators Use Shot2Key

- **Use existing subscriptions, skip extra API bills:** Route frame analysis and prompt drafting through `agy` and `codex` CLIs, picking specific models from each CLI (`agy models` / Codex model cache) with an optional **fallback engine & model** (for example, primary `agy` falling back to `codex`) so rate limits don't stall your batch.
- **Clean shot boundaries, capped for AI video tools:** Keeps a 3-second cut as a 3-second scene instead of merging unrelated camera angles. Only shots longer than your cap (`5 / 8 / 10 s`) are split evenly.
- **Built for Google Flow, Seedance, MiniMax, and Kling:** Generates copy-ready **First Keyframe** and **Last Keyframe** prompts alongside isolated per-model **Video Motion Prompts** tailored to **Omni 1.2 Flash**, **Veo 3.1 - Lite**, **Seedance 2.0**, **MiniMax**, or **Kling AI** using rules from `rea-video`'s `prompting.yaml`.
- **Swap only the characters you care about:** Prompts default to clean natural descriptions with zero raw placeholders. Enable **Replace Characters** to pick which detected characters keep `[Char_1]`, `[Char_2]` tags while leaving supporting extras natural — with automatic drift warnings if you change character checkboxes after generating a video prompt.
- **Inspect every clip and prompt before burning video credits:** Play any scene's exact cut lazily on demand (`ffmpeg` cuts only when you click Play), run **Deep Analyze (0.5 s)** for beat-by-beat facial expression and camera notes, switch the UI between **EN** (default) and **ID**, and audit every prompt, provider/model, fallback reason, and response in **Logs**.

Video decomposition and vendor prompting specifications are powered by [`JuneYaooo/rea-video`](https://github.com/JuneYaooo/rea-video) (**Apache-2.0**) — used as an installed dependency, not vendored code.

---

## Prerequisites

| Tool | Why | Install |
|---|---|---|
| Python 3.10+ | backend + `rea-video` | https://www.python.org/downloads/ |
| Node.js 18+ | frontend | https://nodejs.org/ |
| `agy` CLI | video/frame analysis & prompt crafting (uses your Google AI subscription login) | PowerShell: `irm https://antigravity.google/cli/install.ps1 \| iex` — docs: https://antigravity.google/docs/cli/reference |
| `codex` CLI | video/frame analysis & prompt crafting (uses your ChatGPT / Codex login) | `npm install -g @openai/codex@latest` — repo: https://github.com/openai/codex |

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
4. **Analyze (and Optional Deep Analyze 0.5 s)** sends First Frame + Last Frame + Contact Sheet (or frames sampled every 0.5 s in Deep Analyze) to your chosen `agy` / `codex` CLI and model (automatically retrying with your configured fallback engine/model on failure) and stores `description`, **First Keyframe Prompt**, **Last Keyframe Prompt**, camera/lighting notes, `detected_characters`, and `deep_timeline`.
5. **Inline Scene Clip Player** displays a 16:9 poster per scene and cuts/plays the exact scene MP4 lazily via `ffmpeg` **only when Play is clicked** (cached under `outputs/{id}/clips/`).
6. **Replace Characters Toggle (Per-Character Selection)** switches cleanly between natural descriptions (default, safe to copy directly to Google Flow) and `[Char_1]`, `[Char_2]` placeholder tags for manual character swapping — with per-character checkboxes so background/supporting characters stay natural while only selected main characters keep `[Char_N]`.
7. **First & Last Frame Prompts** stay side-by-side beneath the reference strip so you can edit and copy both prompts straight into Google Flow, Midjourney, Nano Banana, or ChatGPT.
8. **Per-Model Video Motion Prompt & Drift Warnings** store prompts separately for each video model (`Omni 1.2 Flash`, `Veo 3.1 - Lite`, `Seedance 2.0`, `MiniMax`, `Kling`). Un-generated models start empty when switched in the selector, and if you toggle **Replace Characters**, add character checkboxes, or run **Deep Analyze (0.5 s)** after generating a prompt, Shot2Key warns you to regenerate so your latest character tags and 0.5 s timeline beats are included.
9. **Bilingual UI, Logs & Export ZIP** switch interface labels between **EN** (default) and **ID** in the header (generated prompts stay in English), inspect every prompt, provider/model, fallback trace, and raw response in `data/logs/{project_id}.jsonl` via the **Logs** panel, or export a ZIP containing `reference/*.jpg`, `prompts.json`, `VIDEO.md`, `storyboard.json`, `stems/*.wav`, and subtitles.

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
| GET | `/api/projects/{id}/audio/{stem}` | `original` / `vocals` / `music` / `effects` |
| GET | `/api/projects/{id}/report` | `rea-video` `report.html` |
| GET | `/api/projects/{id}/logs` | prompt/response/provider/model log (JSONL, newest first) |
| GET | `/api/projects/{id}/export` | ZIP bundle |
| GET | `/api/settings/cli-models/{engine}` | discover available models for `agy` or `codex` CLI |
| GET/PUT | `/api/settings` | default & fallback CLI engines/models, `max_scene_seconds`, `auto_analyze`, `default_style_prompt` |

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
│       ├── i18n/    # Bilingual UI dictionary (EN default / ID)
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

Covers per-shot splitting (no merging, splitting, contiguity, edge durations), First/Last/Video prompts, `Replace Characters` modes, `Deep Analyze` interval frames, CLI model discovery & fallback execution, provider/model/fallback log tracking, per-model `video_prompts` metadata & drift tracking, lazy clip caching, audio/report/log endpoints, and the export bundle.

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
