"""Conservative HSV candle detector with grid-line suppression and body/wick separation."""
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


def _remove_long_grid_lines(mask: np.ndarray) -> np.ndarray:
    """Suppress long horizontal/vertical structures before connected components."""
    height, width = mask.shape[:2]
    horizontal_len = max(25, width // 5)
    vertical_len = max(25, height // 5)
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (horizontal_len, 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vertical_len))
    horizontal = cv2.morphologyEx(mask, cv2.MORPH_OPEN, horizontal_kernel)
    vertical = cv2.morphologyEx(mask, cv2.MORPH_OPEN, vertical_kernel)
    lines = cv2.bitwise_or(horizontal, vertical)
    return cv2.subtract(mask, lines)


def _longest_true_run(values: np.ndarray) -> tuple[int, int] | None:
    indices = np.flatnonzero(values)
    if indices.size == 0:
        return None
    splits = np.where(np.diff(indices) > 1)[0] + 1
    groups = np.split(indices, splits)
    best = max(groups, key=len)
    return int(best[0]), int(best[-1])


def _body_bounds(component: np.ndarray) -> tuple[int, int] | None:
    """Find the dense central body rows; thin wick rows are excluded."""
    row_counts = np.count_nonzero(component, axis=1)
    max_count = int(row_counts.max(initial=0))
    if max_count < 2:
        return None
    threshold = max(2, int(np.ceil(max_count * 0.55)))
    run = _longest_true_run(row_counts >= threshold)
    if run is None or run[1] - run[0] < 1:
        return None
    return run


def detect_candidates(image: np.ndarray, min_body_height: int = 3) -> list[CandleCandidate]:
    if image is None or image.size == 0 or image.ndim != 3:
        raise ValueError("Expected a non-empty BGR chart image")
    bull, bear = candle_masks(image)
    height, width = image.shape[:2]
    candidates = []

    for color, raw_mask in (("bull", bull), ("bear", bear)):
        mask = _remove_long_grid_lines(raw_mask)
        count, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, 8)
        for i in range(1, count):
            x, y, w, h, area = stats[i]
            if h < min_body_height or w < 2 or w > max(30, width // 20):
                continue
            if area < 6 or h / max(w, 1) < 0.45:
                continue

            component = (labels[y:y+h, x:x+w] == i).astype(np.uint8)
            bounds = _body_bounds(component)
            if bounds is None:
                continue
            body_top, body_bottom = y + bounds[0], y + bounds[1]
            body_height = body_bottom - body_top + 1
            if body_height < min_body_height:
                continue

            cx = int(round(float(centroids[i][0])))
            # Only inspect the candidate's own narrow x-span for wick pixels.
            local = mask[:, max(0, x-1):min(width, x+w+1)]
            rows = np.where(np.any(local > 0, axis=1))[0]
            if rows.size == 0:
                continue
            wick_top, wick_bottom = int(rows.min()), int(rows.max())
            if wick_top > body_top or wick_bottom < body_bottom:
                continue

            fill_ratio = min(1.0, area / max(1, w*h))
            body_ratio = body_height / max(1, h)
            # Confidence penalizes sparse/noisy shapes and components dominated by thin lines.
            confidence = float(np.clip(0.42 + 0.28*fill_ratio + 0.25*body_ratio, 0.0, 0.95))
            if body_ratio < 0.20 or fill_ratio < 0.12:
                continue
            candidates.append(CandleCandidate(
                x=cx,
                body_top=int(body_top),
                body_bottom=int(body_bottom),
                wick_top=wick_top,
                wick_bottom=wick_bottom,
                color=color,
                body_width=int(w),
                confidence=confidence,
            ))

    # Deduplicate near-identical x-centres across the two colour masks.
    candidates.sort(key=lambda c: (c.x, -c.confidence))
    merged = []
    for item in candidates:
        if merged and abs(item.x - merged[-1].x) <= 2:
            if item.confidence > merged[-1].confidence:
                merged[-1] = item
        else:
            merged.append(item)
    return merged
