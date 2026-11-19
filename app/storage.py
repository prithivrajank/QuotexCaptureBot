"""Storage backend: PostgreSQL/SQLite via SQLAlchemy when DATABASE_URL is set; JSONL fallback otherwise."""
import json
from pathlib import Path
from threading import Lock
from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, Boolean, Text, select, and_, update, insert
from app.config import DATA_DIR, DATABASE_URL
from app.models import VisualCandle, Signal

_lock = Lock()
CANDLES_FILE = DATA_DIR / "candles.jsonl"
SIGNALS_FILE = DATA_DIR / "signals.jsonl"

_engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None
_metadata = MetaData()
_candle_table = Table(
    "visual_candles", _metadata,
    Column("symbol", String(40), primary_key=True),
    Column("timeframe_seconds", Integer, primary_key=True),
    Column("timestamp", Integer, primary_key=True),
    Column("is_closed", Boolean, nullable=False, default=False),
    Column("payload", Text, nullable=False),
)
_signal_table = Table(
    "signal_history", _metadata,
    Column("symbol", String(40), primary_key=True),
    Column("timeframe_seconds", Integer, primary_key=True),
    Column("timestamp", Integer, primary_key=True),
    Column("outcome", String(20), nullable=False),
    Column("payload", Text, nullable=False),
)
if _engine is not None:
    _metadata.create_all(_engine)


def storage_backend() -> str:
    return "database" if _engine is not None else "jsonl"


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
            handle.write(json.dumps(row, separators=(",", ":")) + "\\n")
    temporary.replace(path)


def _key(row: dict) -> tuple:
    return (row.get("symbol"), int(row.get("timeframe_seconds", 60)), int(row.get("timestamp", 0)))


def _db_rows(table: Table) -> list[dict]:
    with _engine.connect() as connection:
        records = connection.execute(select(table.c.payload)).scalars().all()
    return [json.loads(value) for value in records]


def upsert_candle(candle: VisualCandle) -> bool:
    item = candle.model_dump()
    key = _key(item)
    with _lock:
        if _engine is not None:
            where = and_(_candle_table.c.symbol == key[0], _candle_table.c.timeframe_seconds == key[1], _candle_table.c.timestamp == key[2])
            with _engine.begin() as connection:
                old_payload = connection.execute(select(_candle_table.c.payload, _candle_table.c.is_closed).where(where)).first()
                was_closed = bool(old_payload and old_payload.is_closed)
                merged = {**(json.loads(old_payload.payload) if old_payload else {}), **item}
                if was_closed:
                    merged = {**json.loads(old_payload.payload), "is_closed": True}
                values = {"is_closed": bool(merged.get("is_closed")), "payload": json.dumps(merged, separators=(",", ":"))}
                if old_payload:
                    connection.execute(update(_candle_table).where(where).values(**values))
                else:
                    connection.execute(insert(_candle_table).values(symbol=key[0], timeframe_seconds=key[1], timestamp=key[2], **values))
                return bool(candle.is_closed and not was_closed)

        rows = _read_all(CANDLES_FILE)
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
    key = _key(item)
    with _lock:
        if _engine is not None:
            where = and_(_signal_table.c.symbol == key[0], _signal_table.c.timeframe_seconds == key[1], _signal_table.c.timestamp == key[2])
            with _engine.begin() as connection:
                exists = connection.execute(select(_signal_table.c.timestamp).where(where)).first()
                if exists:
                    return False
                connection.execute(insert(_signal_table).values(symbol=key[0], timeframe_seconds=key[1], timestamp=key[2], outcome=item.get("outcome", "NOT_EVALUATED"), payload=json.dumps(item, separators=(",", ":"))))
                return True

        rows = _read_all(SIGNALS_FILE)
        if any(_key(row) == key for row in rows):
            return False
        rows.append(item)
        rows.sort(key=lambda row: (row.get("symbol", ""), int(row.get("timeframe_seconds", 60)), int(row.get("timestamp", 0))))
        _write_all(SIGNALS_FILE, rows)
        return True


def evaluate_pending_signals(symbol: str, timeframe_seconds: int, completed_candles: list[dict]) -> int:
    if not completed_candles:
        return 0
    latest = max(completed_candles, key=lambda row: int(row["timestamp"]))
    latest_ts, latest_close = int(latest["timestamp"]), float(latest["close"])
    changed = 0
    with _lock:
        rows = _db_rows(_signal_table) if _engine is not None else _read_all(SIGNALS_FILE)
        for row in rows:
            if row.get("symbol") != symbol.upper() or int(row.get("timeframe_seconds", 60)) != timeframe_seconds or row.get("outcome") != "PENDING":
                continue
            expiry, entry = row.get("suggested_expiry_minutes"), row.get("entry_price")
            if not expiry or entry is None or row.get("direction") not in ("CALL", "PUT"):
                row["outcome"], row["evaluated_at"] = "NOT_EVALUATED", latest_ts
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
            row["outcome"], row["outcome_price"], row["evaluated_at"] = outcome, latest_close, latest_ts
            changed += 1

        if changed and _engine is not None:
            with _engine.begin() as connection:
                for row in rows:
                    if row.get("symbol") == symbol.upper() and int(row.get("timeframe_seconds", 60)) == timeframe_seconds:
                        where = and_(_signal_table.c.symbol == row["symbol"], _signal_table.c.timeframe_seconds == timeframe_seconds, _signal_table.c.timestamp == int(row["timestamp"]))
                        connection.execute(update(_signal_table).where(where).values(outcome=row.get("outcome", "NOT_EVALUATED"), payload=json.dumps(row, separators=(",", ":"))))
        elif changed:
            _write_all(SIGNALS_FILE, rows)
    return changed


def read_jsonl(path: Path, limit: int = 200) -> list[dict]:
    with _lock:
        if _engine is not None:
            table = _candle_table if path == CANDLES_FILE else _signal_table
            return _db_rows(table)[-limit:]
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
