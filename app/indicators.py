import numpy as np
import pandas as pd

def calculate_indicators(closes: list[float]) -> dict:
    if len(closes) < 30:
        return {"ready": False, "reason": "Need at least 30 completed candles"}
    s = pd.Series(closes, dtype="float64")
    delta = s.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean().replace(0, np.nan)
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    ema9 = s.ewm(span=9, adjust=False).mean()
    ema21 = s.ewm(span=21, adjust=False).mean()
    ema12 = s.ewm(span=12, adjust=False).mean()
    ema26 = s.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    mid = s.rolling(20).mean()
    std = s.rolling(20).std(ddof=0)
    return {
        "ready": True,
        "rsi14": _last(rsi),
        "ema9": _last(ema9),
        "ema21": _last(ema21),
        "macd": _last(macd),
        "macd_signal": _last(signal),
        "bb_upper": _last(mid + 2 * std),
        "bb_middle": _last(mid),
        "bb_lower": _last(mid - 2 * std),
    }

def _last(series):
    value = series.iloc[-1]
    return None if pd.isna(value) else float(value)
