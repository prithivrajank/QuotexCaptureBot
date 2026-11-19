from app.indicators import calculate_indicators

def test_requires_minimum_history():
    assert calculate_indicators([1.0] * 10)["ready"] is False

def test_calculates_indicators():
    values = calculate_indicators([1 + i * 0.01 for i in range(40)])
    assert values["ready"] is True
    assert values["ema9"] > values["ema21"]
    assert values["rsi14"] is not None
