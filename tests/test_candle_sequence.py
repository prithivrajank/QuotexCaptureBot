from types import SimpleNamespace

from app.vision.sequence import deduplicate_candles
from app.vision.time_calibration import TimeCalibration


def calibration():
    return TimeCalibration(
        x_left=0,
        timestamp_left=1800000000,
        x_right=600,
        timestamp_right=1800000600,
    )


def candidate(x, confidence):
    return SimpleNamespace(x=x, confidence=confidence)


def test_candidates_are_ordered_by_timestamp():
    ordered, info = deduplicate_candles(
        [candidate(300, 0.8), candidate(100, 0.9), candidate(200, 0.85)],
        calibration(),
        60,
    )
    assert [item.x for item in ordered] == [100, 200, 300]
    assert info["sequence_contiguous"] is True


def test_duplicate_timestamp_keeps_highest_confidence():
    ordered, info = deduplicate_candles(
        [candidate(100, 0.7), candidate(110, 0.95)],
        calibration(),
        60,
    )
    assert len(ordered) == 1
    assert ordered[0].x == 110
    assert info["duplicate_timestamps"]


def test_missing_slots_are_reported_not_fabricated():
    ordered, info = deduplicate_candles(
        [candidate(100, 0.9), candidate(300, 0.9)],
        calibration(),
        60,
    )
    assert len(ordered) == 2
    assert info["missing_timestamps"] == [1800000120]
    assert info["missing_slot_count"] == 1
    assert info["gap_count"] == 1
    assert info["largest_gap_slots"] == 1
    assert info["sequence_contiguous"] is False


def test_large_gap_is_counted_without_unbounded_timestamp_list():
    ordered, info = deduplicate_candles(
        [candidate(0, 0.9), candidate(120000, 0.9)],
        calibration(),
        60,
    )
    assert len(ordered) == 2
    assert info["missing_slot_count"] == 119999
    assert info["largest_gap_slots"] == 119999
    assert len(info["missing_timestamps"]) == 1000
