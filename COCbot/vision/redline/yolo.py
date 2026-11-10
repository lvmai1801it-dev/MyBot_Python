"""YOLO segmentation bridge for redline / no-deploy zone.

Recommended task: instance segmentation with one class `base_area` (the area
inside the red line). The largest mask contour is the red line polygon.

Why segmentation instead of detection:
- A bounding box does not describe an irregular base/redline.
- A mask -> contour -> polygon gives the actual deployable boundary.
- A keypoint model (8-12 redline points) is a valid alternative, but polygon
  labels are easier to produce and audit.

The model is optional. If `models/redline_seg.pt` (or .onnx) is missing or
inference fails, callers fall back to `get_redline_edges_cv()`.
"""

from __future__ import annotations

import os
from typing import List, Sequence, Tuple

import cv2
import numpy as np

from COCbot.vision.redline.geometry import side_for_point

Point = Tuple[int, int]


def _src_dir() -> str:
    # .../src/COCbot/vision/redline/yolo.py -> .../src
    return os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )


def resolve_model_path(model_path: str) -> str:
    if not model_path:
        return ""
    if os.path.isabs(model_path):
        return model_path
    candidate = os.path.join(_src_dir(), model_path)
    if os.path.exists(candidate):
        return candidate
    return os.path.abspath(model_path)


def polygon_to_edges(poly: Sequence[Point]) -> List[List[Point]]:
    """Split a closed redline polygon into [TR, BR, BL, TL] edge lists."""
    if not poly or len(poly) < 4:
        return []

    sides = {"TR": [], "BR": [], "BL": [], "TL": []}
    for p in poly:
        side = side_for_point(p[0], p[1])
        if side:
            sides[side].append((int(p[0]), int(p[1])))

    for side, pts in sides.items():
        if side in ("TL", "TR"):
            pts.sort(key=lambda q: (q[0], q[1]))
        else:
            pts.sort(key=lambda q: (q[0], -q[1]))

    if any(len(sides[s]) < 2 for s in ("TR", "BR", "BL", "TL")):
        return []

    return [sides["TR"], sides["BR"], sides["BL"], sides["TL"]]


class RedlineSegmenter:
    """Thin wrapper around Ultralytics YOLO segmentation.

    Accepts .pt or .onnx; Ultralytics handles pre/post-processing.
    """

    def __init__(self, model_path: str, imgsz: int = 736, conf: float = 0.25):
        self.model = None
        self.imgsz = imgsz
        self.conf = conf
        self.ok = False
        self.error = ""

        path = resolve_model_path(model_path)
        if not path or not os.path.exists(path):
            self.error = f"model not found: {model_path}"
            return

        try:
            from ultralytics import YOLO  # lazy import; optional dependency
            self.model = YOLO(path)
            self.ok = True
        except Exception as e:
            self.error = f"cannot load YOLO model: {e}"

    def predict_polygon(self, img_bgr: np.ndarray) -> List[Point]:
        """Return the largest `base_area` mask contour as a polygon."""
        if not self.ok or self.model is None or img_bgr is None:
            return []

        try:
            results = self.model.predict(
                source=img_bgr, imgsz=self.imgsz, conf=self.conf, verbose=False)
        except Exception as e:
            self.error = f"inference failed: {e}"
            return []

        if not results:
            return []

        r = results[0]
        if getattr(r, "masks", None) is None or len(r.masks.data) == 0:
            return []

        h, w = img_bgr.shape[:2]
        best_mask = None
        best_area = 0

        for mask_t in r.masks.data:
            mask = mask_t.detach().cpu().numpy()
            mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
            mask = (mask > 0.5).astype(np.uint8) * 255
            area = int(cv2.countNonZero(mask))
            if area > best_area:
                best_area = area
                best_mask = mask

        if best_mask is None or best_area < 500:
            return []

        contours, _ = cv2.findContours(
            best_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return []

        contour = max(contours, key=cv2.contourArea)
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.005 * peri, True)
        poly = [(int(p[0][0]), int(p[0][1])) for p in approx]
        return poly if len(poly) >= 4 else []


def get_redline_from_yolo(img_bgr: np.ndarray, model_path: str,
                          imgsz: int = 736, conf: float = 0.25):
    """Return [TR, BR, BL, TL] edges from a YOLO-seg model, or None."""
    segmenter = RedlineSegmenter(model_path, imgsz=imgsz, conf=conf)
    if not segmenter.ok:
        if segmenter.error:
            print(f"[YOLO] {segmenter.error}")
        return None

    poly = segmenter.predict_polygon(img_bgr)
    if not poly:
        print("[YOLO] no base_area mask found")
        return None

    edges = polygon_to_edges(poly)
    if not edges:
        print("[YOLO] mask polygon could not be split into 4 edges")
        return None

    print(f"[YOLO] redline: polygon={len(poly)} pts, "
          f"edges={[len(e) for e in edges]}")
    return edges
