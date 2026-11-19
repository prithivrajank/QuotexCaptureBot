from app.strategy import make_signal

def test_insufficient_history_waits():
    result = make_signal([])
    assert result["direction"] == "WAIT"
