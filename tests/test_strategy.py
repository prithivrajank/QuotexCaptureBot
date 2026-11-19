from app.strategy import make_signal


def test_insufficient_history_waits():
    result = make_signal([])
    assert result["direction"] == "WAIT"
    assert result["suggested_expiry_minutes"] is None


def test_low_visual_confidence_waits():
    candles = [{"close": 1.1, "high": 1.101, "low": 1.099, "confidence": 0.5} for _ in range(50)]
    result = make_signal(candles)
    assert result["direction"] == "WAIT"
    assert "confidence" in result["reasons"][0].lower()


def test_flat_market_waits():
    candles = [
        {"close": 1.1, "high": 1.1001, "low": 1.0999, "confidence": 0.95}
        for _ in range(60)
    ]
    result = make_signal(candles)
    assert result["direction"] == "WAIT"
    assert result["suggested_expiry_minutes"] is None
