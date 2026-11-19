import cv2
import numpy as np

from app.vision.detector import detect_candidates


def test_green_candle_body_and_wick_are_separated():
    image = np.zeros((180, 240, 3), dtype=np.uint8)
    # Dark chart background; saturated green candle body and thin wick.
    cv2.line(image, (80, 35), (80, 145), (0, 180, 80), 2)
    cv2.rectangle(image, (73, 75), (87, 110), (0, 180, 80), -1)

    found = detect_candidates(image)
    assert found
    candle = min(found, key=lambda item: abs(item.x - 80))
    assert candle.color == "bull"
    assert candle.body_top >= 70
    assert candle.body_bottom <= 115
    assert candle.wick_top <= candle.body_top
    assert candle.wick_bottom >= candle.body_bottom


def test_empty_image_returns_no_candidates():
    image = np.zeros((120, 200, 3), dtype=np.uint8)
    assert detect_candidates(image) == []


def test_invalid_image_is_rejected():
    try:
        detect_candidates(np.array([], dtype=np.uint8))
    except ValueError as exc:
        assert "non-empty" in str(exc)
    else:
        raise AssertionError("Expected ValueError for empty image")



def test_touching_wick_connected_candles_are_split_at_vertical_valley():
    image = np.zeros((180, 240, 3), dtype=np.uint8)
    # Two dense candle bodies connected by a narrow wick bridge.
    cv2.rectangle(image, (70, 65), (82, 105), (0, 180, 80), -1)
    cv2.line(image, (76, 35), (76, 130), (0, 180, 80), 2)
    cv2.rectangle(image, (88, 75), (100, 115), (0, 180, 80), -1)
    cv2.line(image, (94, 48), (94, 145), (0, 180, 80), 2)
    cv2.line(image, (82, 90), (88, 90), (0, 180, 80), 1)

    found = detect_candidates(image)
    near_first = [item for item in found if item.x < 85]
    near_second = [item for item in found if item.x > 85]
    assert near_first
    assert near_second


def test_empty_or_ambiguous_wide_blob_is_not_reported_as_many_candles():
    image = np.zeros((160, 240, 3), dtype=np.uint8)
    cv2.rectangle(image, (50, 65), (115, 105), (0, 180, 80), -1)
    found = detect_candidates(image)
    assert len(found) <= 1
