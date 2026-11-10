"""Numeric OCR for Clash of Clans resource / loot labels.

Why this module exists
----------------------
The game draws numbers in a stylized white font with a black outline, over a
semi-transparent coloured bar. EasyOCR and plain Tesseract are unreliable on
that combination. **PaddleOCR (PP-OCRv6) reads all tested resource crops
exactly** (confidence 0.98-0.9999), so it is the primary engine.

Fallback order:
  1. PaddleOCR (already used by smart-train)
  2. Tesseract with a white-mask preprocessing tuned for CoC digits

The engine is lazy: importing this module does not load Paddle/EasyOCR/torch,
which also avoids the Paddle/torch DLL-order conflict.
"""

from __future__ import annotations

import re

import cv2
import numpy as np

_paddle_engine = None
_paddle_checked = False

TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def get_paddle_engine():
    """Return a shared PaddleOCR engine, or None when unavailable."""
    global _paddle_engine, _paddle_checked
    if not _paddle_checked:
        _paddle_checked = True
        try:
            from paddleocr import PaddleOCR
            _paddle_engine = PaddleOCR(
                text_detection_model_name=None,
                text_recognition_model_name="PP-OCRv6_small_rec",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                enable_mkldnn=False,
                lang="en",
            )
        except Exception as e:
            _paddle_engine = None
            print(f"[OCR] PaddleOCR unavailable ({type(e).__name__}: {e})")
    return _paddle_engine


def paddle_available() -> bool:
    return get_paddle_engine() is not None


def _digits(text: str) -> str:
    text = (text or "").replace("O", "0").replace("o", "0")
    return re.sub(r"\D", "", text)


def _read_paddle(img_bgr):
    engine = get_paddle_engine()
    if engine is None:
        return ""

    up = cv2.resize(img_bgr, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC)
    try:
        results = engine.predict(up)
    except Exception as e:
        print(f"[OCR] Paddle inference failed: {e}")
        return ""

    chunks = []
    for res in results or []:
        texts = getattr(res, "rec_texts", None)
        if texts is None and hasattr(res, "get"):
            texts = res.get("rec_texts", [])
        if not texts:
            continue
        for text in texts:
            d = _digits(str(text))
            if d:
                chunks.append(d)

    return "".join(chunks)


def _prep_tesseract(img_bgr):
    """White digits -> black on white, removing the coloured bar background."""
    up = cv2.resize(img_bgr, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC)
    b, g, r = cv2.split(up)
    mask = ((b > 190) & (g > 190) & (r > 190)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    out = 255 - mask
    return cv2.copyMakeBorder(out, 20, 20, 20, 20,
                              cv2.BORDER_CONSTANT, value=255)


def _read_tesseract(img_bgr):
    try:
        import pytesseract
    except Exception:
        return ""

    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    prepared = _prep_tesseract(img_bgr)

    best = ""
    for psm in (7, 8, 6, 13):
        try:
            text = pytesseract.image_to_string(
                prepared,
                config=f"--oem 1 --psm {psm} "
                       "-c tessedit_char_whitelist=0123456789",
            )
        except Exception:
            continue
        d = _digits(text)
        if len(d) > len(best):
            best = d
    return best


def read_digits(img_bgr) -> str:
    """Return the digit string in the crop (may be empty)."""
    if img_bgr is None or getattr(img_bgr, "size", 0) == 0:
        return ""

    digits = _read_paddle(img_bgr)
    if digits:
        return digits
    return _read_tesseract(img_bgr)


def read_number(img_bgr, max_value: int = 999_999_999):
    """Return an int, or None when the crop does not contain a valid number."""
    digits = read_digits(img_bgr)
    if not digits:
        return None
    value = int(digits)
    if value > max_value:
        return None
    return value


def read_region(img_bgr, region_xyxy, max_value: int = 999_999_999):
    """Read a number from an (x1, y1, x2, y2) region of a BGR image."""
    if img_bgr is None or getattr(img_bgr, "size", 0) == 0:
        return None
    x1, y1, x2, y2 = region_xyxy
    crop = img_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    return read_number(crop, max_value=max_value)
