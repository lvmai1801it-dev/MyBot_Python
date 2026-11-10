"""Device/tap helpers for the attack pipeline.

Split out from the old COCbot.attack.py monolith so redline/planner/dropper can be
tested independently.
"""

import re
import time
import random

import cv2
import numpy as np

try:
    import uiautomator2 as u2
except ImportError:
    u2 = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

from COCbot.app import state
from COCbot.platform.adb_utils import _get_target_device, tap as adb_tap


_device = None
_device_initialized = False


def init_device(host: str = None):
    """Initialize uiautomator2 once; fall back to adb tap."""
    global _device, _device_initialized
    if _device_initialized:
        return _device
    _device_initialized = True
    if not u2:
        return None
    try:
        target_host = host or _get_target_device()
    except Exception:
        target_host = getattr(state, 'host', None)
    if not target_host:
        return None
    try:
        print(f"[ATTACK] Khoi tao uiautomator2 toi {target_host}...")
        _device = u2.connect(target_host)
        print("[ATTACK] uiautomator2 san sang!")
    except Exception as e:
        print(f"[ATTACK] uiautomator2 loi ({e}), dung adb_tap fallback.")
        _device = None
    return _device


def get_device():
    global _device, _device_initialized
    if not _device_initialized:
        return init_device()
    return _device


def reset_device():
    global _device, _device_initialized
    _device = None
    _device_initialized = False


def tap(x, y, delay=0.02):
    """Tap via uiautomator2 when available, else adb_tap."""
    global _device
    x, y = int(x), int(y)
    if _device is not None:
        try:
            _device.click(x, y)
            if delay:
                time.sleep(delay)
            return True
        except Exception:
            pass
    try:
        adb_tap(x, y)
        if delay:
            time.sleep(delay)
        return True
    except Exception as e:
        print(f"[TAP ERROR] {e}")
        return False


def set_sleep(sleep_type):
    if sleep_type == 0:
        return random.randint(1, 10) * 0.01
    return random.randint(1, 10) * 0.1


def select_drop_troop(slot_idx):
    """Click a troop/hero/spell card in the bottom attack bar."""
    if slot_idx < 0 or slot_idx > 10:
        return False
    x = 30 + slot_idx * 72 + 35
    y = 682
    tap(x, y)
    time.sleep(0.15)
    return True


def check_slot_has_troops(img, slot_idx):
    """Return (has_troops, remaining_count) for one attack-bar slot."""
    if img is None or img.size == 0:
        return False, 0

    slot_x = 30 + slot_idx * 72
    badge_roi = img[638:658, slot_x + 8:slot_x + 62]
    if badge_roi is None or badge_roi.size == 0:
        return False, 0

    mean_b, _mean_g, mean_r = cv2.mean(badge_roi)[:3]
    has_badge = (mean_b >= 85 and mean_b > mean_r + 15)
    if not has_badge:
        return False, 0

    rem = 0
    if pytesseract:
        try:
            white_mask = ((badge_roi[:, :, 0] > 180) &
                          (badge_roi[:, :, 1] > 180) &
                          (badge_roi[:, :, 2] > 180))
            bin_img = np.zeros(badge_roi.shape[:2], dtype=np.uint8)
            bin_img[white_mask] = 255
            inv = 255 - bin_img
            padded = cv2.copyMakeBorder(inv, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=255)
            padded = cv2.resize(padded, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
            txt = pytesseract.image_to_string(
                padded, config="--psm 7 -c tessedit_char_whitelist=xX0123456789"
            ).strip()
            digits = re.sub(r'\D', '', txt)
            if digits:
                rem = int(digits)
        except Exception:
            pass

    return True, rem if rem > 0 else 5
