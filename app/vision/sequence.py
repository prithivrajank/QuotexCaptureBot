"""Timestamp assignment and gap diagnostics for visible chart-candle candidates."""
from collections.abc import Iterable


def deduplicate_candles(candidates: Iterable, time_calibration, timeframe_seconds: int):
    """Order candidates, retain strongest per slot, and quantify visible gaps.

    Missing slots are counted exactly but only the first 1000 timestamps are
    included in the diagnostic list. No candle is ever fabricated.
    """
    if timeframe_seconds < 1:
        raise ValueError("timeframe_seconds must be positive")

    candidates = list(candidates)
    by_timestamp = {}
    duplicate_slots = []
    for candidate in candidates:
        timestamp = time_calibration.candle_timestamp_at(candidate.x, timeframe_seconds)
        current = by_timestamp.get(timestamp)
        if current is None:
            by_timestamp[timestamp] = candidate
        else:
            duplicate_slots.append(timestamp)
            if float(candidate.confidence) > float(current.confidence):
                by_timestamp[timestamp] = candidate

    ordered = sorted(by_timestamp.items(), key=lambda item: item[0])
    timestamps = [timestamp for timestamp, _ in ordered]
    missing_slots = []
    missing_slot_count = 0
    largest_gap_slots = 0
    gap_count = 0

    for previous, current in zip(timestamps, timestamps[1:]):
        delta = current - previous
        if delta > timeframe_seconds and delta % timeframe_seconds == 0:
            slots = delta // timeframe_seconds - 1
            gap_count += 1
            missing_slot_count += slots
            largest_gap_slots = max(largest_gap_slots, slots)
            remaining = max(0, 1000 - len(missing_slots))
            if remaining:
                missing_slots.extend(
                    range(previous + timeframe_seconds,
                          min(current, previous + timeframe_seconds * (remaining + 1)),
                          timeframe_seconds)
                )

    diagnostics = {
        "candidate_count": len(candidates),
        "unique_slots": len(ordered),
        "duplicate_timestamps": sorted(set(duplicate_slots)),
        "missing_timestamps": missing_slots,
        "missing_slot_count": missing_slot_count,
        "gap_count": gap_count,
        "largest_gap_slots": largest_gap_slots,
        "sequence_contiguous": not duplicate_slots and missing_slot_count == 0,
    }
    return [candidate for _, candidate in ordered], diagnostics
