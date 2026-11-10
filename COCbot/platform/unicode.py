# ==== COCbot/platform/unicode.py ====
"""
Unicode-safe image loading for OpenCV on Windows.
Returns None if file does not exist, is empty, or decoding fails,
matching cv2.imread's standard failure behavior.
"""
import os
import time
from pathlib import Path
import cv2
import numpy as np


def imread_unicode(path, flags=cv2.IMREAD_COLOR, retries=3, delay=0.15):
    if path is None:
        return None
    if isinstance(path, np.ndarray):
        if flags == cv2.IMREAD_GRAYSCALE and path.ndim == 3:
            return cv2.cvtColor(path, cv2.COLOR_BGR2GRAY)
        if flags == cv2.IMREAD_COLOR and path.ndim == 2:
            return cv2.cvtColor(path, cv2.COLOR_GRAY2BGR)
        return path
    try:
        p = Path(path)
    except Exception:
        return None

    if not p.is_file():
        return None

    for attempt in range(retries + 1):
        try:
            size = p.stat().st_size
            if size <= 0:
                return None

            data = p.read_bytes()
            if not data:
                return None

            arr = np.frombuffer(data, dtype=np.uint8)
            img = cv2.imdecode(arr, flags)

            if img is not None and img.size > 0:
                return img

        except Exception:
            pass

        if attempt < retries:
            time.sleep(delay)

    return None
