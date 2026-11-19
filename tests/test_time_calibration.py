from app.vision.time_calibration import TimeCalibration


def test_maps_pixels_to_candle_slots():
    calibration = TimeCalibration(x_left=100, timestamp_left=600, x_right=500, timestamp_right=1000)
    assert calibration.timestamp_at(300) == 800
    assert calibration.candle_timestamp_at(349, 60) == 840


def test_rejects_invalid_anchors():
    import pytest
    with pytest.raises(ValueError):
        TimeCalibration(100, 1000, 100, 1060)
    with pytest.raises(ValueError):
        TimeCalibration(100, 1060, 200, 1000)
