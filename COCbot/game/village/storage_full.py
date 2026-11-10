# ==== COCbot/game/village/storage_full.py ====
"""Detect when the three main storages are full.

Templates `*_collector_full.png` are the orange-backed resource icons that
appear above a collector/storage when it is full.  We match them on the home
village screenshot with OpenCV (TM_CCOEFF_NORMED); a resource counts as full
when at least `min_matches` icons of that type are found.
"""

from __future__ import annotations

import os

import cv2

import COCbot.app.paths  # noqa: F401
from COCbot.app.paths import TEMPLATE_DIR
from COCbot.platform.unicode import imread_unicode

FULL_TEMPLATES = {
    "gold": "gold_collector_full.png",
    "elixir": "elixir_collector_full.png",
    "de": "DE_collector_full.png",
}

DEFAULT_THRESHOLD = 0.85
DEFAULT_MIN_MATCHES = 1
_NMS_RADIUS = 8


def _count_matches(image, tpl, threshold, max_matches=40):
    """Return [(cx, cy, score)] above threshold, suppressed within radius."""
    th, tw = tpl.shape[:2]
    res = cv2.matchTemplate(image, tpl, cv2.TM_CCOEFF_NORMED)
    work = res.copy()
    found = []
    for _ in range(max_matches):
        _, score, _, loc = cv2.minMaxLoc(work)
        if score < threshold:
            break
        x, y = loc
        found.append((x + tw // 2, y + th // 2, float(score)))
        x0, y0 = max(0, x - _NMS_RADIUS), max(0, y - _NMS_RADIUS)
        x1 = min(work.shape[1], x + _NMS_RADIUS)
        y1 = min(work.shape[0], y + _NMS_RADIUS)
        work[y0:y1, x0:x1] = -1.0
    return found


def detect_full_storages(img=None, threshold=DEFAULT_THRESHOLD,
                         min_matches=DEFAULT_MIN_MATCHES):
    """Detect full gold/elixir/dark storages on a home-village screenshot.

    Returns a dict:
        {
          "gold": {"full": bool, "matches": [(x, y, score), ...]},
          "elixir": {...},
          "de": {...},
          "all_full": bool,
        }
    """
    if img is None:
        from COCbot.vision.capture import take_screenshot
        img = take_screenshot("storage_full.png")

    result = {name: {"full": False, "matches": []} for name in FULL_TEMPLATES}
    result["all_full"] = False
    if img is None or not getattr(img, "size", 0):
        print("[STORAGE] Không có ảnh để kiểm tra.")
        return result

    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    threshold = float(threshold)
    min_matches = max(1, int(min_matches))

    for name, filename in FULL_TEMPLATES.items():
        path = os.path.join(str(TEMPLATE_DIR), filename)
        tpl = imread_unicode(path, cv2.IMREAD_COLOR)
        if tpl is None:
            print(f"[STORAGE] Thiếu template: {filename}")
            continue
        if tpl.shape[0] > img.shape[0] or tpl.shape[1] > img.shape[1]:
            print(f"[STORAGE] Template {filename} lớn hơn ảnh.")
            continue
        matches = _count_matches(img, tpl, threshold)
        is_full = len(matches) >= min_matches
        result[name] = {"full": is_full, "matches": matches}
        print(f"[STORAGE] {name}: {len(matches)} icon full "
              f"(ngưỡng {threshold:.2f}) → {'ĐẦY' if is_full else 'chưa đầy'}")

    result["all_full"] = all(result[n]["full"] for n in FULL_TEMPLATES)
    return result


if __name__ == "__main__":
    r = detect_full_storages()
    print("ALL FULL:", r["all_full"])
