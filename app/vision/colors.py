"""Configurable candle colour segmentation for common chart themes."""
import cv2
import numpy as np

DEFAULT_PALETTE = {
    "bull": {"h_min": 35, "h_max": 95, "s_min": 55, "v_min": 45},
    "bear": {"h_min": 0, "h_max": 12, "s_min": 70, "v_min": 45},
}

def _mask_hsv(hsv: np.ndarray, cfg: dict) -> np.ndarray:
    return cv2.inRange(
        hsv,
        np.array([cfg["h_min"], cfg["s_min"], cfg["v_min"]], dtype=np.uint8),
        np.array([cfg["h_max"], 255, 255], dtype=np.uint8),
    )

def candle_masks(image: np.ndarray, palette: dict | None = None) -> tuple[np.ndarray, np.ndarray]:
    if image is None or image.size == 0:
        raise ValueError("Empty chart image")
    cfg = palette or DEFAULT_PALETTE
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    bull = _mask_hsv(hsv, cfg["bull"])
    bear_cfg = cfg["bear"]
    if bear_cfg["h_min"] <= bear_cfg["h_max"]:
        bear = _mask_hsv(hsv, bear_cfg)
    else:
        low = cv2.inRange(hsv, np.array([0, bear_cfg["s_min"], bear_cfg["v_min"]]), np.array([bear_cfg["h_max"],255,255]))
        high = cv2.inRange(hsv, np.array([bear_cfg["h_min"], bear_cfg["s_min"], bear_cfg["v_min"]]), np.array([179,255,255]))
        bear = cv2.bitwise_or(low, high)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 3))
    return cv2.morphologyEx(bull, cv2.MORPH_OPEN, kernel), cv2.morphologyEx(bear, cv2.MORPH_OPEN, kernel)
