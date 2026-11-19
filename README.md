# QuotexCaptureBot

Read-only visual market-analysis project for Quotex Demo charts. The Windows capture process reads only the selected screen rectangle. The API can run locally or on Render. It never places orders or reads browser credentials/cookies.

## Current development status

The branch now includes a first-pass live candle update pipeline and signal-history deduplication:
- The local agent repeatedly updates the current forming candle.
- When the timeframe rolls over, it submits the last observed candle as closed.
- The API upserts candle records by symbol, timeframe and candle timestamp, so repeated forming updates do not create duplicate rows.
- Signals are evaluated only when a candle first transitions to closed; duplicate close submissions do not create duplicate signal-history entries.
- Dashboard refreshes recent candles and signals.

This is still a prototype, not a validated Quotex chart reader. Candle body/wick detection remains heuristic and can misread chart overlays, zoom levels, themes or unusual candle styles. The confidence score is a heuristic filter, not a probability. The agent currently assigns the current time slot to the rightmost detected candle; it does not yet derive timestamps from chart-axis labels or reconstruct a full historical candle series. A missed final capture can therefore leave the last candle incomplete.

## Windows setup (Python 3.11)

```cmd
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python -m app.visual_capture --select
```

The capture setup stores the selected rectangle in `visual_config.json` and preserves a calibration object if one already exists. OHLC reconstruction still requires two manually measured price-axis anchors under `calibration`; do not use placeholder values. See `VISUAL_RECOGNITION_ENGINE.md` for calibration format and limitations.

In a second CMD window, run the API:

```cmd
cd /d path\to\QuotexCaptureBot
.venv\Scripts\activate
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Dashboard: http://127.0.0.1:8000/ · API docs: http://127.0.0.1:8000/docs

## Remote ingest

Set the same long random `INGEST_TOKEN` privately in the local environment and Render environment. Never commit real tokens. The agent sends `is_closed=false` updates while a candle forms and sends the last observed OHLC with `is_closed=true` after timeframe rollover. API endpoints:
- `GET /api/candles?symbol=EURUSD_OTC&timeframe_seconds=60&closed_only=true`
- `GET /api/signals?symbol=EURUSD_OTC`
- `POST /api/ingest/candle` with `X-Ingest-Token`

JSONL storage is single-process prototype storage. Render free filesystem is ephemeral and does not provide durable history across restarts/redeploys; move to a persistent database before relying on long-term history.

## Safety and limitations

- Demo-only development. No Buy/Sell automation.
- Screen pixels are approximate and require chart calibration. Never represent visual estimates as broker-authoritative OHLC.
- Signals are experimental, not guaranteed or financial advice.
- Do not upload screenshots containing account details. Do not share passwords, cookies, session IDs, or tokens.
- Local screen capture runs on the user's Windows PC, not on Render.
