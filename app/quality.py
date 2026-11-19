"""Capture freshness and quality status classification."""


def classify_capture_status(
    timeframe_seconds: int,
    latest_candle_age_seconds: int | None,
    diagnostic_age_seconds: int | None,
    duplicate_count: int = 0,
    missing_timestamps: list[int] | None = None,
    calibration_structurally_valid: bool = True,
    timestamp_alignment_status: str = "ALIGNED",
    missing_slot_count: int = 0,
) -> str:
    """Classify visual capture health; thresholds are intentionally conservative."""
    if latest_candle_age_seconds is None or diagnostic_age_seconds is None:
        return "NO_DATA"
    if diagnostic_age_seconds > 45:
        return "CAPTURE_OFFLINE"
    if latest_candle_age_seconds > max(90, timeframe_seconds * 3):
        return "STALE"
    if duplicate_count > 0 or missing_timestamps or missing_slot_count > 0 or not calibration_structurally_valid:
        return "WARNING"
    if timestamp_alignment_status in ("LAGGING", "AHEAD", "NO_CANDLES"):
        return "TIMESTAMP_DRIFT"
    return "HEALTHY"
