"""Draw and verify the resource/builder OCR regions.

Usage:
    python tools/calibrate_ocr_regions.py                  # live MEmu capture
    python tools/calibrate_ocr_regions.py --image artifacts/regions.png
    python tools/calibrate_ocr_regions.py --set gold 639 14 216 33

The annotated image is written to ``artifacts/ocr_regions_calibration.png`` so
the boxes can be checked against the HUD before saving them in settings.json:

    "ocr_regions": {
        "gold": [639, 14, 216, 33],
        "elixir": [641, 49, 210, 35],
        "dark": [693, 87, 160, 35],
        "gems": [692, 123, 160, 37],
        "builders": [740, 596, 64, 40]
    }
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from COCbot.core.config import load_config
from COCbot.core.config.paths import get_project_paths
from COCbot.core.vision import CaptureConfig, ScreenCapture
from COCbot.core.adb import AdbClient
from COCbot.features.village.resources import (
    HOME_BUILDERS_REGION,
    HOME_DARK_REGION,
    HOME_ELIXIR_REGION,
    HOME_GEMS_REGION,
    HOME_GOLD_REGION,
    regions_from_config,
)


def main() -> int:
    """Render the current OCR regions over a screenshot."""
    parser = argparse.ArgumentParser(description="OCR region calibration")
    parser.add_argument("--image", default="", help="Screenshot to annotate")
    parser.add_argument(
        "--set",
        nargs=5,
        metavar=("KEY", "X", "Y", "W", "H"),
        help="Override one region (KEY x y w h)",
    )
    args = parser.parse_args()

    regions = {
        "gold": HOME_GOLD_REGION,
        "elixir": HOME_ELIXIR_REGION,
        "dark": HOME_DARK_REGION,
        "gems": HOME_GEMS_REGION,
        "builders": HOME_BUILDERS_REGION,
    }
    config = load_config()
    regions.update(regions_from_config(config.vision.ocr_regions))
    if args.set:
        key = args.set[0]
        if key in regions:
            x, y, w, h = (int(value) for value in args.set[1:])
            regions[key] = regions[key].__class__(x, y, w, h)

    if args.image:
        image = cv2.imread(args.image)
    else:
        adb = AdbClient(host=config.emulator.host)
        cap = ScreenCapture(adb, CaptureConfig(max_retries=1, retry_delay=0))
        frame = cap.capture()
        image = frame.image if frame is not None else None
    if image is None:
        print("Could not read a screenshot")
        return 1

    annotated = image.copy()
    for name, region in regions.items():
        cv2.rectangle(
            annotated,
            (region.x, region.y),
            (region.right, region.bottom),
            (0, 255, 0),
            1,
        )
        cv2.putText(
            annotated,
            f"{name} {region.x},{region.y},{region.width},{region.height}",
            (region.x, max(12, region.y - 3)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.35,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )
        print(
            f"{name:8} [{region.x}, {region.y}, {region.width}, {region.height}]"
        )

    output = get_project_paths().src_dir / "artifacts" / "ocr_regions_calibration.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), annotated)
    print(f"saved {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
