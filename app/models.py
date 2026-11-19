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

    @field_validator("symbol")
    @classmethod
    def clean_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("high")
    @classmethod
    def high_consistent(cls, value: float, info):
        return value

    def valid_ohlc(self) -> bool:
        return self.high >= max(self.open, self.close, self.low) and self.low <= min(self.open, self.close, self.high)

class Signal(BaseModel):
    symbol: str
    timestamp: int
    direction: Literal["CALL", "PUT", "WAIT"]
    confidence: float
    reasons: list[str]
    suggested_expiry_minutes: int | None = None
    data_quality: str
    source: str = "visual_estimate"
