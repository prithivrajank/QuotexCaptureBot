import secrets
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from app.config import INGEST_TOKEN
from app.models import VisualCandle, Signal
from app.storage import save_candle, save_signal, candles, signals
from app.strategy import make_signal

app = FastAPI(title="QuotexCaptureBot", version="0.1.0", description="Read-only visual chart analysis. Signals are experimental, not financial advice.")

@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "read_only", "source": "visual_estimates"}

@app.get("/api/candles")
def get_candles(limit: int = 200):
    return {"items": candles(max(1, min(limit, 1000)))}

@app.get("/api/signals")
def get_signals(limit: int = 100):
    return {"items": signals(max(1, min(limit, 500)))}

@app.post("/api/ingest/candle")
def ingest_candle(candle: VisualCandle, x_ingest_token: str = Header(default="")):
    if not INGEST_TOKEN or not secrets.compare_digest(x_ingest_token, INGEST_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid ingest token")
    if not candle.valid_ohlc():
        raise HTTPException(status_code=422, detail="Inconsistent OHLC values")
    if candle.confidence < 0.85:
        raise HTTPException(status_code=422, detail="Visual confidence below acceptance threshold")
    save_candle(candle)
    rows = candles(1000)
    same = [r for r in rows if r["symbol"] == candle.symbol and r["timeframe_seconds"] == candle.timeframe_seconds]
    result = make_signal(same)
    signal = Signal(symbol=candle.symbol, timestamp=candle.timestamp, **result)
    save_signal(signal)
    return {"accepted": True, "signal": signal.model_dump()}

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>QuotexCaptureBot</title><style>body{font:16px system-ui;background:#101827;color:#e5e7eb;margin:0;padding:28px}main{max-width:900px;margin:auto}.card{background:#1e293b;padding:18px;border-radius:12px;margin:14px 0}.muted{color:#94a3b8}a{color:#7dd3fc}</style></head><body><main><h1>QuotexCaptureBot</h1><p class='muted'>Read-only visual analysis · Demo testing only</p><div class='card'><h2>System status</h2><p id='health'>Loading…</p></div><div class='card'><h2>Latest signals</h2><pre id='signals'>Loading…</pre></div><div class='card'><h2>API</h2><a href='/docs'>Open API documentation</a></div></main><script>async function refresh(){try{let h=await fetch('/api/health');document.querySelector('#health').textContent=JSON.stringify(await h.json());let s=await fetch('/api/signals');document.querySelector('#signals').textContent=JSON.stringify(await s.json(),null,2)}catch(e){document.querySelector('#health').textContent='API unavailable'}}refresh();setInterval(refresh,5000)</script></body></html>"""
