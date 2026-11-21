"""Pseudo-label redline screenshots into YOLO-seg ``base_area`` polygons.

Two label sources (--source):

- ``buildings`` (default, for SCOUT captures): the scout view has no red
  no-deploy line, so the base area is approximated from a public CoC
  building detector (keremberke/yolov5m-clash-of-clans on HuggingFace):
  union of the detected building boxes, dilated by ``--margin-px`` (~2 map
  tiles = the redline offset beyond buildings), then the largest contour.
- ``red`` (for ATTACK-phase captures): trace the red no-deploy line with the
  same red-pixel rule as ``COCbot.core.vision.redline`` and keep its largest
  closed contour. Works only when the red line is visible (deploy phase).

Both write ``0 x y x y ...`` polygon labels to ``datasets/redline/labels/raw``
plus overlay previews and a QC report under ``runs/redline/pseudo_preview``.
The labels are machine-generated: review the previews and spot-fix them in a
labeling tool before training (docs/LABELING-GUIDE.md).

Dependencies:
- ``red``: any Python with opencv-python + numpy.
- ``buildings``: the project venv (torch CPU, ``yolov5==7.0.6``,
  ``huggingface_hub==0.19.4``).

Usage:
  python tools/pseudo_label_redline.py                       # scout captures
  python tools/pseudo_label_redline.py --source red         # attack captures
  python tools/pseudo_label_redline.py --preview 12 --overwrite
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

try:  # running as `python tools/pseudo_label_redline.py`
    from redline_common import BASE, ROOT
except ImportError:  # running as `python -m tools.pseudo_label_redline`
    from tools.redline_common import BASE, ROOT

IMAGE_SUFFIXES = (".jpg", ".jpeg")
PREVIEW_DIR = ROOT / "runs" / "redline" / "pseudo_preview"

# Keep in sync with COCbot.core.vision.redline (860x732 frames).
CENTER = (425, 345)
VILLAGE_Y = (40, 650)
VILLAGE_X = (20, 840)
# Yellow border diamond from datasets/redline/images/raw/data.py:
# corners (430,56) (845,368) (430,680) (15,368) -> 830*624/2. 1 tile = 20 px.
MAP_DIAMOND_AREA = 258_960.0
TILE_PX = 20.0

DEFAULT_DETECTOR_REPO = "keremberke/yolov5m-clash-of-clans"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def label_line(points_px, width: int, height: int) -> str:
    coords = " ".join(
        f"{min(max(x / width, 0.0), 1.0):.6f} {min(max(y / height, 0.0), 1.0):.6f}"
        for x, y in points_px
    )
    return f"0 {coords}"


def to_polygon(contour, max_points: int):
    """Simplify a pixel contour into a closed polygon of <= max_points."""
    import cv2

    peri = cv2.arcLength(contour, True)
    eps = max(peri * 0.002, 0.5)
    approx = cv2.approxPolyDP(contour, eps, True)
    while len(approx) > max_points and eps < peri * 0.05:
        eps *= 1.5
        approx = cv2.approxPolyDP(contour, eps, True)
    pts = approx.reshape(-1, 2)
    if len(pts) >= 4:
        return pts
    raw = contour.reshape(-1, 2)  # degenerate simplify -> decimated raw contour
    step = max(len(raw) // max_points, 1)
    return raw[::step]


def save_preview(image, polygon, out_path: Path, boxes=None):
    import cv2
    import numpy as np

    overlay = image.copy()
    if boxes is not None:
        for x1, y1, x2, y2 in boxes:
            cv2.rectangle(overlay, (int(x1), int(y1)), (int(x2), int(y2)),
                          (255, 255, 255), 1)
    pts = polygon.astype(np.int32).reshape(-1, 1, 2)
    cv2.fillPoly(overlay, [pts], (0, 0, 255))
    cv2.polylines(overlay, [pts], True, (0, 255, 255), 2)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), cv2.addWeighted(overlay, 0.45, image, 0.55, 0))


# ---------------------------------------------------------------------------
# Source "red": trace the visible no-deploy line
# ---------------------------------------------------------------------------

def red_line_mask(image):
    """Saturated red pixels inside the village area (the no-deploy line)."""
    import cv2
    import numpy as np

    height, width = image.shape[:2]
    mask = np.zeros((height, width), dtype=np.uint8)
    y0, y1 = VILLAGE_Y
    x0, x1 = VILLAGE_X
    region = image[y0:y1, x0:x1].astype(int)
    red = region[:, :, 2]
    green = region[:, :, 1]
    blue = region[:, :, 0]
    hit = (red > green + 20) & (red > blue + 35) & (red > 90)
    mask[y0:y1, x0:x1] = hit.astype(np.uint8) * 255
    return mask


def largest_redline_contour(mask, min_blob: int, close_iters: int):
    """Clean the red mask and return its largest closed contour."""
    import cv2
    import numpy as np

    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        (mask > 0).astype(np.uint8), connectivity=8
    )
    clean = np.zeros_like(mask)
    for i in range(1, count):
        if stats[i, cv2.CC_STAT_AREA] >= min_blob:
            clean[labels == i] = 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    closed = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, kernel, iterations=close_iters)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    return max(contours, key=cv2.contourArea)


# ---------------------------------------------------------------------------
# Source "buildings": union of detected building boxes + margin
# ---------------------------------------------------------------------------

def load_building_detector(repo: str, filename: str, conf: float):
    from huggingface_hub import hf_hub_download
    import yolov5

    path = hf_hub_download(repo_id=repo, filename=filename)
    model = yolov5.load(path)
    model.conf = conf
    print("Detector:", path)
    print("Classes:", model.names)
    return model


def building_contour(model, image, margin_px: int, bridge_px: int, size: int):
    """Largest contour of the gap-bridged, margin-dilated union of boxes."""
    import cv2
    import numpy as np

    # AutoShape treats ndarray input as RGB; cv2 loads BGR -> flip first.
    rgb = np.ascontiguousarray(image[:, :, ::-1])
    results = model(rgb, size=size)
    det = results.xyxy[0].cpu().numpy()  # (n, 6): x1 y1 x2 y2 conf cls
    if not len(det):
        return None, []

    y0, y1 = VILLAGE_Y
    x0, x1 = VILLAGE_X
    union = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
    for x1b, y1b, x2b, y2b in det[:, :4]:
        xa, ya = max(int(x1b), x0), max(int(y1b), y0)
        xb, yb = min(int(x2b), x1), min(int(y2b), y1)
        if xa < xb and ya < yb:
            union[ya - y0:yb - y0, xa - x0:xb - x0] = 255
    # 1) bridge defense-free pockets inside the base (closing keeps the
    #    outer boundary in place), 2) push the boundary out by margin-px.
    bridge = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * (bridge_px // 2) + 1,) * 2)
    closed = cv2.morphologyEx(union, cv2.MORPH_CLOSE, bridge, iterations=2)
    radius = max(int(round(margin_px)), 1)
    margin = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * radius + 1, 2 * radius + 1))
    grown = cv2.dilate(closed, margin, iterations=1)

    contours, _ = cv2.findContours(grown, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, det[:, :4].tolist()
    # Largest contour, shifted back to full-image coordinates.
    largest = max(contours, key=cv2.contourArea) + [x0, y0]
    return largest, det[:, :4].tolist()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Pseudo-label redline images (scout: buildings; attack: red line)")
    parser.add_argument("--source", choices=("buildings", "red"), default="buildings",
                        help="buildings = scout captures (no visible redline); "
                             "red = attack-phase captures")
    parser.add_argument("--preview", type=int, default=12,
                        help="Number of preview overlays (flagged images first)")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--max-points", type=int, default=64)
    parser.add_argument("--conf", type=float, default=0.25,
                        help="Detector confidence (buildings) / unused (red)")
    parser.add_argument("--margin-px", type=int, default=60,
                        help="buildings: push the boundary out by this many pixels")
    parser.add_argument("--bridge-px", type=int, default=120,
                        help="buildings: bridge defense-free pockets up to this size")
    parser.add_argument("--detector-repo", default=DEFAULT_DETECTOR_REPO)
    parser.add_argument("--detector-file", default="best.pt")
    parser.add_argument("--detector-size", type=int, default=640)
    parser.add_argument("--min-blob", type=int, default=40,
                        help="red: drop specks smaller than this many pixels")
    parser.add_argument("--close-iters", type=int, default=2,
                        help="red: closing passes bridging line gaps")
    args = parser.parse_args()

    try:
        import cv2  # noqa: F401
        import numpy  # noqa: F401
    except Exception as exc:
        print("opencv-python and numpy are required. Error:", exc)
        raise SystemExit(1)

    img_raw = BASE / "images" / "raw"
    lbl_raw = BASE / "labels" / "raw"
    if not img_raw.is_dir():
        print("Missing:", img_raw)
        return

    images = sorted(p for p in img_raw.iterdir()
                    if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)
    if not images:
        print("No .jpg/.jpeg images in", img_raw)
        return

    jobs = [p for p in images
            if args.overwrite or not (lbl_raw / (p.stem + ".txt")).is_file()]
    print(f"source={args.source} images={len(images)} to_label={len(jobs)} "
          f"already_labeled={len(images) - len(jobs)}")

    detector = None
    if args.source == "buildings":
        detector = load_building_detector(
            args.detector_repo, args.detector_file, args.conf)

    lbl_raw.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    qc_path = PREVIEW_DIR / "qc_report.csv"

    rows: list[dict] = []
    flagged: list[str] = []
    n_labeled = n_empty = 0
    previews: dict[str, tuple] = {}  # stem -> (polygon, boxes) to render later

    for path in jobs:
        import cv2

        image = cv2.imread(str(path))
        if image is None:
            rows.append({"stem": path.stem, "detections": -1,
                         "area_ratio": -1.0, "flags": "unreadable"})
            continue
        height, width = image.shape[:2]
        flags: list[str] = []
        boxes: list = []
        contour = None

        if args.source == "red":
            mask = red_line_mask(image)
            contour = largest_redline_contour(mask, args.min_blob, args.close_iters)
        else:
            contour, boxes = building_contour(
                detector, image, args.margin_px, args.bridge_px, args.detector_size)

        if contour is None:
            flags.append("no_base" if args.source == "buildings" else "no_red_line")
            n_empty += 1
        else:
            import cv2 as cv

            filled_area = cv.contourArea(contour)
            ratio = filled_area / MAP_DIAMOND_AREA
            inside = cv.pointPolygonTest(
                contour, (float(CENTER[0]), float(CENTER[1])), False) >= 0
            if args.source == "buildings":
                if len(boxes) < 8:
                    flags.append("few_buildings")
            if ratio < 0.10:
                flags.append("small")
            if ratio > 1.15:
                flags.append("oversize")
            if not inside:
                flags.append("center_out")
            if flags:
                flagged.append(path.stem)

        polygon = None
        if contour is not None:
            polygon = to_polygon(contour, args.max_points)
            n_labeled += 1

        with (lbl_raw / f"{path.stem}.txt").open("w", encoding="utf-8",
                                                 newline="\n") as f:
            if polygon is not None:
                f.write(label_line(polygon, width, height) + "\n")

        rows.append({
            "stem": path.stem,
            "detections": len(boxes) if args.source == "buildings" else "",
            "area_ratio": (round(filled_area / MAP_DIAMOND_AREA, 3)
                           if contour is not None else 0.0),
            "flags": ",".join(flags),
        })
        if polygon is not None and args.preview > 0:
            previews[path.stem] = (polygon, boxes)

    # Render previews: flagged first, then an even spread across the rest.
    if args.preview > 0 and previews:
        chosen = flagged[:args.preview]
        rest = [s for s in previews if s not in chosen]
        slots = args.preview - len(chosen)
        if slots > 0 and rest:
            step = max(len(rest) - 1, 1) / max(slots - 1, 1)
            chosen += [rest[round(i * step)] for i in range(slots)]
        for stem in chosen:
            if stem not in previews:
                continue
            import cv2

            polygon, boxes = previews[stem]
            image = cv2.imread(str(img_raw / f"{stem}.jpg"))
            save_preview(image, polygon, PREVIEW_DIR / f"{stem}.jpg", boxes)

    with qc_path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = ["stem", "detections", "area_ratio", "flags"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"labeled={n_labeled} empty={n_empty} flagged={len(flagged)}")
    if flagged:
        print("Flagged for review (see qc_report.csv):",
              ", ".join(flagged[:12]), "..." if len(flagged) > 12 else "")
    print("QC report:", qc_path)
    print("Previews:", PREVIEW_DIR)
    print("Next: review previews, fix flagged labels, then:")
    print("  python tools/split_redline_dataset.py --val-ratio 0.2 --clean")


if __name__ == "__main__":
    main()
