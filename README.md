# QuotexCaptureBot

Read-only visual market-analysis platform for Quotex Demo charts. Local Windows capture processes chart pixels; the FastAPI service can run locally or on Render. No order placement, browser credential access, cookie extraction, or trading automation.

## Architecture

- Local capture: MSS + OpenCV; user selects a chart rectangle.
- Visual processing: candle colour/body/wick candidates with confidence and calibration status.
- Candle store: timestamped OHLC estimates are explicitly marked visual estimates.
- Indicators: EMA, RSI, MACD, Bollinger Bands.
- Strategies: trend and mean-reversion candidate rules; conflict/low-quality -> WAIT.
- API/dashboard: FastAPI endpoints for health, candles, signals and local ingest.
- Evaluation: signal outcomes are recorded separately; no profitability guarantee.

## Windows quick start (Python 3.11)

```cmd
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m app.visual_capture --select
```

In another CMD window:

```cmd
cd /d path\to\QuotexCaptureBot
.venv\Scripts\activate
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Open http://127.0.0.1:8000/docs for API docs and http://127.0.0.1:8000/ for dashboard status.

## Render

Deploy the API service with start command `uvicorn main:app --host 0.0.0.0 --port $PORT`. The local desktop capture agent does not run on Render. Configure `INGEST_TOKEN` as a strong random secret in Render and locally before enabling remote ingest. Never commit secrets.

## Visual data limitations

Screen pixels are not authoritative OHLC. Price-axis calibration, chart scaling, candle spacing, overlays, and UI changes can make estimates inaccurate. This project labels them as visual estimates and should emit WAIT when calibration/confidence is inadequate. Validate against Demo charts before using signals for decisions.

## Safety

Demo-only development. Read-only analysis. No automatic Buy/Sell, no browser debugging protocol, no session or credential collection. Do not upload account screenshots containing personal information.
