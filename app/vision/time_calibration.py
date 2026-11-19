"""Map chart x pixels to Unix candle time using two manually selected x-axis anchors."""
from dataclasses import dataclass

@dataclass(frozen=True)
class TimeCalibration:
    x_left: float
    timestamp_left: float
    x_right: float
    timestamp_right: float

    def __post_init__(self):
        if self.x_right <= self.x_left:
            raise ValueError("Time calibration right x anchor must be greater than left x anchor")
        if self.timestamp_left == self.timestamp_right:
            raise ValueError("Time calibration timestamps must differ")
        if self.timestamp_right < self.timestamp_left:
            raise ValueError("Right time anchor must be later than left time anchor")

    def timestamp_at(self, x: float) -> int:
        ratio = (float(x) - self.x_left) / (self.x_right - self.x_left)
        return int(round(self.timestamp_left + ratio * (self.timestamp_right - self.timestamp_left)))

    def candle_timestamp_at(self, x: float, timeframe_seconds: int) -> int:
        if timeframe_seconds < 1:
            raise ValueError("Timeframe must be positive")
        raw = self.timestamp_at(x)
        return raw - (raw % timeframe_seconds)

    def to_dict(self):
        return {"x_left": self.x_left, "timestamp_left": self.timestamp_left, "x_right": self.x_right, "timestamp_right": self.timestamp_right}

    @classmethod
    def from_dict(cls, value: dict):
        return cls(float(value["x_left"]), float(value["timestamp_left"]), float(value["x_right"]), float(value["timestamp_right"]))
