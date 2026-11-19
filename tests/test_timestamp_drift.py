from app.quality import classify_capture_status


def test_timestamp_drift_is_reported():
    assert classify_capture_status(60, 50, 10, 0, [], True, "LAGGING") == "TIMESTAMP_DRIFT"
    assert classify_capture_status(60, 50, 10, 0, [], True, "AHEAD") == "TIMESTAMP_DRIFT"


def test_healthy_alignment_is_healthy():
    assert classify_capture_status(60, 50, 10, 0, [], True, "ALIGNED") == "HEALTHY"
