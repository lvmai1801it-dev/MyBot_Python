"""Redline detection: YOLO segmentation first, OpenCV isometric fallback.

The old MyBot.run.dll `getRedArea` path is intentionally removed:
- it triggers DetectRedArea.checkLicence() -> Process.Kill() and is flaky in a
  non-MyBot host;
- it can close the emulator when the process is elevated.

YOLO-seg (`base_area` mask) is the primary path when a model is configured.
The pure OpenCV fallback is always available.
"""

import math
import os

import cv2
import numpy as np

from COCbot.vision.redline.yolo import get_redline_from_yolo, resolve_model_path


TARGET_HEX_COLORS = [
    "#cb6326", "#d56e2a", "#cf6425", "#7c3f16",
    "#bd4f1c", "#da6226", "#c04e1f",
]


def hex_to_bgr(hex_color):
    hex_color = hex_color.lstrip('#')
    b = int(hex_color[4:6], 16)
    g = int(hex_color[2:4], 16)
    r = int(hex_color[0:2], 16)
    return (b, g, r)


def get_redline_edges_cv(img_bgr, tolerance=25):
    """OpenCV isometric fallback (kept from the original COCbot.attack.py)."""
    h, w = img_bgr.shape[:2]

    center_map = (433, 353)

    b = img_bgr[:, :, 0].astype(int)
    g = img_bgr[:, :, 1].astype(int)
    r = img_bgr[:, :, 2].astype(int)

    village_roi = np.zeros((h, w), dtype=bool)
    village_roi[130:560, 150:760] = True

    red_match = (r > g + 20) & (r > b + 35) & (r > 90) & village_roi
    ys, xs = np.where(red_match)

    if len(xs) > 20:
        dx = int(np.percentile(np.abs(xs - center_map[0]), 95))
        dy = int(np.percentile(np.abs(ys - center_map[1]), 95))
        dx = max(240, min(340, dx))
        dy = max(180, min(250, dy))
    else:
        dx = 280
        dy = 210

    p_top_red = (center_map[0], center_map[1] - dy)
    p_bottom_red = (center_map[0], center_map[1] + dy)
    p_left_red = (center_map[0] - dx, center_map[1])
    p_right_red = (center_map[0] + dx, center_map[1])

    ui_bottom_limit = 615

    def parallel_offset(p1, p2, dist=40):
        ddx = p2[0] - p1[0]
        ddy = p2[1] - p1[1]
        length = math.hypot(ddx, ddy)
        if length == 0:
            return [p1, p1, p1, p1, p1]
        n1 = (-ddy / length, ddx / length)
        n2 = (ddy / length, -ddx / length)
        mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        to_mid = (mid[0] - center_map[0], mid[1] - center_map[1])
        n = n1 if (n1[0] * to_mid[0] + n1[1] * to_mid[1]) > (
            n2[0] * to_mid[0] + n2[1] * to_mid[1]) else n2

        op1 = (max(10, min(w - 10, int(p1[0] + n[0] * dist))),
               max(35, min(ui_bottom_limit, int(p1[1] + n[1] * dist))))
        op2 = (max(10, min(w - 10, int(p2[0] + n[0] * dist))),
               max(35, min(ui_bottom_limit, int(p2[1] + n[1] * dist))))

        return [
            op1,
            (int(op1[0] + (op2[0] - op1[0]) * 0.25),
             int(op1[1] + (op2[1] - op1[1]) * 0.25)),
            (int(op1[0] + (op2[0] - op1[0]) * 0.5),
             int(op1[1] + (op2[1] - op1[1]) * 0.5)),
            (int(op1[0] + (op2[0] - op1[0]) * 0.75),
             int(op1[1] + (op2[1] - op1[1]) * 0.75)),
            op2,
        ]

    return [
        parallel_offset(p_top_red, p_right_red, 40),     # Edge 0: TR
        parallel_offset(p_right_red, p_bottom_red, 40),  # Edge 1: BR
        parallel_offset(p_bottom_red, p_left_red, 40),   # Edge 2: BL
        parallel_offset(p_left_red, p_top_red, 40),      # Edge 3: TL
    ]


def get_redline_edges_ex(img_bgr, tolerance=25, model_path=""):
    """
    Redline detection with source information.

    Returns (edges, source) where source is "yolo", "cv" or "none".
    """
    if img_bgr is None or not hasattr(img_bgr, 'size') or img_bgr.size == 0:
        return None, "none"

    if model_path:
        resolved = resolve_model_path(model_path)
        if os.path.exists(resolved):
            yolo_edges = get_redline_from_yolo(img_bgr, resolved)
            if yolo_edges:
                return yolo_edges, "yolo"
        # Missing model is normal: fall back silently to OpenCV.

    return get_redline_edges_cv(img_bgr, tolerance), "cv"


def get_redline_edges(img_bgr, tolerance=25, model_path=""):
    """Backward-compatible wrapper returning only the edges."""
    return get_redline_edges_ex(img_bgr, tolerance, model_path)[0]
