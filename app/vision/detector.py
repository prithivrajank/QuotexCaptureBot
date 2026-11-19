"""Conservative HSV candle detector with grid suppression and merged-shape splitting."""
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
    return cv2.subtract(mask, cv2.bitwise_or(horizontal, vertical))


def _longest_true_run(values: np.ndarray) -> tuple[int, int] | None:
    indices = np.flatnonzero(values)
    if indices.size == 0:
        return None
    groups = np.split(indices, np.where(np.diff(indices) > 1)[0] + 1)
    best = max(groups, key=len)
    return int(best[0]), int(best[-1])


def _body_bounds(component: np.ndarray) -> tuple[int, int] | None:
    """Find dense central body rows; thin wick rows are excluded."""
    row_counts = np.count_nonzero(component, axis=1)
    max_count = int(row_counts.max(initial=0))
    if max_count < 2:
        return None
    threshold = max(2, int(np.ceil(max_count * 0.55)))
    run = _longest_true_run(row_counts >= threshold)
    if run is None or run[1] - run[0] < 1:
        return None
    return run


def _split_wide_component(component: np.ndarray, max_width: int) -> list[tuple[int, int]]:
    """Split touching candles at low-ink vertical valleys; reject unsplittable blobs."""
    width = component.shape[1]
    if width <= max_width:
        return [(0, width)]
    projection = np.count_nonzero(component, axis=0).astype(float)
    # Smooth single-pixel gaps but preserve valleys between neighbouring bodies.
    smooth = np.convolve(projection, np.ones(3) / 3.0, mode="same")
    midpoint = width // 2
    lo = max(2, midpoint - max_width // 2)
    hi = min(width - 2, midpoint + max_width // 2 + 1)
    if lo >= hi:
        return []
    valley = lo + int(np.argmin(smooth[lo:hi]))
    peak_left = float(np.max(smooth[:valley])) if valley else 0.0
    peak_right = float(np.max(smooth[valley + 1:])) if valley + 1 < width else 0.0
    valley_strength = float(smooth[valley])
    if min(peak_left, peak_right) <= 0 or valley_strength > min(peak_left, peak_right) * 0.58:
        return []
    left = _split_wide_component(component[:, :valley], max_width)
    right = _split_wide_component(component[:, valley:], max_width)
    if not left or not right:
        return []
    return left + [(start + valley, end + valley) for start, end in right]


def detect_candidates(image: np.ndarray, min_body_height: int = 3) -> list[CandleCandidate]:
    if image is None or image.size == 0 or image.ndim != 3:
        raise ValueError("Expected a non-empty BGR chart image")
    bull, bear = candle_masks(image)
    height, width = image.shape[:2]
    max_body_width = 30
    candidates = []

    for color, raw_mask in (("bull", bull), ("bear", bear)):
        mask = _remove_long_grid_lines(raw_mask)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
        for i in range(1, count):
            x, y, w, h, area = stats[i]
            if h < min_body_height or w < 2 or area < 6 or h / max(w, 1) < 0.45:
                continue
            component = (labels[y:y+h, x:x+w] == i).astype(np.uint8)
            segments = _split_wide_component(component, max_body_width)
            for start, end in segments:
                piece = component[:, start:end]
                pw = end - start
                if pw < 2 or pw > max_body_width:
                    continue
                bounds = _body_bounds(piece)
                if bounds is None:
                    continue
                body_top, body_bottom = y + bounds[0], y + bounds[1]
                body_height = body_bottom - body_top + 1
                if body_height < min_body_height:
                    continue
                local = piece
                rows = np.where(np.any(local > 0, axis=1))[0]
                if rows.size == 0:
                    continue
                wick_top, wick_bottom = y + int(rows.min()), y + int(rows.max())
                if wick_top > body_top or wick_bottom < body_bottom:
                    continue
                fill_ratio = float(np.count_nonzero(piece) / max(1, piece.shape[0] * piece.shape[1]))
                body_ratio = body_height / max(1, wick_bottom - wick_top + 1)
                if body_ratio < 0.20 or fill_ratio < 0.12:
                    continue
                confidence = float(np.clip(0.70 + 0.20 * fill_ratio + 0.10 * body_ratio, 0.0, 0.95))
                candidates.append(CandleCandidate(
                    x=int(x + start + (pw - 1) / 2),
                    body_top=int(body_top),
                    body_bottom=int(body_bottom),
                    wick_top=int(wick_top),
                    wick_bottom=int(wick_bottom),
                    color=color,
                    body_width=int(pw),
                    confidence=confidence,
                ))

    # Resolve same-candle detections across overlapping bull/bear masks.
    candidates.sort(key=lambda c: (c.x, -c.confidence))
    merged = []
    for item in candidates:
        if merged and abs(item.x - merged[-1].x) <= max(2, min(item.body_width, merged[-1].body_width) // 3):
            previous = merged[-1]
            overlap = min(item.wick_bottom, previous.wick_bottom) >= max(item.wick_top, previous.wick_top)
            if overlap:
                if item.confidence > previous.confidence:
                    merged[-1] = item
                continue
        merged.append(item)
    return merged
