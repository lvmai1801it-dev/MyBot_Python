"""Capture raw screenshots for redline YOLO labeling.

Saves the ORIGINAL ADB PNG bytes when available (ScreenshotArray.png_bytes),
which preserves the exact image the bot sees.

Usage:
  python tools/capture_redline_dataset.py --count 200 --interval 2

Output:
  datasets/redline/images/raw/2026-11-09_12-30-00_0001.png
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from COCbot.vision.capture import take_screenshot  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Capture CoC screenshots for redline labeling")
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between captures")
    parser.add_argument("--out", default=os.path.join(ROOT, "datasets", "redline", "images", "raw"))
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    saved = 0

    for i in range(args.count):
        try:
            img = take_screenshot(output_path="screen.png", max_retries=2, retry_delay=2.0)
        except Exception as e:
            print("capture failed:", e)
            time.sleep(args.interval)
            continue

        if img is None:
            print("capture returned None")
            time.sleep(args.interval)
            continue

        name = f"{stamp}_{i + 1:04d}.png"
        dst = os.path.join(args.out, name)
        try:
            data = getattr(img, "png_bytes", None)
            if data:
                with open(dst, "wb") as f:
                    f.write(data)
            else:
                import cv2
                ok, buf = cv2.imencode(".png", img)
                if not ok:
                    raise RuntimeError("cv2.imencode failed")
                buf.tofile(dst)
            saved += 1
            print(f"[{saved}/{args.count}] {dst}")
        except Exception as e:
            print("save failed:", e)

        time.sleep(args.interval)

    print(f"Done: {saved} images -> {args.out}")


if __name__ == "__main__":
    main()
