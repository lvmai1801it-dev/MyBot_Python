# ==== COCbot/game/training/smart_train_utils.py ====
import os
import cv2
import numpy as np

import COCbot.app.paths
from COCbot.platform.unicode import imread_unicode

TEMPLATE_ROOT = os.path.join(COCbot.app.paths.TEMPLATE_DIR, "Smart_Auto_train")
PNG_EXT = ".png"

def find_template_path(name: str, subdir: str | None = None) -> str | None:
    filename = name if name.lower().endswith(PNG_EXT) else name + PNG_EXT
    target = filename.lower()

    if subdir:
        root_dir = os.path.join(TEMPLATE_ROOT, subdir)
        for root, _, files in os.walk(root_dir):
            for f in files:
                if f.lower() == target:
                    return os.path.join(root, f)

    for root, _, files in os.walk(TEMPLATE_ROOT):
        for f in files:
            if f.lower() == target:
                return os.path.join(root, f)

    return None

def match(name: str, hay, thresh: float = 0.92, subdir: str | None = None):
    path = find_template_path(name, subdir)
    if not path or hay is None:
        return (False, 0.0, (0, 0))

    tpl = imread_unicode(path)
    if tpl is None or tpl.shape[0] > hay.shape[0] or tpl.shape[1] > hay.shape[1]:
        return (False, 0.0, (0, 0))

    res = cv2.matchTemplate(hay, tpl, cv2.TM_CCOEFF_NORMED)
    _, val, _, loc = cv2.minMaxLoc(res)
    h, w = tpl.shape[:2]
    return (val >= thresh, val, (loc[0] + w // 2, loc[1] + h // 2))

def match_multiscale(tpl_path, hay, thresh=0.45):
    if tpl_path is None or hay is None:
        return (False, 0.0, (0, 0))

    tpl_color = imread_unicode(tpl_path)
    if tpl_color is None or tpl_color.size == 0:
        return (False, 0.0, (0, 0))

    tpl_gray = cv2.cvtColor(tpl_color, cv2.COLOR_BGR2GRAY)
    hay_gray = cv2.cvtColor(hay, cv2.COLOR_BGR2GRAY)
    tpl_edge = cv2.Canny(tpl_gray, 50, 150)
    hay_edge = cv2.Canny(hay_gray, 50, 150)

    best = (0.0, (0, 0))
    scales = [1.0, 0.9, 1.1, 0.8, 1.2, 0.7, 1.3, 0.6, 1.4, 0.5, 1.5, 0.45, 0.4]

    for scale in scales:
        if scale != 1.0:
            nw, nh = int(tpl_edge.shape[1] * scale), int(tpl_edge.shape[0] * scale)
            if nw < 10 or nh < 10:
                continue
            scaled = cv2.resize(tpl_edge, (nw, nh), interpolation=cv2.INTER_AREA)
        else:
            scaled = tpl_edge

        if scaled.shape[0] > hay_edge.shape[0] or scaled.shape[1] > hay_edge.shape[1]:
            continue

        res = cv2.matchTemplate(hay_edge, scaled, cv2.TM_CCOEFF_NORMED)
        _, val, _, loc = cv2.minMaxLoc(res)
        if val > best[0]:
            h, w = scaled.shape[:2]
            best = (val, (loc[0] + w // 2, loc[1] + h // 2))

    return (best[0] >= thresh, best[0], best[1])

def roi(img, x1: int, y1: int, x2: int, y2: int):
    return img[y1:y2, x1:x2]

# Alias để tương thích với code cũ
_roi = roi