"""Local Windows capture/recognition agent for one independently calibrated chart profile.

Run one process per visible chart. This agent reads pixels only and never accesses
browser storage, credentials, cookies, or broker APIs.
"""
import argparse
import json
import os
import time
from pathlib import Path

from app.vision.config import load_visual_config, load_calibration, load_time_calibration, validate_visual_config
from app.vision.detector import detect_candidates
from app.vision.reconstruct import reconstruct, validate_candidate
from app.vision.sequence import deduplicate_candles
import cv2
import mss
import numpy as np
import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default=None, help="Override the API URL in the profile")
    parser.add_argument("--config", default="visual_config.json", help="Path to this chart's independent JSON profile")
    parser.add_argument("--symbol", default=None, help="Override the profile symbol")
    parser.add_argument("--timeframe", type=int, default=None, help="Override timeframe in seconds")
    parser.add_argument("--fps", type=float, default=None, help="Override capture FPS")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    config_path = Path(args.config)
    cfg = load_visual_config(config_path)
    profile_errors = validate_visual_config(cfg)
    if profile_errors:
        raise SystemExit("Invalid chart profile: " + "; ".join(profile_errors))
    api = (args.api or cfg.get("api") or os.getenv("BOT_API_URL") or "http://127.0.0.1:8000").rstrip("/")
    symbol = (args.symbol or cfg.get("symbol") or "EURUSD_OTC").strip().upper()
    timeframe = int(args.timeframe or cfg.get("timeframe_seconds", 60))
    fps = float(args.fps or cfg.get("fps", 2))
    if timeframe < 1 or not 0 < fps <= 5:
        raise SystemExit("Timeframe must be positive and FPS must be greater than 0 and at most 5.")

    token = os.getenv("INGEST_TOKEN", "")
    if not token:
        raise SystemExit("Set INGEST_TOKEN in this terminal before remote ingest.")

    region = cfg["region"] if "region" in cfg else {k: cfg[k] for k in ("left", "top", "width", "height")}
    price_calibration = load_calibration(config_path)
    time_calibration = load_time_calibration(config_path)
    headers = {"X-Ingest-Token": token}
    sent_fingerprints = {}
    last_diagnostics_fingerprint = None
    last_diagnostics_success_monotonic = 0.0

    print(json.dumps({"status": "started", "symbol": symbol, "timeframe_seconds": timeframe, "config": str(config_path), "api": api}))
    with mss.mss() as sct:
        while True:
            now = int(time.time())
            current_slot = now - (now % timeframe)
            raw = np.asarray(sct.grab(region))
            frame = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)
            found = detect_candidates(frame)
            found, sequence_info = deduplicate_candles(found, time_calibration, timeframe)
            latest_candidate_timestamp = max((time_calibration.candle_timestamp_at(item.x, timeframe) for item in found), default=None)
            drift_seconds = current_slot - latest_candidate_timestamp if latest_candidate_timestamp is not None else None
            if drift_seconds is None:
                alignment_status = "NO_CANDLES"
            elif drift_seconds < -timeframe:
                alignment_status = "AHEAD"
            elif drift_seconds > max(120, timeframe * 2):
                alignment_status = "LAGGING"
            else:
                alignment_status = "ALIGNED"
            diagnostic_payload = {
                "symbol": symbol, "timeframe_seconds": timeframe, "reported_at": now,
                "candidate_count": sequence_info["candidate_count"],
                "unique_slots": sequence_info["unique_slots"],
                "duplicate_count": len(sequence_info["duplicate_timestamps"]),
                "missing_timestamps": sequence_info["missing_timestamps"],
                "missing_slot_count": sequence_info["missing_slot_count"],
                "gap_count": sequence_info["gap_count"],
                "largest_gap_slots": sequence_info["largest_gap_slots"],
                "calibration_structurally_valid": True,
                "latest_candidate_timestamp": latest_candidate_timestamp,
                "expected_current_slot": current_slot,
                "timestamp_drift_seconds": drift_seconds,
                "timestamp_alignment_status": alignment_status,
                "source": "visual_estimate",
            }
            diagnostic_fingerprint = (
                diagnostic_payload["candidate_count"], diagnostic_payload["unique_slots"],
                diagnostic_payload["duplicate_count"], tuple(diagnostic_payload["missing_timestamps"]), diagnostic_payload["missing_slot_count"],
                diagnostic_payload["gap_count"], diagnostic_payload["largest_gap_slots"],
                diagnostic_payload["latest_candidate_timestamp"], diagnostic_payload["expected_current_slot"],
                diagnostic_payload["timestamp_drift_seconds"], diagnostic_payload["timestamp_alignment_status"]
            )
            if diagnostic_fingerprint != last_diagnostics_fingerprint or time.monotonic() - last_diagnostics_success_monotonic >= 30:
                try:
                    diag_response = requests.post(api + "/api/ingest/diagnostics", json=diagnostic_payload, headers=headers, timeout=8)
                    if diag_response.ok:
                        last_diagnostics_fingerprint = diagnostic_fingerprint
                        last_diagnostics_success_monotonic = time.monotonic()
                    else:
                        print(f"Diagnostics rejected for {symbol}: {diag_response.status_code} {diag_response.text[:160]}")
                except requests.RequestException as exc:
                    print(f"Diagnostics API error for {symbol}: {exc}")
            if sequence_info["duplicate_timestamps"] or sequence_info["missing_timestamps"]:
                print(json.dumps({"event": "candle_sequence_warning", "symbol": symbol, **sequence_info}))

            for candidate in found:
                candle_ts = time_calibration.candle_timestamp_at(candidate.x, timeframe)
                if candle_ts > current_slot or candle_ts < current_slot - (500 * timeframe):
                    continue
                try:
                    validate_candidate(candidate)
                    payload = reconstruct(candidate, price_calibration, symbol, candle_ts, timeframe)
                except (ValueError, OverflowError) as exc:
                    print(json.dumps({
                        "event": "candle_candidate_rejected",
                        "symbol": symbol,
                        "timestamp": candle_ts,
                        "reason": str(exc),
                        "confidence": candidate.confidence,
                    }))
                    continue
                payload["is_closed"] = candle_ts < current_slot
                key = (symbol, timeframe, candle_ts)
                fingerprint = tuple(round(payload[k], 8) for k in ("open", "high", "low", "close")) + (round(payload["confidence"], 3), payload["is_closed"])
                if sent_fingerprints.get(key) == fingerprint:
                    continue
                try:
                    response = requests.post(api + "/api/ingest/candle", json=payload, headers=headers, timeout=8)
                    if response.ok:
                        sent_fingerprints[key] = fingerprint
                        print(json.dumps({"symbol": symbol, "timeframe_seconds": timeframe, "timestamp": candle_ts, "closed": payload["is_closed"], "result": response.json()}))
                    else:
                        print(f"Ingest rejected for {symbol}: {response.status_code} {response.text[:200]}")
                except requests.RequestException as exc:
                    print(f"API connection error for {symbol}: {exc}")

            cutoff = current_slot - (500 * timeframe)
            sent_fingerprints = {key: value for key, value in sent_fingerprints.items() if key[2] >= cutoff}
            if args.once:
                break
            time.sleep(1.0 / fps)


if __name__ == "__main__":
    main()
