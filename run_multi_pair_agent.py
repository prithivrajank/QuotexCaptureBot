"""Launch one read-only capture process for each calibrated chart profile."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from app.vision.config import validate_visual_config


def main():
    parser = argparse.ArgumentParser(description="Start one capture process per calibrated chart profile.")
    parser.add_argument("--profiles-dir", default="capture_profiles")
    args = parser.parse_args()

    profiles_dir = Path(args.profiles_dir)
    profiles = sorted(profiles_dir.glob("*.json"))
    if not profiles:
        raise SystemExit(f"No profile JSON files found in {profiles_dir.resolve()}")

    processes = []
    for profile in profiles:
        try:
            data = json.loads(profile.read_text(encoding="utf-8"))
            errors = validate_visual_config(data)
            if errors:
                raise ValueError("; ".join(errors))
            symbol = str(data["symbol"]).strip().upper()
            timeframe = int(data.get("timeframe_seconds", 60))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise SystemExit(f"Invalid profile {profile}: {exc}")

        command = [sys.executable, "-m", "app.local_agent", "--config", str(profile)]
        print(f"Starting {symbol} ({timeframe}s) using {profile}", flush=True)
        processes.append(subprocess.Popen(command))

    print(f"Started {len(processes)} chart capture process(es). Press Ctrl+C to stop all.", flush=True)
    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        print("Stopping capture processes...")
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
