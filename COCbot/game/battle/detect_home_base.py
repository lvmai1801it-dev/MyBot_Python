# ==== COCbot/game/battle/detect_home_base.py ====
import os
import subprocess
import sys

import cv2

import COCbot.app.paths
from COCbot.platform.unicode import imread_unicode
from COCbot.vision.capture import take_screenshot
from COCbot.vision.ocr import reader

DEBUG = True


def _log(*args):
    """In log có tiền tố để dễ grep. Tắt khi DEBUG=False."""
    if DEBUG:
        print("🔎", *args)


TEMPLATES_DIR = str(COCbot.app.paths.TEMPLATE_DIR)

SHOP_TEMPLATE = os.path.join(TEMPLATES_DIR, "shop.png")
SHOP_NEW = os.path.join(TEMPLATES_DIR, "shop.png")
BUILD_NEW = os.path.join(TEMPLATES_DIR, "build.png")
GAME_SETTING = os.path.join(TEMPLATES_DIR, "game_setting.png")

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

SCREEN_W = 860
SCREEN_H = 732

# Dead code — giữ để tham khảo. Gốc: (1408, 826, 1582, 886)
x1, y1, x2, y2 = (757, 672, 850, 721)


def detect_home_base():
    """
    Kiểm tra game có đang ở màn hình Home Base không.
    Trả về True nếu phát hiện dấu hiệu home base, ngược lại False.

    3 bước kiểm tra (early-exit):
      Check 1: Template matching icon Shop/Build trên toàn ảnh
      Check 2: Template matching icon Settings trong ROI cố định
      Check 3: OCR đọc chữ "Shop"/"Build" trong 2 vùng cố định
    """

    # ── Bước 0: Chụp màn hình & đọc ảnh ──────────────────────
    img = take_screenshot("home.png")

    if img is None or img.size == 0:
        _log("❌ Không đọc được screenshot home.png")
        return False

    h_img, w_img = img.shape[:2]
    _log(f"📐 Screenshot size: {w_img}×{h_img}  (kỳ vọng {SCREEN_W}×{SCREEN_H})")

    if (w_img, h_img) != (SCREEN_W, SCREEN_H):
        _log(
            f"⚠️  Độ phân giải KHÁC kỳ vọng {SCREEN_W}×{SCREEN_H} → toạ độ có thể sai lệch!"
        )

    gray_full = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img

    # ── Check 1: Template matching icon Shop/Build toàn ảnh ──
    for tpl_path in (SHOP_NEW, BUILD_NEW, SHOP_TEMPLATE):
        tpl = imread_unicode(tpl_path, cv2.IMREAD_GRAYSCALE)
        tpl_name = os.path.basename(tpl_path)

        if tpl is None:
            _log(f"⚠️  Check1: không đọc được template {tpl_name}")
            continue

        _log(f"  Check1: {tpl_name} size={tpl.shape[1]}×{tpl.shape[0]}")

        if tpl.shape[0] < gray_full.shape[0] and tpl.shape[1] < gray_full.shape[1]:
            res = cv2.matchTemplate(gray_full, tpl, cv2.TM_CCOEFF_NORMED)
            score = float(res.max())
            _log(f"  Check1: {tpl_name} max_score={score:.3f} (ngưỡng 0.7)")

            if score >= 0.7:
                _log(f"✅ Check1 MATCH: {tpl_name} (score={score:.3f})")
                return True
        else:
            _log(f"⚠️  Check1: {tpl_name} LỚN HƠN ảnh, bỏ qua")

    # ── Check 2: Settings icon trong vùng ROI cố định ────────
    x1_roi, y1_roi, x2_roi, y2_roi = (777, 406, 859, 576)

    if x2_roi > w_img or y2_roi > h_img:
        _log(
            f"⚠️  Check2: ROI ({x1_roi},{y1_roi},{x2_roi},{y2_roi}) VƯỢT BIÊN ảnh {w_img}×{h_img} → sẽ bị cắt rỗng!"
        )

    roi = gray_full[y1_roi:y2_roi, x1_roi:x2_roi]
    _log(
        f"  Check2: ROI shape={roi.shape[1] if roi.size else 0}×{roi.shape[0] if roi.size else 0} (size={roi.size})"
    )

    tpl_settings = imread_unicode(GAME_SETTING, cv2.IMREAD_GRAYSCALE)

    if roi.size == 0:
        _log("⚠️  Check2: ROI RỖNG → bỏ qua (toạ độ vượt biên?)")
    elif tpl_settings is None:
        _log("⚠️  Check2: không đọc được game_setting.png")
    elif tpl_settings.shape[0] >= roi.shape[0] or tpl_settings.shape[1] >= roi.shape[1]:
        _log(
            f"⚠️  Check2: template settings {tpl_settings.shape[1]}×{tpl_settings.shape[0]} không nhỏ hơn ROI {roi.shape[1]}×{roi.shape[0]} → bỏ qua"
        )
    else:
        res_settings = cv2.matchTemplate(roi, tpl_settings, cv2.TM_CCOEFF_NORMED)
        score_settings = float(res_settings.max())
        _log(f"  Check2: settings max_score={score_settings:.3f}")
        if score_settings >= 0.7:
            _log(f"✅ Check2 MATCH settings (score={score_settings:.3f})")
            return True

    # ── Check 3: OCR đọc chữ "Shop"/"Build" trong 2 vùng cố định ──
    OCR_ROIS = (
        (
            779,
            350,
            852,
            464,
        ),  # vùng UI mới (góc trên-phải) — gốc (1450, 430, 1585, 570)
        (
            757,
            672,
            850,
            721,
        ),  # vùng UI cũ (footer dưới-phải) — gốc (1408, 826, 1582, 886)
    )

    for idx, (rx1, ry1, rx2, ry2) in enumerate(OCR_ROIS, start=1):
        if rx2 > w_img or ry2 > h_img:
            _log(
                f"⚠️  Check3[{idx}]: ROI ({rx1},{ry1},{rx2},{ry2}) VƯỢT BIÊN ảnh {w_img}×{h_img} → crop sẽ rỗng!"
            )

        crop = img[ry1:ry2, rx1:rx2]
        _log(
            f"  Check3[{idx}]: crop shape={crop.shape[1] if crop.size else 0}×{crop.shape[0] if crop.size else 0} (size={crop.size})"
        )

        if crop.size == 0:
            _log(f"⚠️  Check3[{idx}]: crop rỗng → BỎ QUA resize/OCR")
            continue

        upscaled = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        try:
            results = reader.readtext(upscaled)
            _log(f"  Check3[{idx}]: OCR trả về {len(results)} vùng text")

            for _, text, _conf in results:
                t_low = text.lower()
                _log(f'    OCR text: "{text}"')
                if "shop" in t_low or "build" in t_low:
                    _log(f'✅ Check3 MATCH: "{text}"')
                    return True
        except Exception as e:
            _log(f"⚠️  Check3[{idx}]: OCR lỗi: {e}")

    _log("❌ Không phát hiện home base (cả 3 check đều fail)")
    return False
