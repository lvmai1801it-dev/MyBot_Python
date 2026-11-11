"""Wall template calibration helper.

Usage:
    python tools/calibrate_wall_templates.py --image artifacts/coc_zoomed.png --level 17

Prints the best OpenCV match scores for the generic wall templates and the
per-level templates under ``walls/<level>/``. The output is meant to choose a
threshold and to identify templates that no longer match the current game art.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from COCbot.core.config.coordinates import HR_WALL_ROI
from COCbot.core.config.paths import get_project_paths


def _score(roi, template) -> float:
    """Return the best normalized match score for *template* inside *roi*."""
    if template is None or template.size == 0:
        return 0.0
    if template.shape[0] > roi.shape[0] or template.shape[1] > roi.shape[1]:
        return 0.0
    result = cv2.matchTemplate(roi, template, cv2.TM_CCOEFF_NORMED)
    _, score, _, _ = cv2.minMaxLoc(result)
    return float(score)


def main() -> int:
    """Run the calibration report."""
    parser = argparse.ArgumentParser(description="Wall template calibration")
    parser.add_argument("--image", required=True, help="Screenshot path")
    parser.add_argument("--level", type=int, default=8, help="Wall template level dir")
    args = parser.parse_args()

    image = cv2.imread(args.image)
    if image is None:
        print(f"Cannot read {args.image}")
        return 1
    x, y, w, h = HR_WALL_ROI.x, HR_WALL_ROI.y, HR_WALL_ROI.width, HR_WALL_ROI.height
    roi = image[y : y + h, x : x + w]
    if roi.size == 0:
        print("Empty wall ROI")
        return 1

    paths = get_project_paths()
    generic = [paths.templates_dir / name for name in ("wall.png", "wall_2.png", "wall_3.png", "wall_4.png")]
    level_dir = paths.src_dir / "walls" / str(args.level)
    level_templates = sorted(level_dir.glob("*.png")) if level_dir.is_dir() else []
    print(f"ROI={w}x{h}  level={args.level}  level_dir={level_dir}")

    rows = []
    for path in generic + level_templates:
        template = cv2.imread(str(path))
        rows.append((_score(roi, template), str(path.relative_to(paths.src_dir))))
    rows.sort(reverse=True)
    for score, name in rows[:20]:
        print(f"{score:0.3f}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
