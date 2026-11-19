"""Conservative multi-indicator signal filter; scores are heuristic, not win probabilities."""
from app.indicators import calculate_indicators


def make_signal(candles: list[dict]) -> dict:
    if len(candles) < 50:
        return _wait("Need at least 50 completed candles for EMA50 and market context", "insufficient")
    latest = candles[-1]
    if latest.get("confidence", 0) < 0.80:
        return _wait("Latest visual candle confidence/shape score below 0.80", "low")
    if any(c.get("confidence", 0) < 0.72 for c in candles[-20:]):
        return _wait("Recent visual candle shape quality is inconsistent", "low")

    values = calculate_indicators(candles)
    if not values.get("ready"):
        return _wait(values.get("reason", "Indicators unavailable"), "insufficient")

    close = values["close"]
    rsi = values["rsi14"]
    atr = values["atr14"]
    support, resistance = values["support20"], values["resistance20"]
    if None in (close, rsi, atr, support, resistance) or atr <= 0:
        return _wait("Market structure indicators are unavailable", "insufficient")

    # Avoid entries in compressed/sideways conditions or directly into nearby S/R.
    if values["bb_width_pct"] is None or values["bb_width_pct"] < 0.035 or values["trend_strength"] < 0.12:
        return _wait("Sideways or low-volatility market filter", "ready")
    near_support = abs(close - support) <= atr * 0.18
    near_resistance = abs(resistance - close) <= atr * 0.18
    if near_support or near_resistance:
        return _wait("Price is too close to a recent support/resistance boundary", "ready")

    call_votes, put_votes, reasons = 0, 0, []
    if values["ema9"] > values["ema21"] > values["ema50"]:
        call_votes += 2
        reasons.append("EMA9 > EMA21 > EMA50 bullish alignment")
    elif values["ema9"] < values["ema21"] < values["ema50"]:
        put_votes += 2
        reasons.append("EMA9 < EMA21 < EMA50 bearish alignment")

    if values["macd"] > values["macd_signal"]:
        call_votes += 1
        reasons.append("MACD above signal")
    elif values["macd"] < values["macd_signal"]:
        put_votes += 1
        reasons.append("MACD below signal")

    if 50 <= rsi <= 68:
        call_votes += 1
        reasons.append(f"RSI bullish momentum ({rsi:.1f})")
    elif 32 <= rsi < 50:
        put_votes += 1
        reasons.append(f"RSI bearish momentum ({rsi:.1f})")
    elif rsi > 75 or rsi < 25:
        return _wait(f"RSI extreme ({rsi:.1f}); avoid chasing", "ready")

    if close > values["bb_middle"] and close < values["bb_upper"]:
        call_votes += 1
        reasons.append("Price in upper half of Bollinger range")
    elif close < values["bb_middle"] and close > values["bb_lower"]:
        put_votes += 1
        reasons.append("Price in lower half of Bollinger range")

    if call_votes >= 4 and put_votes == 0:
        direction, score = "CALL", call_votes
    elif put_votes >= 4 and call_votes == 0:
        direction, score = "PUT", put_votes
    else:
        return _wait("Indicator votes are mixed or insufficient", "ready")

    # This score is a rule-strength score, not a statistical probability.
    confidence = min(0.92, 0.52 + score * 0.08 + min(values["trend_strength"], 1.0) * 0.08)
    strong_trend = values["trend_strength"] >= 0.45 and score >= 5
    expiry = 1 if strong_trend and confidence >= 0.78 else 2
    reasons.extend([
        f"BB width={values['bb_width_pct']:.4f}%",
        f"ATR14={atr:.8g}; trend strength={values['trend_strength']:.3f}",
        f"Support20={support:.8g}; Resistance20={resistance:.8g}",
        "Confidence is a heuristic rule score, not a probability or guaranteed win rate",
    ])
    return {
        "direction": direction,
        "confidence": round(confidence, 3),
        "reasons": reasons,
        "suggested_expiry_minutes": expiry,
        "data_quality": "visual_estimate_not_exchange_verified",
    }


def _wait(reason: str, quality: str) -> dict:
    return {
        "direction": "WAIT",
        "confidence": 0.0,
        "reasons": [reason],
        "suggested_expiry_minutes": None,
        "data_quality": quality,
    }
