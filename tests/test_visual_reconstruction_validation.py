import pytest

from app.vision.calibration import PriceCalibration
from app.vision.detector import CandleCandidate
from app.vision.reconstruct import reconstruct, validate_candidate


def candidate(**overrides):
    values = dict(
        x=20, body_top=30, body_bottom=45, wick_top=25,
        wick_bottom=50, color="bull", body_width=8, confidence=0.9,
    )
    values.update(overrides)
    return CandleCandidate(**values)


def test_valid_candidate_reconstructs_consistent_ohlc():
    calibration = PriceCalibration(0, 2.0, 100, 1.0)
    candle = reconstruct(candidate(), calibration, "EURUSD_OTC", 1_800_000_000, 60)
    assert candle["source"] == "visual_estimate"
    assert candle["high"] >= max(candle["open"], candle["close"])
    assert candle["low"] <= min(candle["open"], candle["close"])


@pytest.mark.parametrize("overrides", [
    {"body_top": 46},
    {"wick_top": 31},
    {"body_width": 0},
    {"confidence": 1.5},
    {"color": "blue"},
    {"wick_bottom": 600},
])
def test_malformed_candidate_is_rejected(overrides):
    with pytest.raises(ValueError):
        validate_candidate(candidate(**overrides))


def test_non_positive_calibrated_prices_are_rejected():
    with pytest.raises(ValueError, match="positive"):
        PriceCalibration(0, 1.0, 100, -1.0)



def test_reconstruction_requires_timeframe_aligned_timestamp():
    calibration = PriceCalibration(0, 2.0, 100, 1.0)
    with pytest.raises(ValueError):
        reconstruct(candidate(), calibration, "EURUSD_OTC", 1_800_000_001, 60)
