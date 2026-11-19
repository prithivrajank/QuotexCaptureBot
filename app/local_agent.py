"""Local Windows capture/recognition agent. Sends forming updates and closes candles on rollover.

This is still heuristic pixel recognition; confidence is a detector score, not a
statistical probability. The chart must remain visible and calibrated.
"""
import argparse
import json
import os
import time
from pathlib import Path
import cv2
import mss
import numpy as np
import requests
from app.vision.config import load_visual_config, load_calibration
from app.vision.detector import detect_candidates
from app.vision.reconstruct import reconstruct


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
    calibration = load_calibration()
    headers = {"X-Ingest-Token": token}
    pending = None
    last_payload_fingerprint = None
    with mss.mss() as sct:
        while True:
            now = int(time.time())
            slot = now - (now % args.timeframe)
            raw = np.asarray(sct.grab(region))
            frame = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)
            found = detect_candidates(frame)

            # On candle rollover, close the previous candle using its last observed OHLC.
            if pending is not None and slot > pending["timestamp"]:
                closed_payload = {**pending, "is_closed": True}
                try:
                    response = requests.post(args.api.rstrip("/") + "/api/ingest/candle", json=closed_payload, headers=headers, timeout=8)
                    print(f"Closed candle: {response.status_code} {response.text[:250]}")
                except requests.RequestException as exc:
                    print(f"Close ingest error: {exc}")
                pending = None
                last_payload_fingerprint = None

            if found:
                candidate = max(found, key=lambda item: item.x)
                payload = reconstruct(candidate, calibration, args.symbol, slot, args.timeframe)
                payload["is_closed"] = False
                # Avoid flooding the API with identical pixel readings.
                fingerprint = tuple(round(payload[k], 8) for k in ("open", "high", "low", "close")) + (round(payload["confidence"], 3),)
                pending = payload
                if fingerprint != last_payload_fingerprint:
                    try:
                        response = requests.post(args.api.rstrip("/") + "/api/ingest/candle", json=payload, headers=headers, timeout=8)
                        if response.ok:
                            last_payload_fingerprint = fingerprint
                            print(json.dumps(response.json()))
                        else:
                            print(f"Ingest rejected: {response.status_code} {response.text[:200]}")
                    except requests.RequestException as exc:
                        print(f"API connection error: {exc}")
            if args.once:
                break
            time.sleep(1.0 / max(0.2, min(args.fps, 5)))

    # On Ctrl+C the current candle intentionally remains forming, not falsely closed.


if __name__ == "__main__":
    main()
