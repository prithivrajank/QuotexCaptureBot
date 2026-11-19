"""Read-only local screen-region preview and selection, per chart profile."""
import argparse
import json
from pathlib import Path

import cv2
import mss
import numpy as np


def select_region(frame):
    title = "Select chart only; ENTER confirms, ESC cancels"
    x, y, w, h = cv2.selectROI(title, frame, True, False)
    cv2.destroyWindow(title)
    if w < 100 or h < 100:
        return None
    return {"left": int(x), "top": int(y), "width": int(w), "height": int(h)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="visual_config.json", help="Profile JSON to edit/preview")
    parser.add_argument("--select", action="store_true")
    parser.add_argument("--fps", type=float, default=5)
    args = parser.parse_args()
    if not 0 < args.fps <= 15:
        raise SystemExit("FPS must be between 0 and 15")

    config_path = Path(args.config)
    with mss.mss() as sct:
        mon = sct.monitors[1]
        shot = np.asarray(sct.grab(mon))
        frame = cv2.cvtColor(shot, cv2.COLOR_BGRA2BGR)
        config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
        region = None if args.select else config.get("region")
        if region is None and all(k in config for k in ("left", "top", "width", "height")):
            region = {k: config[k] for k in ("left", "top", "width", "height")}
        if region is None:
            region = select_region(frame)
            if region is None:
                print("Selection cancelled")
                return
            config["region"] = region
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

        x, y, w, h = (int(region[k]) for k in ("left", "top", "width", "height"))
        if x < 0 or y < 0 or w < 100 or h < 100 or x + w > mon["width"] or y + h > mon["height"]:
            raise SystemExit("Saved region is outside the screen. Run with --select.")
        print(f"Read-only preview for {config_path}. Q/Esc quit; R reselect; P pause.")
        paused = False
        while True:
            if not paused:
                shot = np.asarray(sct.grab(mon))
                frame = cv2.cvtColor(shot, cv2.COLOR_BGRA2BGR)
                cv2.imshow("Quotex chart region - read only", frame[y:y+h, x:x+w])
            key = cv2.waitKey(max(1, int(1000 / args.fps))) & 0xff
            if key in (ord("q"), 27):
                break
            if key == ord("p"):
                paused = not paused
            if key == ord("r"):
                shot = np.asarray(sct.grab(mon))
                frame = cv2.cvtColor(shot, cv2.COLOR_BGRA2BGR)
                new_region = select_region(frame)
                if new_region:
                    config["region"] = new_region
                    config_path.parent.mkdir(parents=True, exist_ok=True)
                    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
                    x, y, w, h = (new_region[k] for k in ("left", "top", "width", "height"))
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
