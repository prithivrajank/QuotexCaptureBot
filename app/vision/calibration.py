"""Pixel-to-price calibration using two user-supplied chart-axis anchors."""
from dataclasses import dataclass

@dataclass(frozen=True)
class PriceCalibration:
    y_top: float
    price_top: float
    y_bottom: float
    price_bottom: float

    def __post_init__(self):
        if self.y_top == self.y_bottom:
            raise ValueError("Calibration pixel anchors must differ")
        if self.price_top == self.price_bottom:
            raise ValueError("Calibration prices must differ")

    def price_at(self, y: float) -> float:
        ratio = (y - self.y_top) / (self.y_bottom - self.y_top)
        return self.price_top + ratio * (self.price_bottom - self.price_top)

    def to_dict(self):
        return {"y_top": self.y_top, "price_top": self.price_top, "y_bottom": self.y_bottom, "price_bottom": self.price_bottom}

    @classmethod
    def from_dict(cls, value: dict):
        return cls(float(value["y_top"]), float(value["price_top"]), float(value["y_bottom"]), float(value["price_bottom"]))
