"""Thread-safe JSONL prototype storage with upsert and signal outcome updates."""
import json
from pathlib import Path
from threading import Lock
from app.config import DATA_DIR
from app.models import VisualCandle, Signal

_lock = Lock()
CANDLES_FILE = DATA_DIR / "candles.jsonl"
SIGNALS_FILE = DATA_DIR / "signals.jsonl"


def _read_all(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
            except json.JSONDecodeError:
                continue
    return rows


def _write_all(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    temporary.replace(path)


def _key(row: dict) -> tuple:
    return (row.get("symbol"), int(row.get("timeframe_seconds", 60)), int(row.get("timestamp", 0)))


def upsert_candle(candle: VisualCandle) -> bool:
    item = candle.model_dump()
    with _lock:
        rows = _read_all(CANDLES_FILE)
        key = _key(item)
        old = next((row for row in rows if _key(row) == key), None)
        was_closed = bool(old and old.get("is_closed"))
        merged = {**(old or {}), **item}
        if was_closed:
            merged = {**old, "is_closed": True}
        rows = [row for row in rows if _key(row) != key]
        rows.append(merged)
        rows.sort(key=lambda row: (row.get("symbol", ""), int(row.get("timeframe_seconds", 60)), int(row.get("timestamp", 0))))
        _write_all(CANDLES_FILE, rows)
        return bool(candle.is_closed and not was_closed)


def save_signal(signal: Signal) -> bool:
    item = signal.model_dump()
    with _lock:
        rows = _read_all(SIGNALS_FILE)
        key = _key(item)
        if any(_key(row) == key for row in rows):
            return False
        rows.append(item)
        rows.sort(key=lambda row: (row.get("symbol", ""), int(row.get("timeframe_seconds", 60)), int(row.get("timestamp", 0))))
        _write_all(SIGNALS_FILE, rows)
        return True


def evaluate_pending_signals(symbol: str, timeframe_seconds: int, completed_candles: list[dict]) -> int:
    """Evaluate signals only when a closed candle reaches their expiry timestamp."""
    if not completed_candles:
        return 0
    latest = max(completed_candles, key=lambda row: int(row["timestamp"]))
    latest_ts = int(latest["timestamp"])
    latest_close = float(latest["close"])
    changed = 0
    with _lock:
        rows = _read_all(SIGNALS_FILE)
        for row in rows:
            if row.get("symbol") != symbol.upper() or int(row.get("timeframe_seconds", 60)) != timeframe_seconds:
                continue
            if row.get("outcome") != "PENDING":
                continue
            expiry = row.get("suggested_expiry_minutes")
            entry = row.get("entry_price")
            if not expiry or entry is None or row.get("direction") not in ("CALL", "PUT"):
                row["outcome"] = "NOT_EVALUATED"
                row["evaluated_at"] = latest_ts
                changed += 1
                continue
            target_ts = int(row["timestamp"]) + int(expiry) * 60
            if latest_ts < target_ts:
                continue
            if latest_close == float(entry):
                outcome = "DRAW"
            elif (row["direction"] == "CALL" and latest_close > float(entry)) or (row["direction"] == "PUT" and latest_close < float(entry)):
                outcome = "WIN"
            else:
                outcome = "LOSS"
            row["outcome"] = outcome
            row["outcome_price"] = latest_close
            row["evaluated_at"] = latest_ts
            changed += 1
        if changed:
            _write_all(SIGNALS_FILE, rows)
    return changed


def read_jsonl(path: Path, limit: int = 200) -> list[dict]:
    with _lock:
        return _read_all(path)[-limit:]


def candles(limit: int = 200, symbol: str | None = None, timeframe_seconds: int | None = None, closed_only: bool = False) -> list[dict]:
    rows = read_jsonl(CANDLES_FILE, 100000)
    if symbol:
        rows = [row for row in rows if row.get("symbol") == symbol.upper()]
    if timeframe_seconds is not None:
        rows = [row for row in rows if int(row.get("timeframe_seconds", 60)) == timeframe_seconds]
    if closed_only:
        rows = [row for row in rows if row.get("is_closed")]
    return rows[-limit:]


def signals(limit: int = 100, symbol: str | None = None, outcome: str | None = None) -> list[dict]:
    rows = read_jsonl(SIGNALS_FILE, 100000)
    if symbol:
        rows = [row for row in rows if row.get("symbol") == symbol.upper()]
    if outcome:
        rows = [row for row in rows if row.get("outcome") == outcome.upper()]
    return rows[-limit:]
