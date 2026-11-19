"""Local Windows capture/recognition agent. Sends estimates to the remote API."""
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
    token = os.getenv("INGEST_TOKEN", "")
    if not token:
        raise SystemExit("Set INGEST_TOKEN in this terminal before remote ingest.")
    cfg = load_visual_config()
    region = cfg["region"] if "region" in cfg else {k: cfg[k] for k in ("left","top","width","height")}
    calibration = load_calibration()
    last_sent = {}
    headers = {"X-Ingest-Token": token}
    with mss.mss() as sct:
        while True:
            raw = np.asarray(sct.grab(region))
            frame = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)
            found = detect_candidates(frame)
            now = int(time.time())
            # Only the rightmost candidate is treated as the forming candle.
            # Historical x-axis timestamps are not inferred in this version.
            if found:
                candidate = max(found, key=lambda item: item.x)
                slot = now - (now % args.timeframe)
                key = (args.symbol.upper(), slot)
                if key not in last_sent:
                    payload = reconstruct(candidate, calibration, args.symbol, slot, args.timeframe)
                    try:
                        response = requests.post(args.api.rstrip("/") + "/api/ingest/candle", json=payload, headers=headers, timeout=8)
                        if response.ok:
                            last_sent[key] = now
                            print(json.dumps(response.json()))
                        else:
                            print(f"Ingest rejected: {response.status_code} {response.text[:200]}")
                    except requests.RequestException as exc:
                        print(f"API connection error: {exc}")
            if args.once:
                break
            time.sleep(1.0 / max(0.2, min(args.fps, 5)))

if __name__ == "__main__":
    main()
