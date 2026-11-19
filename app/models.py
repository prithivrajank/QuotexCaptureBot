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
        values = (self.open, self.high, self.low, self.close)
        if not all(__import__("math").isfinite(v) for v in values):
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
    data_quality: str
    source: str = "visual_estimate"
