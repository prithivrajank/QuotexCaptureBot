"""Load and validate chart capture settings and manual calibration anchors."""
import json
import math
from pathlib import Path

from app.vision.calibration import PriceCalibration
from app.vision.time_calibration import TimeCalibration

CONFIG_PATH = Path("visual_config.json")


def load_visual_config(path: Path = CONFIG_PATH) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{path} missing. Create a chart profile first.")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Visual profile must be a JSON object.")
    return data


def validate_visual_config(data: dict) -> list[str]:
    """Return actionable profile errors; all calibration pixels are crop-relative."""
    errors = []
    region = data.get("region", data)
    if not isinstance(region, dict):
        return ["region must be a JSON object"]
    try:
        left, top, width, height = (int(region[k]) for k in ("left", "top", "width", "height"))
        if left < 0 or top < 0 or width < 100 or height < 100:
            errors.append("region needs non-negative left/top and width/height of at least 100 pixels")
    except (KeyError, TypeError, ValueError):
        return ["region must contain integer left, top, width and height"]

    try:
        price = PriceCalibration.from_dict(data["calibration"])
        if not all(math.isfinite(v) for v in (price.y_top, price.y_bottom, price.price_top, price.price_bottom)):
            errors.append("price calibration values must be finite")
        if min(price.price_top, price.price_bottom) <= 0:
            errors.append("price-axis anchors must be positive")
        if not (0 <= price.y_top < height and 0 <= price.y_bottom < height):
            errors.append("price calibration y anchors must fall inside the crop (0 to height-1)")
    except (KeyError, TypeError, ValueError, OverflowError):
        errors.append("calibration needs distinct numeric y_top/y_bottom pixels and price_top/price_bottom values")

    try:
        timing = TimeCalibration.from_dict(data["time_calibration"])
        if not all(math.isfinite(v) for v in (timing.x_left, timing.x_right, timing.timestamp_left, timing.timestamp_right)):
            errors.append("time calibration values must be finite")
        if not (0 <= timing.x_left < width and 0 <= timing.x_right < width):
            errors.append("time calibration x anchors must fall inside the crop (0 to width-1)")
        if timing.timestamp_left <= 0 or timing.timestamp_right <= timing.timestamp_left:
            errors.append("time anchors must be positive and the right timestamp must be later")
    except (KeyError, TypeError, ValueError, OverflowError):
        errors.append("time_calibration needs distinct numeric x_left/x_right pixels and increasing positive timestamps")

    try:
        timeframe = int(data.get("timeframe_seconds", 60))
        if timeframe < 1 or timeframe > 3600:
            errors.append("timeframe_seconds must be between 1 and 3600")
    except (TypeError, ValueError):
        errors.append("timeframe_seconds must be an integer")

    symbol = data.get("symbol")
    if not isinstance(symbol, str) or not symbol.strip():
        errors.append("symbol must be a non-empty string")
    return errors


def load_calibration(path: Path = CONFIG_PATH) -> PriceCalibration:
    data = load_visual_config(path)
    errors = validate_visual_config(data)
    price_errors = [e for e in errors if "price" in e or e.startswith("calibration")]
    if price_errors:
        raise ValueError("Invalid price calibration: " + "; ".join(price_errors))
    return PriceCalibration.from_dict(data["calibration"])


def load_time_calibration(path: Path = CONFIG_PATH) -> TimeCalibration:
    data = load_visual_config(path)
    errors = validate_visual_config(data)
    time_errors = [e for e in errors if "time" in e]
    if time_errors:
        raise ValueError("Invalid time calibration: " + "; ".join(time_errors))
    return TimeCalibration.from_dict(data["time_calibration"])
