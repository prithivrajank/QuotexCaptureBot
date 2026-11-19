"""Load calibration and chart capture settings from a local JSON file."""
import json
from pathlib import Path
from app.vision.calibration import PriceCalibration
from app.vision.time_calibration import TimeCalibration

CONFIG_PATH = Path("visual_config.json")

def load_visual_config(path: Path = CONFIG_PATH) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{path} missing. Run capture setup and create calibration first.")
    return json.loads(path.read_text(encoding="utf-8"))

def load_calibration(path: Path = CONFIG_PATH) -> PriceCalibration:
    data = load_visual_config(path)
    if "calibration" not in data:
        raise ValueError("Add calibration with two visible price-axis anchors before generating OHLC.")
    return PriceCalibration.from_dict(data["calibration"])

def load_time_calibration(path: Path = CONFIG_PATH) -> TimeCalibration:
    data = load_visual_config(path)
    if "time_calibration" not in data:
        raise ValueError("Add time_calibration with two x-axis pixel/time anchors. See VISUAL_RECOGNITION_ENGINE.md.")
    return TimeCalibration.from_dict(data["time_calibration"])
