"""Heuristic candle candidate detector. Requires chart-only crop and calibration."""
from dataclasses import dataclass, asdict
import cv2
import numpy as np
from app.vision.colors import candle_masks

@dataclass
class CandleCandidate:
    x: int
    body_top: int
    body_bottom: int
    wick_top: int
    wick_bottom: int
    color: str
    body_width: int
    confidence: float

    def to_dict(self):
        return asdict(self)

def detect_candidates(image: np.ndarray, min_body_height: int = 3) -> list[CandleCandidate]:
    bull, bear = candle_masks(image)
    height, width = image.shape[:2]
    candidates = []
    for color, mask in (("bull", bull), ("bear", bear)):
        count, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, 8)
        for i in range(1, count):
            x, y, w, h, area = stats[i]
            if h < min_body_height or w < 2 or w > max(30, width // 20):
                continue
            if area < 5 or h / max(w, 1) < 0.35:
                continue
            cx = int(centroids[i][0])
            # Extend wick using same colour pixels in the candle's narrow vertical column.
            col = mask[:, max(0, cx-1):min(width, cx+2)]
            rows = np.where(np.any(col > 0, axis=1))[0]
            if len(rows) == 0:
                continue
            wt, wb = int(rows.min()), int(rows.max())
            body_top, body_bottom = int(y), int(y+h-1)
            fill_ratio = min(1.0, area / max(1, w*h))
            confidence = float(min(0.95, 0.45 + 0.35*fill_ratio + 0.2*min(1.0, h/12)))
            candidates.append(CandleCandidate(cx, body_top, body_bottom, wt, wb, color, int(w), confidence))
    # Merge detections at almost identical x positions; keep highest confidence candidate.
    candidates.sort(key=lambda c: (c.x, -c.confidence))
    merged = []
    for item in candidates:
        if merged and abs(item.x - merged[-1].x) <= 2:
            if item.confidence > merged[-1].confidence:
                merged[-1] = item
        else:
            merged.append(item)
    return merged
