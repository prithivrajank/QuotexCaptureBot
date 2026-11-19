import json
from pathlib import Path
from threading import Lock
from app.config import DATA_DIR
from app.models import VisualCandle, Signal

_lock = Lock()
CANDLES_FILE = DATA_DIR / "candles.jsonl"
SIGNALS_FILE = DATA_DIR / "signals.jsonl"

def _append(path: Path, obj: dict) -> None:
    with _lock, path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, separators=(",", ":")) + "\n")

def save_candle(candle: VisualCandle) -> None:
    _append(CANDLES_FILE, candle.model_dump())

def save_signal(signal: Signal) -> None:
    _append(SIGNALS_FILE, signal.model_dump())

def read_jsonl(path: Path, limit: int = 200) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows[-limit:]

def candles(limit: int = 200) -> list[dict]:
    return read_jsonl(CANDLES_FILE, limit)

def signals(limit: int = 100) -> list[dict]:
    return read_jsonl(SIGNALS_FILE, limit)
