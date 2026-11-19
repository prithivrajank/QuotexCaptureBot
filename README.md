# QuotexCaptureBot

Read-only visual market-analysis project for Quotex Demo charts. The Windows capture process reads only the selected screen rectangle. The API can run locally or on Render. It never places orders or reads browser credentials/cookies.

## Status
This repository contains the initial end-to-end scaffold: local chart preview, API, JSONL storage, indicator calculations, conservative signal filter, dashboard, and Render configuration. **Visual candle extraction/OHLC reconstruction is not yet complete.** Until that module is implemented and validated, the signal engine should be treated as experimental and will return WAIT when it has insufficient data.

## Windows setup (Python 3.11)

```cmd
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python -m app.visual_capture --select
```

In a second CMD window, run the API:

```cmd
cd /d path\to\QuotexCaptureBot
.venv\Scripts\activate
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Dashboard: http://127.0.0.1:8000/ · API docs: http://127.0.0.1:8000/docs

## Remote ingest

Set a long random `INGEST_TOKEN` in local environment and Render environment. Never commit real tokens. POST validated `VisualCandle` JSON to `/api/ingest/candle` with header `X-Ingest-Token`. Confidence below 0.85 is rejected. Render free filesystem is ephemeral; use a persistent database before relying on long-term history.

## Safety and limitations

- Demo-only development. No Buy/Sell automation.
- Screen pixels are approximate and require chart calibration. Never represent visual estimates as broker-authoritative OHLC.
- Signals are experimental, not guaranteed or financial advice.
- Do not upload screenshots containing account details. Do not share passwords, cookies, session IDs, or tokens.
- Local screen capture runs on the user's Windows PC, not on Render.
