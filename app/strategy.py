from app.indicators import calculate_indicators

def make_signal(candles: list[dict]) -> dict:
    if len(candles) < 30:
        return {"direction": "WAIT", "confidence": 0.0, "reasons": ["Insufficient completed candles"], "suggested_expiry_minutes": None, "data_quality": "insufficient"}
    latest = candles[-1]
    if latest.get("confidence", 0) < 0.85:
        return {"direction": "WAIT", "confidence": 0.0, "reasons": ["Visual candle confidence below 0.85"], "suggested_expiry_minutes": None, "data_quality": "low"}
    values = calculate_indicators([float(c["close"]) for c in candles])
    if not values.get("ready"):
        return {"direction": "WAIT", "confidence": 0.0, "reasons": [values.get("reason", "Indicators unavailable")], "suggested_expiry_minutes": None, "data_quality": "insufficient"}
    votes = []
    if values["ema9"] > values["ema21"]:
        votes.append("CALL")
    elif values["ema9"] < values["ema21"]:
        votes.append("PUT")
    if values["macd"] > values["macd_signal"]:
        votes.append("CALL")
    elif values["macd"] < values["macd_signal"]:
        votes.append("PUT")
    rsi = values["rsi14"]
    if rsi is not None and rsi < 35:
        votes.append("CALL")
    elif rsi is not None and rsi > 65:
        votes.append("PUT")
    call, put = votes.count("CALL"), votes.count("PUT")
    if call >= 2 and put == 0:
        direction, confidence = "CALL", min(0.95, 0.55 + call * 0.12)
    elif put >= 2 and call == 0:
        direction, confidence = "PUT", min(0.95, 0.55 + put * 0.12)
    else:
        direction, confidence = "WAIT", 0.0
    return {
        "direction": direction, "confidence": confidence,
        "reasons": [f"EMA9={values['ema9']:.6g}; EMA21={values['ema21']:.6g}", f"RSI14={rsi}", f"MACD={values['macd']}; signal={values['macd_signal']}"],
        "suggested_expiry_minutes": 1 if confidence >= 0.75 else (2 if direction != "WAIT" else None),
        "data_quality": "visual_estimate_not_exchange_verified",
    }
