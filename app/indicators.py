"""Technical indicators calculated only from completed visual-estimate candles."""
import numpy as np
import pandas as pd


def calculate_indicators(candles: list[dict] | list[float]) -> dict:
    if len(candles) < 30:
        return {"ready": False, "reason": "Need at least 30 completed candles"}
    if isinstance(candles[0], dict):
        frame = pd.DataFrame(candles)
        close = pd.to_numeric(frame["close"], errors="coerce")
        high = pd.to_numeric(frame["high"], errors="coerce")
        low = pd.to_numeric(frame["low"], errors="coerce")
    else:
        close = pd.Series(candles, dtype="float64")
        high = close
        low = close
    if close.isna().any() or high.isna().any() or low.isna().any():
        return {"ready": False, "reason": "Candle history contains invalid OHLC values"}

    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.mask((loss == 0) & (gain > 0), 100).mask((gain == 0) & (loss > 0), 0)

    mid = close.rolling(20).mean()
    std = close.rolling(20).std(ddof=0)
    bb_upper, bb_lower = mid + 2 * std, mid - 2 * std
    bb_width_pct = ((bb_upper - bb_lower) / mid.abs().replace(0, np.nan)) * 100

    previous_close = close.shift(1)
    true_range = pd.concat([(high-low).abs(), (high-previous_close).abs(), (low-previous_close).abs()], axis=1).max(axis=1)
    atr14 = true_range.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    recent_high = high.shift(1).rolling(20).max()
    recent_low = low.shift(1).rolling(20).min()
    atr = _last(atr14)
    spread = abs(_last(ema9) - _last(ema21))
    trend_strength = spread / atr if atr and atr > 0 else 0.0
    width = _last(bb_width_pct)
    return {
        "ready": True,
        "close": _last(close),
        "rsi14": _last(rsi),
        "ema9": _last(ema9),
        "ema21": _last(ema21),
        "ema50": _last(ema50),
        "macd": _last(macd),
        "macd_signal": _last(macd_signal),
        "bb_upper": _last(bb_upper),
        "bb_middle": _last(mid),
        "bb_lower": _last(bb_lower),
        "bb_width_pct": width,
        "atr14": atr,
        "trend_strength": float(trend_strength),
        "resistance20": _last(recent_high),
        "support20": _last(recent_low),
    }


def _last(series):
    value = series.iloc[-1]
    return None if pd.isna(value) else float(value)
