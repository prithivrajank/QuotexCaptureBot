"""Convert detected candle pixels into explicitly estimated OHLC values."""
from app.vision.detector import CandleCandidate
from app.vision.calibration import PriceCalibration

def reconstruct(candidate: CandleCandidate, calibration: PriceCalibration, symbol: str, timestamp: int, timeframe_seconds: int = 60) -> dict:
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
