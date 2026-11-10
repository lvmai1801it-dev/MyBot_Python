# ==== COCbot/game/training/smart_train_ocr.py ====
"""Numeric OCR used by smart-train.

All engines now live in :mod:`COCbot.vision.read_text.numbers` (PaddleOCR first,
Tesseract fallback). This keeps one PaddleOCR instance for the whole app and
avoids loading it twice.
"""

from COCbot.vision.read_text.numbers import read_number, paddle_available

PADDLE_AVAILABLE = None  # lazily resolved by read_number()


def is_paddle_available() -> bool:
    return paddle_available()


def read_number_ocr(crop_bgr):
    if crop_bgr is None or getattr(crop_bgr, "size", 0) == 0:
        return 0
    return read_number(crop_bgr) or 0


def read_troop_count(roi_img, match_loc, tpl_size):
    w, h = tpl_size
    x, y = match_loc
    ocr_y1, ocr_y2 = 10, 27
    ocr_x1 = max(0, x - 2)
    ocr_x2 = min(roi_img.shape[1], x + w + 5)
    num_crop = roi_img[ocr_y1:ocr_y2, ocr_x1:ocr_x2]
    return read_number_ocr(num_crop)
