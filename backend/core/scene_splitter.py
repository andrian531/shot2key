"""Smart scene splitter: turn rea-video shots into scenes of at most 10 seconds.

Rules
-----
* A shot shorter than the cap is kept whole and may be *grouped* with the
  following shots while the group still fits under the cap.
* A shot longer than the cap is *split* into ``ceil(duration / cap)`` equal
  pieces, so a 25 s shot becomes 3 scenes of ~8.33 s.
* Scenes are contiguous: scene *n* ends exactly where scene *n+1* starts, and
  the first scene starts at the first shot's start.
* Every scene carries the reference keyframe of the shot it starts in; the
  caller may re-extract a frame for split pieces (see ``Scene.is_split``).

The module is pure Python (no ffmpeg, no FastAPI) so it is cheap to test.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

#: Tolerance for float noise when comparing a scene length against the cap.
EPS = 1e-6


@dataclass
class Scene:
    """One storyboard scene, always ``duration <= max_seconds``."""

    index: int
    start_time: float
    end_time: float
    duration: float
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


@dataclass
class _Segment:
    """A piece of a shot that is guaranteed to fit under the cap."""

    start: float
    end: float
    shot_index: int
    is_split: bool

    @property
    def duration(self) -> float:
        return self.end - self.start


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


def _segments(shots: Sequence[dict[str, Any]], max_seconds: float) -> list[_Segment]:
    """Cut every over-long shot into equal pieces that fit under the cap."""
    segments: list[_Segment] = []
    for shot in shots:
        start, end = shot["start"], shot["end"]
        duration = end - start
        if duration <= max_seconds + EPS:
            segments.append(_Segment(start, end, shot["index"], False))
            continue
        # ``- EPS`` keeps an exact multiple (20.0 / 10.0) from rounding up to 3.
        pieces = max(1, math.ceil(duration / max_seconds - EPS))
        step = duration / pieces
        for piece in range(pieces):
            piece_start = start + step * piece
            piece_end = end if piece == pieces - 1 else start + step * (piece + 1)
            segments.append(
                _Segment(round(piece_start, 3), round(piece_end, 3), shot["index"], True)
            )
    return segments


def split_scenes(
    shots: Iterable[dict[str, Any]],
    max_seconds: float = 10.0,
) -> list[Scene]:
    """Group/split ``shots`` into scenes no longer than ``max_seconds``.

    ``shots`` items need ``start``/``end`` (or ``start_time``/``end_time``) and
    optionally ``index``. Returns scenes in timeline order, 1-indexed.
    """
    if max_seconds <= 0:
        raise ValueError("max_seconds must be positive")

    clean = _normalise_shots(shots)
    if not clean:
        return []

    scenes: list[Scene] = []
    current: Scene | None = None

    for segment in _segments(clean, max_seconds):
        if current is not None and (segment.end - current.start_time) <= max_seconds + EPS:
            current.end_time = segment.end
            current.duration = current.end_time - current.start_time
            if segment.shot_index not in current.shot_indices:
                current.shot_indices.append(segment.shot_index)
            continue

        current = Scene(
            index=len(scenes) + 1,
            start_time=segment.start,
            end_time=segment.end,
            duration=segment.end - segment.start,
            shot_indices=[segment.shot_index],
            is_split=segment.is_split,
            keyframe_shot_index=segment.shot_index,
        )
        scenes.append(current)

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
