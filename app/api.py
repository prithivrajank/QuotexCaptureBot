import secrets
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse
from app.config import INGEST_TOKEN
from app.models import VisualCandle, Signal
from app.storage import upsert_candle, save_signal, candles, signals, evaluate_pending_signals, storage_backend
from app.strategy import make_signal

app = FastAPI(title="QuotexCaptureBot", version="0.3.0", description="Read-only visual chart analysis. Signals are experimental, not financial advice.")


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "read_only", "source": "visual_estimates", "pipeline": "candle_lifecycle_signal_outcomes", "storage": storage_backend()}


@app.get("/api/candles")
def get_candles(limit: int = 200, symbol: str | None = None, timeframe_seconds: int | None = Query(default=None, ge=1, le=3600), closed_only: bool = False):
    return {"items": candles(max(1, min(limit, 1000)), symbol, timeframe_seconds, closed_only)}


@app.get("/api/signals")
def get_signals(limit: int = 100, symbol: str | None = None, outcome: str | None = None):
    return {"items": signals(max(1, min(limit, 500)), symbol, outcome)}


@app.get("/api/performance")
def performance(symbol: str | None = None):
    rows = signals(10000, symbol)
    evaluated = [row for row in rows if row.get("outcome") in ("WIN", "LOSS", "DRAW")]
    wins = sum(row["outcome"] == "WIN" for row in evaluated)
    losses = sum(row["outcome"] == "LOSS" for row in evaluated)
    draws = sum(row["outcome"] == "DRAW" for row in evaluated)
    decisive = wins + losses
    return {"evaluated": len(evaluated), "pending": sum(row.get("outcome") == "PENDING" for row in rows), "wins": wins, "losses": losses, "draws": draws, "win_rate_percent": round(wins / decisive * 100, 2) if decisive else None, "note": "Historical visual estimates only; not a prediction or guarantee."}


@app.post("/api/ingest/candle")
def ingest_candle(candle: VisualCandle, x_ingest_token: str = Header(default="")):
    if not INGEST_TOKEN or not secrets.compare_digest(x_ingest_token, INGEST_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid ingest token")
    if not candle.valid_ohlc():
        raise HTTPException(status_code=422, detail="Inconsistent or non-finite OHLC values")
    if candle.confidence < 0.85:
        raise HTTPException(status_code=422, detail="Visual confidence below acceptance threshold")

    newly_closed = upsert_candle(candle)
    if not candle.is_closed:
        return {"accepted": True, "candle_state": "forming", "signal": None}

    if not newly_closed:
        return {"accepted": True, "candle_state": "already_closed", "signal": None}

    completed = candles(1000, candle.symbol, candle.timeframe_seconds, closed_only=True)
    result = make_signal(completed)
    direction = result["direction"]
    expiry = result["suggested_expiry_minutes"]
    signal = Signal(
        symbol=candle.symbol,
        timeframe_seconds=candle.timeframe_seconds,
        timestamp=candle.timestamp,
        entry_price=candle.close,
        outcome="PENDING" if direction in ("CALL", "PUT") and expiry else "NOT_EVALUATED",
        **result
    )
    created = save_signal(signal)
    evaluated = evaluate_pending_signals(candle.symbol, candle.timeframe_seconds, completed)
    return {"accepted": True, "candle_state": "closed", "signal_created": created, "outcomes_updated": evaluated, "signal": signal.model_dump() if created else None}


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>QuotexCaptureBot</title><style>body{font:16px system-ui;background:#101827;color:#e5e7eb;margin:0;padding:28px}main{max-width:900px;margin:auto}.card{background:#1e293b;padding:18px;border-radius:12px;margin:14px 0}.muted{color:#94a3b8}a{color:#7dd3fc}</style></head><body><main><h1>QuotexCaptureBot</h1><p class='muted'>Read-only visual analysis · Demo testing only</p><div class='card'><h2>System status</h2><p id='health'>Loading…</p></div><div class='card'><h2>Performance (historical)</h2><pre id='performance'>Loading…</pre></div><div class='card'><h2>Latest signals</h2><pre id='signals'>Loading…</pre></div><div class='card'><h2>Recent candles</h2><pre id='candles'>Loading…</pre></div><div class='card'><h2>API</h2><a href='/docs'>Open API documentation</a></div></main><script>async function refresh(){try{let h=await fetch('/api/health');document.querySelector('#health').textContent=JSON.stringify(await h.json());let p=await fetch('/api/performance');document.querySelector('#performance').textContent=JSON.stringify(await p.json(),null,2);let s=await fetch('/api/signals?limit=20');document.querySelector('#signals').textContent=JSON.stringify(await s.json(),null,2);let c=await fetch('/api/candles?limit=20');document.querySelector('#candles').textContent=JSON.stringify(await c.json(),null,2)}catch(e){document.querySelector('#health').textContent='API unavailable'}}refresh();setInterval(refresh,5000)</script></body></html>"""
