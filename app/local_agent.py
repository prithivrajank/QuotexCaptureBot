"""Local Windows capture/recognition agent. Uses manual x-axis calibration for candle timestamps.

This remains heuristic pixel recognition; it does not read chart labels or broker data.
"""
import argparse
import json
import os
import time
from app.vision.config import load_visual_config, load_calibration, load_time_calibration
from app.vision.detector import detect_candidates
from app.vision.reconstruct import reconstruct
import cv2
import mss
import numpy as np
import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default=os.getenv("BOT_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--symbol", default="EURUSD_OTC")
    parser.add_argument("--timeframe", type=int, default=60)
    parser.add_argument("--fps", type=float, default=2)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.timeframe < 1 or args.fps <= 0:
        raise SystemExit("Timeframe and FPS must be positive.")
    token = os.getenv("INGEST_TOKEN", "")
    if not token:
        raise SystemExit("Set INGEST_TOKEN in this terminal before remote ingest.")
    cfg = load_visual_config()
    region = cfg["region"] if "region" in cfg else {k: cfg[k] for k in ("left", "top", "width", "height")}
    price_calibration = load_calibration()
    time_calibration = load_time_calibration()
    headers = {"X-Ingest-Token": token}
    sent_fingerprints = {}
    with mss.mss() as sct:
        while True:
            now = int(time.time())
            current_slot = now - (now % args.timeframe)
            raw = np.asarray(sct.grab(region))
            frame = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)
            found = detect_candidates(frame)
            seen_keys = set()

            for candidate in found:
                candle_ts = time_calibration.candle_timestamp_at(candidate.x, args.timeframe)
                # Do not ingest projected future candles or stale chart positions.
                if candle_ts > current_slot or candle_ts < current_slot - (500 * args.timeframe):
                    continue
                payload = reconstruct(candidate, price_calibration, args.symbol, candle_ts, args.timeframe)
                payload["is_closed"] = candle_ts < current_slot
                key = (payload["symbol"], candle_ts)
                seen_keys.add(key)
                fingerprint = tuple(round(payload[k], 8) for k in ("open", "high", "low", "close")) + (round(payload["confidence"], 3), payload["is_closed"])
                if sent_fingerprints.get(key) == fingerprint:
                    continue
                try:
                    response = requests.post(args.api.rstrip("/") + "/api/ingest/candle", json=payload, headers=headers, timeout=8)
                    if response.ok:
                        sent_fingerprints[key] = fingerprint
                        print(json.dumps({"timestamp": candle_ts, "closed": payload["is_closed"], "result": response.json()}))
                    else:
                        print(f"Ingest rejected: {response.status_code} {response.text[:200]}")
                except requests.RequestException as exc:
                    print(f"API connection error: {exc}")

            # Keep memory bounded; recent 500 candle slots are enough for this local agent.
            cutoff = current_slot - (500 * args.timeframe)
            sent_fingerprints = {key: value for key, value in sent_fingerprints.items() if key[1] >= cutoff}
            if args.once:
                break
            time.sleep(1.0 / max(0.2, min(args.fps, 5)))


if __name__ == "__main__":
    main()
