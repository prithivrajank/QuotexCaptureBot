from app.storage import evaluate_pending_signals


def test_call_outcome_win(tmp_path, monkeypatch):
    import app.storage as storage
    monkeypatch.setattr(storage, "SIGNALS_FILE", tmp_path / "signals.jsonl")
    storage.SIGNALS_FILE.write_text(
        '{"symbol":"EURUSD_OTC","timeframe_seconds":60,"timestamp":1000,"direction":"CALL","suggested_expiry_minutes":1,"entry_price":1.1,"outcome":"PENDING"}\n',
        encoding="utf-8",
    )
    count = evaluate_pending_signals("EURUSD_OTC", 60, [{"timestamp":1060, "close":1.101}])
    assert count == 1
    row = storage.signals(10)[0]
    assert row["outcome"] == "WIN"
    assert row["outcome_price"] == 1.101


def test_wait_signal_not_evaluated(tmp_path, monkeypatch):
    import app.storage as storage
    monkeypatch.setattr(storage, "SIGNALS_FILE", tmp_path / "signals.jsonl")
    storage.SIGNALS_FILE.write_text(
        '{"symbol":"EURUSD_OTC","timeframe_seconds":60,"timestamp":1000,"direction":"WAIT","suggested_expiry_minutes":null,"entry_price":1.1,"outcome":"NOT_EVALUATED"}\n',
        encoding="utf-8",
    )
    count = evaluate_pending_signals("EURUSD_OTC", 60, [{"timestamp":1200, "close":1.2}])
    assert count == 0


def test_uses_first_closed_candle_at_or_after_expiry(tmp_path, monkeypatch):
    import app.storage as storage
    monkeypatch.setattr(storage, "SIGNALS_FILE", tmp_path / "signals.jsonl")
    storage.SIGNALS_FILE.write_text(
        '{"symbol":"EURUSD_OTC","timeframe_seconds":60,"timestamp":1000,"direction":"CALL","suggested_expiry_minutes":1,"entry_price":1.1,"outcome":"PENDING"}\\n',
        encoding="utf-8",
    )
    completed = [
        {"timestamp":1180, "close": 1.105},
        {"timestamp":1060, "close": 1.101},
        {"timestamp":1120, "close": 1.090},
    ]
    assert storage.evaluate_pending_signals("EURUSD_OTC", 60, completed) == 1
    row = storage.signals(10)[0]
    assert row["outcome"] == "WIN"
    assert row["evaluated_at"] == 1060
    assert row["outcome_price"] == 1.101
