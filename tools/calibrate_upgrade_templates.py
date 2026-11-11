"""Report hero/defense upgrade template match scores.

Usage:
    python tools/calibrate_upgrade_templates.py --image artifacts/hero_detail.png
    python tools/calibrate_upgrade_templates.py --image artifacts/panel2.png --rows
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from COCbot.core.config.paths import get_project_paths
from COCbot.features.village.upgrades import (
    DEFAULT_BUTTONS,
    DEFAULT_TARGETS,
    _ocr_rows,
)
from COCbot.models.frame import Frame


def main() -> int:
    """Print the best score for every configured upgrade template."""
    parser = argparse.ArgumentParser(description="Upgrade template calibration")
    parser.add_argument("--image", required=True, help="Screenshot path")
    parser.add_argument(
        "--dir",
        default="",
        help="Template dir (default Templates/upgrade)",
    )
    parser.add_argument(
        "--rows",
        action="store_true",
        help="Also OCR the Buildings & Heroes rows in the image",
    )
    args = parser.parse_args()

    image = cv2.imread(args.image)
    if image is None:
        print(f"Cannot read {args.image}")
        return 1
    directory = (
        Path(args.dir) if args.dir else get_project_paths().templates_dir / "upgrade"
    )
    print(f"template_dir={directory}")

    names = [target.template for target in DEFAULT_TARGETS] + list(DEFAULT_BUTTONS.values())
    for name in names:
        path = directory / name
        if not path.is_file():
            print(f"MISSING  {name}")
            continue
        template = cv2.imread(str(path))
        if template is None:
            print(f"UNREADABLE {name}")
            continue
        if template.shape[0] > image.shape[0] or template.shape[1] > image.shape[1]:
            print(f"TOO LARGE {name}")
            continue
        result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        _, score, _, _ = cv2.minMaxLoc(result)
        print(f"{score:0.3f}  {name}")

    if args.rows:
        frame = Frame(image=image, width=image.shape[1], height=image.shape[0])
        rows = _ocr_rows(frame)
        print(f"rows={len(rows)}")
        for row in rows:
            print(f"  ({row.point.x},{row.point.y})  {row.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
