from pydantic import BaseModel, Field, field_validator
from typing import Literal


class VisualCandle(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    timeframe_seconds: int = Field(default=60, ge=1, le=3600)
    timestamp: int = Field(gt=0)
    open: float
    high: float
    low: float
    close: float
    confidence: float = Field(ge=0, le=1)
    source: Literal["visual_estimate"] = "visual_estimate"
    is_closed: bool = False

    @field_validator("symbol")
    @classmethod
    def clean_symbol(cls, value: str) -> str:
        return value.strip().upper()

    def valid_ohlc(self) -> bool:
        import math
        values = (self.open, self.high, self.low, self.close)
        if not all(math.isfinite(v) for v in values):
            return False
        return self.high >= max(self.open, self.close, self.low) and self.low <= min(self.open, self.close, self.high)


class Signal(BaseModel):
    symbol: str
    timeframe_seconds: int = 60
    timestamp: int
    direction: Literal["CALL", "PUT", "WAIT"]
    confidence: float
    reasons: list[str]
    suggested_expiry_minutes: int | None = None
    entry_price: float | None = None
    outcome: Literal["PENDING", "WIN", "LOSS", "DRAW", "NOT_EVALUATED"] = "NOT_EVALUATED"
    outcome_price: float | None = None
    evaluated_at: int | None = None
    data_quality: str
    source: str = "visual_estimate"


class CaptureDiagnostics(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    timeframe_seconds: int = Field(ge=1, le=3600)
    reported_at: int = Field(gt=0)
    candidate_count: int = Field(ge=0)
    unique_slots: int = Field(ge=0)
    duplicate_count: int = Field(ge=0)
    missing_timestamps: list[int] = Field(default_factory=list, max_length=1000)
    calibration_structurally_valid: bool = True
    latest_candidate_timestamp: int | None = None
    expected_current_slot: int | None = None
    timestamp_drift_seconds: int | None = None
    timestamp_alignment_status: Literal["ALIGNED", "LAGGING", "AHEAD", "NO_CANDLES"] = "NO_CANDLES"
    source: Literal["visual_estimate"] = "visual_estimate"

    @field_validator("symbol")
    @classmethod
    def clean_diagnostic_symbol(cls, value: str) -> str:
        return value.strip().upper()
