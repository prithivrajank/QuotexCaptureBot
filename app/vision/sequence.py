"""Timestamp assignment helpers for visible chart-candle candidates."""
from collections.abc import Iterable


def deduplicate_candles(candidates: Iterable, time_calibration, timeframe_seconds: int):
    """Map candidates to candle slots, keep one strongest candidate per slot.

    Returns (ordered_candidates, diagnostics). Missing slots are reported, never
    fabricated or interpolated into synthetic candles.
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

    ordered = sorted(
        ((timestamp, candidate) for timestamp, candidate in by_timestamp.items()),
        key=lambda item: item[0],
    )
    timestamps = [item[0] for item in ordered]
    missing_slots = []
    for previous, current in zip(timestamps, timestamps[1:]):
        delta = current - previous
        if delta > timeframe_seconds and delta % timeframe_seconds == 0:
            missing_slots.extend(range(previous + timeframe_seconds, current, timeframe_seconds))

    diagnostics = {
        "candidate_count": len(candidates),
        "unique_slots": len(ordered),
        "duplicate_timestamps": sorted(set(duplicate_slots)),
        "missing_timestamps": missing_slots,
        "sequence_contiguous": not duplicate_slots and not missing_slots,
    }
    return [candidate for _, candidate in ordered], diagnostics
