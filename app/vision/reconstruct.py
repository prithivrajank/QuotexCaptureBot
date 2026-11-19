"""Convert detected candle pixels into explicitly estimated OHLC values."""
import math

from app.vision.detector import CandleCandidate
from app.vision.calibration import PriceCalibration


def validate_candidate(candidate: CandleCandidate) -> None:
    """Reject malformed pixel geometry before converting it into a price candle."""
    values = (
        candidate.x, candidate.body_top, candidate.body_bottom,
        candidate.wick_top, candidate.wick_bottom, candidate.body_width,
        candidate.confidence,
    )
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError("Candidate contains non-finite geometry")
    if candidate.color not in {"bull", "bear"}:
        raise ValueError("Candidate has an unknown candle colour")
    if candidate.body_width < 2 or candidate.body_width > 30:
        raise ValueError("Candidate body width is outside the supported range")
    if not 0 <= candidate.confidence <= 1:
        raise ValueError("Candidate confidence is outside 0..1")
    if candidate.wick_top > candidate.body_top or candidate.wick_bottom < candidate.body_bottom:
        raise ValueError("Wick bounds do not contain the candle body")
    if candidate.body_top >= candidate.body_bottom:
        raise ValueError("Candle body has no positive pixel height")
    body_height = candidate.body_bottom - candidate.body_top + 1
    total_height = candidate.wick_bottom - candidate.wick_top + 1
    if total_height <= 0 or body_height / total_height < 0.08:
        raise ValueError("Candle body is implausibly small relative to its wick")
    if total_height > 500:
        raise ValueError("Candidate height is implausibly large")


def reconstruct(candidate: CandleCandidate, calibration: PriceCalibration, symbol: str, timestamp: int, timeframe_seconds: int = 60) -> dict:
    validate_candidate(candidate)
    if timestamp <= 0 or timeframe_seconds < 1:
        raise ValueError("Timestamp and timeframe must be positive")
    p_wick_top = calibration.price_at(candidate.wick_top)
    p_wick_bottom = calibration.price_at(candidate.wick_bottom)
    p_body_top = calibration.price_at(candidate.body_top)
    p_body_bottom = calibration.price_at(candidate.body_bottom)
    body_high = max(p_body_top, p_body_bottom)
    body_low = min(p_body_top, p_body_bottom)
    if candidate.color == "bull":
        open_price, close_price = p_body_bottom, p_body_top
    else:
        open_price, close_price = p_body_top, p_body_bottom
    high = max(p_wick_top, p_wick_bottom, body_high)
    low = min(p_wick_top, p_wick_bottom, body_low)
    prices = (open_price, high, low, close_price)
    if not all(math.isfinite(value) and value > 0 for value in prices):
        raise ValueError("Calibration produced a non-finite or non-positive price")
    if high < max(open_price, close_price) or low > min(open_price, close_price) or high < low:
        raise ValueError("Reconstructed OHLC geometry is inconsistent")
    return {
        "symbol": symbol.upper(),
        "timeframe_seconds": timeframe_seconds,
        "timestamp": int(timestamp),
        "open": float(open_price),
        "high": float(high),
        "low": float(low),
        "close": float(close_price),
        "confidence": float(candidate.confidence),
        "source": "visual_estimate",
        "visual": {"x": candidate.x, "color": candidate.color, "body_width": candidate.body_width},
    }
