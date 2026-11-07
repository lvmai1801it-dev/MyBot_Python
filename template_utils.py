# ==== template_utils.py ====
import cv2

from utils.unicode import imread_unicode


def _match_gray(img_gray, tpl_path: str, threshold=None, roi=None):
    thr = float(threshold)
    if thr > 1.0:
        thr = thr / 100.0
    thr = max(0.0, min(1.0, thr))
    if roi is not None:
        x1, y1, x2, y2 = roi
        h, w = img_gray.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            return (False, 0.0, None)
        src = img_gray[y1:y2, x1:x2]
    else:
        src = img_gray
    tpl = imread_unicode(tpl_path, cv2.IMREAD_GRAYSCALE)
    if tpl is None or tpl.size == 0:
        return (False, 0.0, None)
    if src.shape[0] < tpl.shape[0] or src.shape[1] < tpl.shape[1]:
        return (False, 0.0, None)
    res = cv2.matchTemplate(src, tpl, cv2.TM_CCOEFF_NORMED)
    _, score, _, loc = cv2.minMaxLoc(res)
    return (score >= thr, float(score), loc)


def _match_color(image_bgr, tpl_path, threshold_pct, roi=None):
    thr = float(threshold_pct)
    if thr > 1.0:
        thr = thr / 100.0
    thr = max(0.0, min(1.0, thr))
    tpl = imread_unicode(tpl_path, cv2.IMREAD_COLOR)
    if tpl is None or tpl.size == 0:
        print(f'[CC] ❌ missing template: {tpl_path}')
        return (False, 0.0, None)
    src = image_bgr
    if roi:
        x1, y1, x2, y2 = roi
        h, w = image_bgr.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            print('[CC] ❌ invalid ROI after clamp')
            return (False, 0.0, None)
        src = image_bgr[y1:y2, x1:x2]
    th, tw = tpl.shape[:2]
    if src.shape[0] < th or src.shape[1] < tw:
        return (False, 0.0, None)
    res = cv2.matchTemplate(src, tpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    cx = max_loc[0] + tw // 2
    cy = max_loc[1] + th // 2
    if roi:
        cx += x1
        cy += y1
    ok = max_val >= thr
    return (ok, float(max_val), (cx, cy))


def _match_template(img, tmpl_path, region, thresh):
    x1, y1, x2, y2 = region
    h, w = img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return (0, None, None)
    roi = img[y1:y2, x1:x2]

    tmpl = imread_unicode(tmpl_path, cv2.IMREAD_UNCHANGED)
    if tmpl is None:
        raise FileNotFoundError(f'template not found: {tmpl_path}')

    if tmpl.ndim == 3 and tmpl.shape[2] == 4:
        tmpl = cv2.cvtColor(tmpl, cv2.COLOR_BGRA2BGR)
    if roi.ndim == 3 and roi.shape[2] == 4:
        roi = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR)

    roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if roi.ndim == 3 else roi
    tmpl_gray = cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY) if tmpl.ndim == 3 else tmpl

    if (roi_gray.shape[0] < tmpl_gray.shape[0]
            or roi_gray.shape[1] < tmpl_gray.shape[1]):
        return (0, None, None)

    res = cv2.matchTemplate(roi_gray, tmpl_gray, cv2.TM_CCOEFF_NORMED)
    _, score, _, loc = cv2.minMaxLoc(res)
    if score < thresh:
        return (score, None, None)
    cx = x1 + loc[0] + tmpl_gray.shape[1] // 2
    cy = y1 + loc[1] + tmpl_gray.shape[0] // 2
    return (score, cx, cy)