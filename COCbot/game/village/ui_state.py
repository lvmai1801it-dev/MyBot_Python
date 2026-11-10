"""Detect and close Shop/army/settings panels that block the home screen.

A wrong tap can leave the bot inside the Shop or another overlay. Every later
step then fails because it is not looking at the village. This module finds the
close button (X) of known panels and closes it; if only the Shop is detected it
falls back to the Android BACK key.
"""

from __future__ import annotations

import os
import subprocess
import time

import cv2

from COCbot.app.paths import TEMPLATE_DIR
from COCbot.platform.adb_config import ADB_BIN

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
CONFIRM_THRESHOLD = 0.72

CLOSE_TEMPLATES = [
    "close_button_shop.png",
    "close_button_layout.png",
    "close_button_profile.png",
    "close_button_setting.png",
    "close_button_shield.png",
]
SHOP_TEMPLATE = "shop_new.png"


def _host():
    from COCbot.platform.adb_utils import _get_target_device
    return _get_target_device()


def _key_back(host):
    subprocess.run(
        [ADB_BIN, "-s", host, "shell", "input", "keyevent", "4"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )


def _tap(host, x, y):
    subprocess.run(
        [ADB_BIN, "-s", host, "shell", "input", "tap", str(x), str(y)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )


def close_open_panels(max_rounds: int = 2) -> bool:
    """Close known overlays. Returns True when something was closed."""
    host = _host()
    if not host:
        return False

    from COCbot.vision.capture import take_screenshot
    from COCbot.platform.unicode import imread_unicode
    from COCbot.platform.tap_guard import blocked

    closed = False
    for _ in range(max(1, max_rounds)):
        shot = take_screenshot("ui_state.png")
        img = imread_unicode(shot, cv2.IMREAD_GRAYSCALE)
        if img is None or img.size == 0:
            break

        best = None  # (score, name, template, location)
        for name in CLOSE_TEMPLATES:
            path = os.path.join(str(TEMPLATE_DIR), name)
            tpl = imread_unicode(path, cv2.IMREAD_GRAYSCALE)
            if tpl is None or tpl.size == 0:
                continue
            if tpl.shape[0] > img.shape[0] or tpl.shape[1] > img.shape[1]:
                continue
            res = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
            _, score, _, loc = cv2.minMaxLoc(res)
            if score >= CONFIRM_THRESHOLD and (best is None or score > best[0]):
                best = (score, name, tpl, loc)

        if best is None:
            # Explicit Shop-panel check: BACK is safer than guessing a button.
            path = os.path.join(str(TEMPLATE_DIR), SHOP_TEMPLATE)
            tpl = imread_unicode(path, cv2.IMREAD_GRAYSCALE)
            if tpl is not None and tpl.size and tpl.shape[0] <= img.shape[0] and tpl.shape[1] <= img.shape[1]:
                res = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
                _, score, _, _ = cv2.minMaxLoc(res)
                if score >= CONFIRM_THRESHOLD:
                    print(f"[UI] Shop panel detected (score={score:.2f}) -> BACK")
                    _key_back(host)
                    time.sleep(1.0)
                    closed = True
                    continue
            break

        score, name, tpl, loc = best
        cx = loc[0] + tpl.shape[1] // 2
        cy = loc[1] + tpl.shape[0] // 2
        print(f"[UI] Panel open ({name}, score={score:.2f}) -> close")

        if blocked(cx, cy, "close_panel"):
            _key_back(host)
        else:
            _tap(host, cx, cy)
        time.sleep(1.0)
        closed = True

    return closed
