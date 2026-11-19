from app.quality import classify_capture_status


def test_healthy_capture_status():
    assert classify_capture_status(60, 75, 10, 0, [], True) == "HEALTHY"


def test_missing_candle_is_no_data():
    assert classify_capture_status(60, None, 10, 0, [], True) == "NO_DATA"


def test_stale_candle_is_stale():
    assert classify_capture_status(60, 181, 10, 0, [], True) == "STALE"


def test_old_diagnostics_are_offline():
    assert classify_capture_status(60, 50, 46, 0, [], True) == "CAPTURE_OFFLINE"


def test_sequence_gaps_or_invalid_calibration_are_warning():
    assert classify_capture_status(60, 50, 10, 1, [], True) == "WARNING"
    assert classify_capture_status(60, 50, 10, 0, [123], True) == "WARNING"
    assert classify_capture_status(60, 50, 10, 0, [], False) == "WARNING"
