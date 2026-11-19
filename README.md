# QuotexCaptureBot

Read-only visual market-analysis project for Quotex Demo charts. The Windows capture agent reads only the selected screen rectangle and sends reconstructed candle estimates to the API. It never places orders or reads browser credentials/cookies.

## Current build

- Windows screen capture with manual price-axis and time-axis calibration.
- Multi-pair capture through independent per-chart JSON profiles and one read-only process per visible chart.
- Visual candle reconstruction with confidence filtering and forming/closed candle lifecycle.
- FastAPI service with protected candle-ingest endpoint.
- EMA 9/21/50, MACD, RSI 14, Bollinger Bands, ATR 14, trend strength and recent support/resistance calculations.
- CALL/PUT/WAIT signal engine with 1-minute or 2-minute suggested expiry rules.
- Duplicate candle/signal protection and historical outcome evaluation.
- PostgreSQL persistence when `DATABASE_URL` is configured; JSONL fallback otherwise.
- Live dashboard with candlestick chart, CALL/PUT markers, latest signals, performance summary, candle details, indicator snapshot and API health.
- Optional Telegram notifications for newly-created CALL/PUT signals; disabled unless both private Telegram environment variables are configured. WAIT signals are not sent.
- API documentation at `/docs`.

## Important data limitations

This is a prototype, not a validated Quotex chart reader. Candle body/wick detection is heuristic and can misread overlays, zoom levels, themes or unusual candle styles. Price and timestamp calibration are manual, using two anchors each; chart layout, zoom, timeframe or candle spacing changes can invalidate calibration. The reconstructed OHLC values are **visual estimates**, not an official or broker-authoritative feed.

Signal confidence is a rule-strength score, not a probability. Historical WIN/LOSS/DRAW labels compare estimated candle closes and do not model payout, spread, execution delay, slippage or broker settlement. They are not actual trading profit or a guarantee.

## Windows setup (Python 3.11)

```cmd
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python -m app.visual_capture --select
```

The capture setup stores the selected rectangle in `visual_config.json`. OHLC reconstruction requires two manually measured price-axis anchors under `calibration`, and timestamp reconstruction requires two candle-center x-axis anchors under `time_calibration`. Do not use placeholder values. See [VISUAL_RECOGNITION_ENGINE.md](VISUAL_RECOGNITION_ENGINE.md) for the exact format and limitations.

In a second CMD window:

```cmd
cd /d path\to\QuotexCaptureBot
.venv\Scripts\activate
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Dashboard: http://127.0.0.1:8000/ · API docs: http://127.0.0.1:8000/docs



## Quotex chart crop profile (screenshot reference)

For the supplied 1917 × 1078 desktop screenshot, the initial chart-only capture rectangle is:

```json
{
  "symbol": "USD/BRL_OTC",
  "timeframe_seconds": 60,
  "fps": 2,
  "region": {
    "left": 205,
    "top": 330,
    "width": 1340,
    "height": 645
  }
}
```

These coordinates are a starting crop for that screenshot's display layout, not universal coordinates. The screenshot shows a 1-minute chart. Recheck the rectangle if Windows display scaling, browser zoom, window size, taskbar, or Quotex layout changes. The crop intentionally excludes browser chrome, the left navigation, the right trade panel and the bottom time labels. After selecting the region, add the two manually measured price-axis anchors and two x-axis time anchors to the same profile before running capture. The supplied screenshot alone does not provide sufficiently precise calibration values for price/time reconstruction.

## Multi-pair capture (one profile per visible chart)

The bot does not turn one screenshot into several symbols. To monitor multiple pairs at once, open each pair in its own visible chart region (for example, separate chart windows) and create one independent profile per chart. Every profile needs its own screen region, two price-axis calibration anchors and two time-axis calibration anchors.

1. Create a JSON profile for each chart under `capture_profiles/` (for example, `capture_profiles/EURUSD_OTC.json`). Include `symbol`, optional `timeframe_seconds` (default 60), optional `fps` (default 2, maximum 5), `region`, `calibration` and `time_calibration`.
2. Select/preview each profile's region with `python -m app.visual_capture --config capture_profiles/EURUSD_OTC.json --select`. Repeat for each profile. Add that profile's own calibration anchors using the documented format; never copy another chart's pixel anchors.
3. Set `INGEST_TOKEN` in the terminal environment, then run `python run_multi_pair_agent.py`. The launcher starts one capture process per valid JSON profile and stops them together with Ctrl+C.

A profile's `region` is in absolute desktop-screen coordinates. Chart windows must remain in those positions and keep the same zoom, timeframe, candle spacing and theme used during calibration. Each profile must point to a different actual chart. Monitoring more pairs requires enough screen space to keep each chart visible; a single chart cannot provide simultaneous independent data for multiple symbols. Capture processes share the same `INGEST_TOKEN` and API URL, with optional per-profile `api` and `fps` settings.

## Optional Telegram notifications

Create a Telegram bot using the official BotFather account and obtain the destination chat ID. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` as private environment variables in Render. Do not put real values in `.env.example`, GitHub, screenshots or chat messages. The notifier sends only newly-created CALL/PUT signal summaries; it does not send WAIT alerts or place orders. If either variable is missing, notifications remain disabled. A notification failure does not stop candle ingestion.

## API endpoints

- `GET /api/health`
- `GET /api/candles?symbol=EURUSD_OTC&timeframe_seconds=60&closed_only=true`
- `GET /api/signals?symbol=EURUSD_OTC`
- `GET /api/indicators?symbol=EURUSD_OTC&timeframe_seconds=60`
- `GET /api/performance`
- `POST /api/ingest/candle` with `X-Ingest-Token`

## Render deployment and persistence

Set a long random `INGEST_TOKEN` privately in both the Windows agent environment and Render environment. For persistent history, set `DATABASE_URL` privately in Render to a PostgreSQL connection string (for example, Neon or Render PostgreSQL). The app creates its tables automatically. If `DATABASE_URL` is blank, it uses JSONL files, which are not durable on an ephemeral Render filesystem. Never commit database URLs, passwords or tokens.

The Windows capture agent must remain running on the computer displaying the Demo chart. Render hosts the API/dashboard; it cannot capture the user's local screen.

## Safety

- Demo-only development; no Buy/Sell automation.
- Never represent visual estimates as broker-authoritative OHLC.
- No guaranteed signals or guaranteed profit.
- Do not upload screenshots containing account details or share passwords, cookies, session IDs or tokens.

## Validation status

Features have been committed to the development branch. They have **not** been locally executed or runtime-validated yet, following the requested workflow. Complete the remaining build first; then perform controlled Demo validation and fix issues found before relying on the dashboard.
