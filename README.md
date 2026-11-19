# QuotexCaptureBot

Read-only visual market-analysis project for Quotex Demo charts. The Windows capture process reads only the selected screen rectangle. The API can run locally or on Render. It never places orders or reads browser credentials/cookies.

## Current development status

The branch now includes a first-pass live candle update pipeline and signal-history deduplication:
- The local agent repeatedly updates the current forming candle.
- When the timeframe rolls over, it submits the last observed candle as closed.
- The API upserts candle records by symbol, timeframe and candle timestamp, so repeated forming updates do not create duplicate rows.
- Signals are evaluated only when a candle first transitions to closed; duplicate close submissions do not create duplicate signal-history entries.
- Dashboard refreshes recent candles, signals and historical outcome statistics.\n- CALL/PUT signals record the closed candle close as the estimated entry price and remain PENDING until a later closed candle reaches the configured expiry timestamp. The evaluator labels WIN/LOSS/DRAW by comparing that later close with the entry price; WAIT signals are not evaluated.\n- `GET /api/performance` returns counts and a historical win rate based only on evaluated CALL/PUT signals.

This is still a prototype, not a validated Quotex chart reader. Candle body/wick detection remains heuristic and can misread chart overlays, zoom levels, themes or unusual candle styles. The confidence score is a heuristic filter, not a probability. The agent now maps detected candle x-centers to timestamps using two manually supplied x-axis time anchors and can submit multiple visible candles. This is linear pixel-to-time calibration, not automatic OCR; irregular spacing, hidden candles, or chart layout changes can invalidate it. Compare reconstructed candles with the visible Demo chart before relying on the history.

## Windows setup (Python 3.11)

```cmd
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python -m app.visual_capture --select
```

The capture setup stores the selected rectangle in `visual_config.json` and preserves a calibration object if one already exists. OHLC reconstruction requires two manually measured price-axis anchors under `calibration`, and timestamp reconstruction requires two candle-center x-axis anchors under `time_calibration`; do not use placeholder values. See `VISUAL_RECOGNITION_ENGINE.md` for the exact format and limitations.

In a second CMD window, run the API:

```cmd
cd /d path\to\QuotexCaptureBot
.venv\Scripts\activate
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Dashboard: http://127.0.0.1:8000/ · API docs: http://127.0.0.1:8000/docs

## Remote ingest

Set the same long random `INGEST_TOKEN` privately in the local environment and Render environment. For persistent history, also set `DATABASE_URL` to a PostgreSQL database connection string (for example, a Neon or Render PostgreSQL database). Never commit real tokens. The agent sends `is_closed=false` updates while a candle forms and sends the last observed OHLC with `is_closed=true` after timeframe rollover. API endpoints:
- `GET /api/candles?symbol=EURUSD_OTC&timeframe_seconds=60&closed_only=true`
- `GET /api/signals?symbol=EURUSD_OTC`
- `POST /api/ingest/candle` with `X-Ingest-Token`

Outcome evaluation uses candle-close comparison and does not model payout, spread, execution delay, slippage or broker settlement. It is a rough historical label, not a real-money result.\n\nStorage now supports PostgreSQL (recommended for Render) or JSONL fallback. Set the private `DATABASE_URL` environment variable in Render to a PostgreSQL connection string; the app creates its tables automatically. If `DATABASE_URL` is blank, it uses local JSONL files. Never commit a database URL or password. The PostgreSQL schema uses unique keys for each symbol/timeframe/timestamp. This code has been pushed but not locally executed per the current development preference.

## Safety and limitations

- Demo-only development. No Buy/Sell automation.
- Screen pixels are approximate and require chart calibration. Never represent visual estimates as broker-authoritative OHLC.
- Signals are experimental, not guaranteed or financial advice.
- Do not upload screenshots containing account details. Do not share passwords, cookies, session IDs, or tokens.
- Local screen capture runs on the user's Windows PC, not on Render.
