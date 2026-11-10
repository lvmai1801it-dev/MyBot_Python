# ==== COCbot/game/account/ready_villages.py ====
"""
ready_villages.py - Supercell ID account switcher
"""

import glob
import os
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

import COCbot.app.paths
from COCbot.app.coords import (
    RV_BACK_TAP,
    RV_CLOSE_SETTINGS_TAP,
    RV_LOADED_ROI,
    RV_SETTINGS_TAP,
    RV_SWITCH_BUTTON_ROI,
    RV_VILLAGE_COORDS,
)
from COCbot.platform.adb_config import ADB_BIN
from COCbot.platform.ahk import run_ahk
from COCbot.platform.unicode import imread_unicode
from COCbot.vision.capture import take_screenshot

DEBUG = True


def dbg(msg: str):
    if DEBUG:
        ts = time.strftime("%H:%M:%S")
        print(f"[D] {ts}  {msg}")


TEMPLATE_DIR = COCbot.app.paths.TEMPLATE_PATH

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

LOADED_ROI = RV_LOADED_ROI
LOADED_TPL = os.path.join(TEMPLATE_DIR, "is_account_loaded.png")

SWITCH_BUTTON_ROI = RV_SWITCH_BUTTON_ROI

MEMU = "127.0.0.1:21503"
BLUESTACKS = "127.0.0.1:5555"

VILLAGE_COORDS = RV_VILLAGE_COORDS


def _get_host():
    from COCbot.app import state as main

    return getattr(main, "host", None)


def tap(coord: tuple[int, int]) -> None:
    host = _get_host()
    x, y = coord
    subprocess.run(
        [ADB_BIN, "-s", host, "shell", "input", "tap", str(x), str(y)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )


def match_one(
    template_name: str,
    screenshot: np.ndarray,
    roi: tuple[int, int, int, int],
    thresh: float = 0.9,
) -> tuple[int, int] | None:
    path = os.path.join(TEMPLATE_DIR, template_name)
    tmpl = imread_unicode(path, cv2.IMREAD_COLOR)
    if tmpl is None:
        dbg(f"! Failed to load template: {path}")
        return None

    x1, y1, x2, y2 = roi
    crop = screenshot[y1:y2, x1:x2]

    res = cv2.matchTemplate(crop, tmpl, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    vis = screenshot.copy()
    h, w = tmpl.shape[:2]
    top_left = (x1 + max_loc[0], y1 + max_loc[1])
    bottom_right = (top_left[0] + w, top_left[1] + h)
    cv2.rectangle(vis, top_left, bottom_right, (0, 255), 3)

    if max_val >= thresh:
        cx = x1 + max_loc[0] + w // 2
        cy = y1 + max_loc[1] + h // 2
        return (cx, cy)

    return None


def clear_memu_screenshots():
    pics_dir = Path.home() / "Pictures" / "MEmu Photo" / "Screenshots"
    if not pics_dir.is_dir():
        print(
            f"[WARN] No MEmu screenshot folder found at {pics_dir!r}, nothing to delete."
        )
        return

    pattern = str(pics_dir / "Screenshot_*.png")
    files = glob.glob(pattern)
    if not files:
        print(f"[INFO] No screenshots to delete in {pics_dir!r}.")
        return

    deleted = 0
    for fp in files:
        try:
            os.remove(fp)
            deleted += 1
        except OSError as e:
            print(f"[ERROR] Could not delete {fp}: {e}")


def get_latest_memu_screenshot(retries: int = 3, delay: float = 1.0) -> Path:
    dirs = [
        Path.home() / "Pictures" / "MEmu Photo" / "Screenshots",
        Path.home() / "Pictures" / "MEmu" / "Screenshots",
    ]

    for attempt in range(1, retries + 1):
        for pics_dir in dirs:
            if not pics_dir.is_dir():
                continue

            files = list(pics_dir.glob("Screenshot_*.png"))
            if not files:
                continue

            return max(files, key=lambda f: f.stat().st_mtime)

        run_ahk("bypass_screen.ahk")
        time.sleep(delay)

    tried = "\n".join(str(d) for d in dirs)
    raise FileNotFoundError(
        f"No screenshots found after {retries} attempts in:\n{tried}"
    )


def switch_to_village(idx: int):
    dbg(f"switch_to_village({idx})")
    time.sleep(2)

    tap(RV_SETTINGS_TAP)
    time.sleep(1)

    tmp = take_screenshot()
    scr = imread_unicode(tmp)
    sw = match_one("switch_button.png", scr, SWITCH_BUTTON_ROI)
    if not sw:
        print("[WARN] Switch-Account button not found; aborting switch_to_village")
        tap(RV_CLOSE_SETTINGS_TAP)
        return

    tap(sw)
    time.sleep(2)

    if _get_host() == MEMU:
        run_ahk("bypass_screen.ahk")
        time.sleep(1)
        shot = get_latest_memu_screenshot()
    else:
        shot = take_screenshot()

    img = imread_unicode(shot)
    if img is None:
        print("[ERROR] Could not load screenshot in switch_to_village")
        tap(RV_BACK_TAP)
        time.sleep(1)
        tap(RV_CLOSE_SETTINGS_TAP)
        return

    for attempt in range(2):
        roi_color = img[LOADED_ROI[1] : LOADED_ROI[3], LOADED_ROI[0] : LOADED_ROI[2]]
        roi_gray = cv2.cvtColor(roi_color, cv2.COLOR_BGR2GRAY)

        tpl = imread_unicode(LOADED_TPL, cv2.IMREAD_GRAYSCALE)
        if roi_gray is None or tpl is None:
            raise RuntimeError("Failed to load ROI or template for switch_to_village")

        res = cv2.matchTemplate(roi_gray, tpl, cv2.TM_CCOEFF_NORMED)
        _, maxv, _, _ = cv2.minMaxLoc(res)

        if maxv >= 0.85:
            dbg("Accounts list loaded")
            break

        if attempt == 0:
            dbg("Accounts not loaded yet; retrying in 5s")
            time.sleep(5)
            if _get_host() == MEMU:
                run_ahk("bypass_screen.ahk")
                time.sleep(1)
                shot = get_latest_memu_screenshot()
            else:
                shot = take_screenshot()
            img = imread_unicode(shot)
        else:
            print("[WARN] Accounts list failed to load → closing UI")
            tap(RV_BACK_TAP)
            time.sleep(0.5)
            tap(RV_CLOSE_SETTINGS_TAP)
            time.sleep(0.5)
            return

    print("Loading. . .")
    time.sleep(5)
    coord = VILLAGE_COORDS.get(idx)
    if not coord:
        print(f"[ERROR] Invalid village index: {idx}")
    else:
        tap(coord)
        time.sleep(1)

    dbg(f"Switched to Village_{idx}")

    if _get_host() == MEMU:
        clear_memu_screenshots()
