import json

import app.storage as storage


def sample_report(**overrides):
    report = {
        "symbol": "EURUSD_OTC",
        "timeframe_seconds": 60,
        "reported_at": 1795000000,
        "candidate_count": 12,
        "unique_slots": 10,
        "duplicate_count": 2,
        "missing_timestamps": [1794999880],
        "calibration_structurally_valid": True,
        "source": "visual_estimate",
    }
    report.update(overrides)
    return report


def test_quality_report_is_persisted_and_replaced_per_pair(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "_engine", None)
    monkeypatch.setattr(storage, "QUALITY_FILE", tmp_path / "quality.jsonl")
    storage.save_quality_report(sample_report())
    storage.save_quality_report(sample_report(reported_at=1795000030, duplicate_count=0, missing_timestamps=[]))
    rows = storage.quality_reports("EURUSD_OTC", 60)
    assert len(rows) == 1
    assert rows[0]["reported_at"] == 1795000030
    assert rows[0]["duplicate_count"] == 0


def test_quality_reports_filter_by_symbol_and_timeframe(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "_engine", None)
    monkeypatch.setattr(storage, "QUALITY_FILE", tmp_path / "quality.jsonl")
    storage.save_quality_report(sample_report())
    storage.save_quality_report(sample_report(symbol="GBPUSD_OTC", timeframe_seconds=120))
    assert len(storage.quality_reports(symbol="EURUSD_OTC")) == 1
    assert len(storage.quality_reports(timeframe_seconds=120)) == 1
    assert storage.quality_reports(symbol="USDJPY_OTC") == []
