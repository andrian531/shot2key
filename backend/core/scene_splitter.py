"""Scene splitter: one shot = one scene, split only when a shot is too long.

Rules
-----
* **Shots are never merged.** A 3 s shot stays a 3 s scene even if three of
  them would fit under the cap — merging different camera angles into one
  scene produces unusable video prompts for Google Flow / Veo.
* A shot longer than the cap is *split* into ``ceil(duration / cap)`` equal
  pieces, so a 15.5 s shot becomes 2 scenes of 7.75 s (``is_split = True``).
* Scenes are contiguous: scene *n* ends exactly where scene *n+1* starts, and
  the first scene starts at the first shot's start.
* Every scene carries the reference keyframe of the shot it came from; the
  caller re-extracts a frame for split pieces (see ``Scene.is_split``).

The module is pure Python (no ffmpeg, no FastAPI) so it is cheap to test.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable

#: Tolerance for float noise when comparing a scene length against the cap.
EPS = 1e-6


@dataclass
class Scene:
    """One storyboard scene, always ``duration <= max_seconds``."""

    index: int
    start_time: float
    end_time: float
    duration: float
    #: Always a single shot: scenes are never merged across shots.
    shot_indices: list[int] = field(default_factory=list)
    #: True when the scene is a slice of a single shot longer than the cap.
    is_split: bool = False
    #: Index of the shot whose reference frame represents this scene.
    keyframe_shot_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "start_time": round(self.start_time, 3),
            "end_time": round(self.end_time, 3),
            "duration": round(self.duration, 3),
            "shot_indices": list(self.shot_indices),
            "is_split": self.is_split,
            "keyframe_shot_index": self.keyframe_shot_index,
        }


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalise_shots(shots: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only usable shots, sorted by start time."""
    clean: list[dict[str, Any]] = []
    for position, shot in enumerate(shots):
        start = _as_float(shot.get("start", shot.get("start_time")))
        end = _as_float(shot.get("end", shot.get("end_time")))
        if end - start <= EPS:
            continue
        index = shot.get("index")
        clean.append(
            {
                "index": int(index) if index is not None else position + 1,
                "start": start,
                "end": end,
            }
        )
    clean.sort(key=lambda item: (item["start"], item["end"]))
    return clean


def split_scenes(
    shots: Iterable[dict[str, Any]],
    max_seconds: float = 10.0,
) -> list[Scene]:
    """Turn every shot into its own scene, splitting shots over the cap.

    ``shots`` items need ``start``/``end`` (or ``start_time``/``end_time``) and
    optionally ``index``. Returns scenes in timeline order, 1-indexed.
    """
    if max_seconds <= 0:
        raise ValueError("max_seconds must be positive")

    scenes: list[Scene] = []

    for shot in _normalise_shots(shots):
        start, end = shot["start"], shot["end"]
        duration = end - start

        if duration <= max_seconds + EPS:
            scenes.append(
                Scene(
                    index=len(scenes) + 1,
                    start_time=start,
                    end_time=end,
                    duration=duration,
                    shot_indices=[shot["index"]],
                    is_split=False,
                    keyframe_shot_index=shot["index"],
                )
            )
            continue

        # ``- EPS`` keeps an exact multiple (20.0 / 10.0) from rounding up to 3.
        pieces = max(1, math.ceil(duration / max_seconds - EPS))
        step = duration / pieces
        for piece in range(pieces):
            piece_start = start + step * piece
            piece_end = end if piece == pieces - 1 else start + step * (piece + 1)
            scenes.append(
                Scene(
                    index=len(scenes) + 1,
                    start_time=round(piece_start, 3),
                    end_time=round(piece_end, 3),
                    duration=round(piece_end, 3) - round(piece_start, 3),
                    shot_indices=[shot["index"]],
                    is_split=True,
                    keyframe_shot_index=shot["index"],
                )
            )

    # Round once at the end so the reported numbers match the JSON exactly.
    for scene in scenes:
        scene.start_time = round(scene.start_time, 3)
        scene.end_time = round(scene.end_time, 3)
        scene.duration = round(scene.end_time - scene.start_time, 3)

    return scenes


def scenes_from_breakdown(
    breakdown: dict[str, Any],
    max_seconds: float = 10.0,
) -> list[Scene]:
    """Convenience wrapper for a rea-video ``breakdown.json`` payload."""
    return split_scenes(breakdown.get("shots") or [], max_seconds=max_seconds)
