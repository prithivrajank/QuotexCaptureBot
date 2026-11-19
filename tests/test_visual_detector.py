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
