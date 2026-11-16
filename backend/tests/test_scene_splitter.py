"""Scene splitter: one shot = one scene, split only when a shot is too long."""

from __future__ import annotations

import math

import pytest

from core.scene_splitter import split_scenes

MAX = 10.0


def _shots(*durations: float) -> list[dict]:
    shots, cursor = [], 0.0
    for index, duration in enumerate(durations, start=1):
        shots.append({"index": index, "start": round(cursor, 3), "end": round(cursor + duration, 3)})
        cursor += duration
    return shots


def _assert_valid(scenes, total: float, max_seconds: float = MAX) -> None:
    assert scenes, "expected at least one scene"
    for scene in scenes:
        assert scene.duration <= max_seconds + 1e-6, f"scene {scene.index} is {scene.duration}s"
        assert scene.end_time > scene.start_time
        # one shot per scene: never merged
        assert len(scene.shot_indices) == 1
    # contiguous, no gaps or overlaps
    assert scenes[0].start_time == pytest.approx(0.0, abs=1e-6)
    for previous, current in zip(scenes, scenes[1:]):
        assert current.start_time == pytest.approx(previous.end_time, abs=1e-6)
    assert scenes[-1].end_time == pytest.approx(total, abs=1e-3)
    assert sum(scene.duration for scene in scenes) == pytest.approx(total, abs=1e-3)


def test_three_short_shots_stay_three_scenes():
    """The Phase 2 rule: short shots are NOT merged into one ~10 s scene."""
    scenes = split_scenes(_shots(3.0, 3.0, 3.0), max_seconds=MAX)
    assert len(scenes) == 3
    _assert_valid(scenes, 9.0)
    assert [scene.duration for scene in scenes] == [3.0, 3.0, 3.0]
    assert [scene.shot_indices for scene in scenes] == [[1], [2], [3]]
    assert not any(scene.is_split for scene in scenes)


def test_ten_short_shots_stay_ten_scenes():
    scenes = split_scenes(_shots(*([3.0] * 10)), max_seconds=MAX)
    assert len(scenes) == 10
    _assert_valid(scenes, 30.0)
    assert all(scene.duration == 3.0 for scene in scenes)


def test_thirty_second_single_shot_becomes_three_scenes():
    scenes = split_scenes(_shots(30.0), max_seconds=MAX)
    assert len(scenes) == 3
    _assert_valid(scenes, 30.0)
    assert [scene.index for scene in scenes] == [1, 2, 3]
    assert all(scene.is_split for scene in scenes)
    assert all(scene.shot_indices == [1] for scene in scenes)


def test_long_shot_is_split_into_equal_pieces():
    scenes = split_scenes(_shots(25.0), max_seconds=MAX)
    assert len(scenes) == 3
    _assert_valid(scenes, 25.0)
    assert all(scene.duration <= MAX for scene in scenes)


def test_fifteen_and_a_half_seconds_becomes_two_pieces():
    scenes = split_scenes(_shots(15.5), max_seconds=MAX)
    assert len(scenes) == 2
    _assert_valid(scenes, 15.5)
    assert [scene.duration for scene in scenes] == [7.75, 7.75]
    assert all(scene.is_split for scene in scenes)


def test_exact_cap_is_a_single_scene():
    scenes = split_scenes(_shots(10.0), max_seconds=MAX)
    assert len(scenes) == 1
    assert scenes[0].duration == pytest.approx(10.0)
    assert not scenes[0].is_split


def test_just_over_the_cap_is_split():
    scenes = split_scenes([{"index": 1, "start": 0.0, "end": 10.05}], max_seconds=MAX)
    assert len(scenes) == 2
    _assert_valid(scenes, 10.05)


def test_mixed_shot_lengths_never_exceed_the_cap():
    # 4 + 4 + 4 (three scenes) + 12 -> 2 pieces + 2.5 + 2.5 (two scenes) = 7
    scenes = split_scenes(_shots(4.0, 4.0, 4.0, 12.0, 2.5, 2.5), max_seconds=MAX)
    assert len(scenes) == 7
    _assert_valid(scenes, 29.0)
    assert all(scene.duration <= MAX for scene in scenes)


def test_scene_count_matches_the_minimum_for_a_long_video():
    total = 95.0
    scenes = split_scenes(_shots(total), max_seconds=MAX)
    assert len(scenes) >= math.ceil(total / MAX)
    _assert_valid(scenes, total)


def test_keyframe_shot_index_points_at_the_source_shot():
    scenes = split_scenes(_shots(3.0, 3.0, 3.0, 3.0), max_seconds=MAX)
    assert [scene.keyframe_shot_index for scene in scenes] == [1, 2, 3, 4]


def test_empty_and_invalid_input():
    assert split_scenes([], max_seconds=MAX) == []
    assert split_scenes([{"index": 1, "start": 5.0, "end": 5.0}], max_seconds=MAX) == []
    assert split_scenes([{"index": 1, "start": 9.0, "end": 4.0}], max_seconds=MAX) == []


def test_unsorted_shots_are_sorted_by_start():
    shots = [
        {"index": 2, "start": 4.0, "end": 8.0},
        {"index": 1, "start": 0.0, "end": 4.0},
    ]
    scenes = split_scenes(shots, max_seconds=MAX)
    assert len(scenes) == 2
    assert [scene.shot_indices for scene in scenes] == [[1], [2]]


def test_custom_cap_is_respected():
    scenes = split_scenes(_shots(30.0), max_seconds=5.0)
    assert len(scenes) == 6
    _assert_valid(scenes, 30.0, max_seconds=5.0)


def test_custom_cap_keeps_short_shots_whole():
    scenes = split_scenes(_shots(3.0, 3.0, 3.0), max_seconds=5.0)
    assert len(scenes) == 3
    _assert_valid(scenes, 9.0, max_seconds=5.0)


def test_invalid_cap_raises():
    with pytest.raises(ValueError):
        split_scenes(_shots(5.0), max_seconds=0)
