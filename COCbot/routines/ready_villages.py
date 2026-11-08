# ==== ready_villages.py ====
"""
ready_villages.py — Supercell ID multi-village switcher
"""
import os
import sys
import time
import cv2
import subprocess
import glob
import threading
from typing import Tuple, Optional
import numpy as np
import json

import core.paths

from PyQt5.QtCore import QObject, pyqtSignal, QEventLoop
from utils.screenshot_utils import take_screenshot
from COCbot.emulator.adb_config import ADB_BIN
from utils.ocr_reader import reader
from utils.ahk_utils import run_ahk
from pathlib import Path
from utils.unicode import imread_unicode
from core.coords import (
    RV_LOADED_ROI, RV_FOURTH_ROI, RV_SWITCH_BUTTON_ROI,
    RV_CROP_RECTS, RV_VILLAGE_COORDS, RV_ACCOUNT_DETECT_ROIS,
    RV_SETTINGS_TAP, RV_CLOSE_SETTINGS_TAP, RV_BACK_TAP,
)

DEBUG = True


def dbg(msg: str):
    if DEBUG:
        ts = time.strftime('%H:%M:%S')
        print(f'[D] {ts}  {msg}')


TEMPLATE_DIR = core.paths.TEMPLATE_PATH
PROFILES_DIR = core.paths.PROFILES_PATH

PROFILES_DIR.mkdir(exist_ok=True, parents=True)
CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

LOADED_ROI = RV_LOADED_ROI
LOADED_TPL = os.path.join(TEMPLATE_DIR, 'is_account_loaded.png')

FOURTH_ROI = RV_FOURTH_ROI
SWITCH_BUTTON_ROI = RV_SWITCH_BUTTON_ROI

MEMU = '127.0.0.1:21503'
BLUESTACKS = '127.0.0.1:5555'

CROP_RECTS = RV_CROP_RECTS
VILLAGE_COORDS = RV_VILLAGE_COORDS
ACCOUNT_DETECT_ROIS = RV_ACCOUNT_DETECT_ROIS


def _get_host():
    import main
    return getattr(main, 'host', None)


def tap(coord: Tuple[int, int]) -> None:
    host = _get_host()
    x, y = coord
    subprocess.run(
        [ADB_BIN, '-s', host, 'shell', 'input', 'tap', str(x), str(y)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )


def match_one(
    template_name: str,
    screenshot: np.ndarray,
    roi: Tuple[int, int, int, int],
    thresh: float = 0.9,
) -> Optional[Tuple[int, int]]:
    path = os.path.join(TEMPLATE_DIR, template_name)
    tmpl = imread_unicode(path, cv2.IMREAD_COLOR)
    if tmpl is None:
        dbg(f'! Failed to load template: {path}')
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
    pics_dir = Path.home() / 'Pictures' / 'MEmu Photo' / 'Screenshots'
    if not pics_dir.is_dir():
        print(f'[WARN] No MEmu screenshot folder found at {pics_dir!r}, nothing to delete.')
        return

    pattern = str(pics_dir / 'Screenshot_*.png')
    files = glob.glob(pattern)
    if not files:
        print(f'[INFO] No screenshots to delete in {pics_dir!r}.')
        return

    deleted = 0
    for fp in files:
        try:
            os.remove(fp)
            deleted += 1
        except OSError as e:
            print(f'[ERROR] Could not delete {fp}: {e}')


def get_latest_memu_screenshot(retries: int = 3, delay: float = 1.0) -> Path:
    dirs = [
        Path.home() / 'Pictures' / 'MEmu Photo' / 'Screenshots',
        Path.home() / 'Pictures' / 'MEmu' / 'Screenshots',
    ]

    for attempt in range(1, retries + 1):
        for pics_dir in dirs:
            if not pics_dir.is_dir():
                continue

            files = list(pics_dir.glob('Screenshot_*.png'))
            if not files:
                continue

            return max(files, key=lambda f: f.stat().st_mtime)

        run_ahk('bypass_screen.ahk')
        time.sleep(delay)

    tried = '\n'.join(str(d) for d in dirs)
    raise FileNotFoundError(
        f'No screenshots found after {retries} attempts in:\n{tried}'
    )


def save_village_config(idx: int, cfg: dict):
    PROFILES_DIR.mkdir(exist_ok=True)

    json_path = PROFILES_DIR / f'Village_{idx}.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)
    print(f'[D] Saved config → {json_path}')

    img_path = PROFILES_DIR / f'account_{idx}.png'
    take_screenshot(output_path=str(img_path))
    print(f'[D] Captured image   → {img_path}')


def add_village(count: int):
    dbg('Opening Settings for add_village')
    tap(RV_SETTINGS_TAP)
    time.sleep(1)

    tmp = take_screenshot()
    scr0 = imread_unicode(tmp)

    sw_btn = match_one('switch_button.png', scr0, SWITCH_BUTTON_ROI)
    if not sw_btn:
        print('[WARN] Could not find Switch-Account button.')
        tap(RV_CLOSE_SETTINGS_TAP)
        return

    dbg('Tapping Switch-Account')
    tap(sw_btn)
    time.sleep(2)

    if _get_host() == MEMU:
        run_ahk('bypass_screen.ahk')
        time.sleep(1)
        shot_path = get_latest_memu_screenshot()
    else:
        shot_path = take_screenshot()

    scr = imread_unicode(shot_path)
    if scr is None:
        print('[ERROR] Failed to load screenshot for add_village.')
        return

    total_avail = None
    for (x1, y1, x2, y2), num in ACCOUNT_DETECT_ROIS:
        if match_one('account_counter.png', scr, (x1, y1, x2, y2)):
            total_avail = num
            break
    if total_avail is None:
        total_avail = 4 if match_one('account_counter_2.png', scr, FOURTH_ROI) else 5

    print(f'[INFO] Device has {total_avail} Supercell IDs available')

    existing = len(glob.glob(str(PROFILES_DIR / 'account_*.png')))
    max_new = min(count, total_avail - existing, 5 - existing)
    if max_new <= 0:
        print(f'[INFO] No new villages to add (existing={existing}, avail={total_avail})')
        return

    for idx in range(existing + 1, existing + max_new + 1):
        x1, y1, x2, y2 = CROP_RECTS[idx - 1]
        crop = scr[y1:y2, x1:x2]
        out = PROFILES_DIR / f'account_{idx}.png'
        cv2.imwrite(str(out), crop)
        dbg(f'Saved new account_{idx}.png')

    if _get_host() == MEMU:
        clear_memu_screenshots()


def switch_to_village(idx: int):
    dbg(f'switch_to_village({idx})')
    time.sleep(2)

    tap(RV_SETTINGS_TAP)
    time.sleep(1)

    tmp = take_screenshot()
    scr = imread_unicode(tmp)
    sw = match_one('switch_button.png', scr, SWITCH_BUTTON_ROI)
    if not sw:
        print('[WARN] Switch-Account button not found; aborting switch_to_village')
        tap(RV_CLOSE_SETTINGS_TAP)
        return

    tap(sw)
    time.sleep(2)

    if _get_host() == MEMU:
        run_ahk('bypass_screen.ahk')
        time.sleep(1)
        shot = get_latest_memu_screenshot()
    else:
        shot = take_screenshot()

    img = imread_unicode(shot)
    if img is None:
        print('[ERROR] Could not load screenshot in switch_to_village')
        tap(RV_BACK_TAP)
        time.sleep(1)
        tap(RV_CLOSE_SETTINGS_TAP)
        return

    for attempt in range(2):
        roi_color = img[LOADED_ROI[1]:LOADED_ROI[3], LOADED_ROI[0]:LOADED_ROI[2]]
        roi_gray = cv2.cvtColor(roi_color, cv2.COLOR_BGR2GRAY)

        tpl = imread_unicode(LOADED_TPL, cv2.IMREAD_GRAYSCALE)
        if roi_gray is None or tpl is None:
            raise RuntimeError('Failed to load ROI or template for switch_to_village')

        res = cv2.matchTemplate(roi_gray, tpl, cv2.TM_CCOEFF_NORMED)
        _, maxv, _, _ = cv2.minMaxLoc(res)

        if maxv >= 0.85:
            dbg('Accounts list loaded')
            break

        if attempt == 0:
            dbg('Accounts not loaded yet; retrying in 5s')
            time.sleep(5)
            if _get_host() == MEMU:
                run_ahk('bypass_screen.ahk')
                time.sleep(1)
                shot = get_latest_memu_screenshot()
            else:
                shot = take_screenshot()
            img = imread_unicode(shot)
        else:
            print('[WARN] Accounts list failed to load → closing UI')
            tap(RV_BACK_TAP)
            time.sleep(0.5)
            tap(RV_CLOSE_SETTINGS_TAP)
            time.sleep(0.5)
            return

    print('Loading. . .')
    time.sleep(5)
    coord = VILLAGE_COORDS.get(idx)
    if not coord:
        print(f'[ERROR] Invalid village index: {idx}')
    else:
        tap(coord)
        time.sleep(1)

    dbg(f'Switched to Village_{idx}')

    if _get_host() == MEMU:
        clear_memu_screenshots()


def prepare_accounts(start: int = 1, count: int = None) -> int:
    dbg('prepare_accounts: opening Switch-Account UI')
    tap(RV_SETTINGS_TAP)
    time.sleep(1)
    shot = take_screenshot()
    img = imread_unicode(shot)
    btn = match_one('switch_button.png', img, SWITCH_BUTTON_ROI)
    if not btn:
        raise RuntimeError('Switch-Account button not found')
    tap(btn)
    time.sleep(2)

    if _get_host() == MEMU:
        run_ahk('bypass_screen.ahk')
        time.sleep(1)
        shot = get_latest_memu_screenshot()
        img = imread_unicode(shot)
        if img is None:
            raise RuntimeError('Failed to load screenshot after bypass')
    else:
        shot = take_screenshot()
        img = imread_unicode(shot)
        if img is None:
            raise RuntimeError('Failed to load screenshot on BlueStacks')

    detected_total = None
    for (x1, y1, x2, y2), n in ACCOUNT_DETECT_ROIS:
        if match_one('account_counter.png', img, (x1, y1, x2, y2)):
            detected_total = n
            break
    if detected_total is None:
        detected_total = 4 if match_one('account_counter_2.png', img, FOURTH_ROI) else 5

    print(f'[INFO] prepare_accounts: detected {detected_total} profiles')

    accounts_file = PROFILES_DIR / 'accounts.txt'
    with open(accounts_file, 'w') as af:
        af.write(str(detected_total))

    if detected_total == 1:
        print('[WARN] Only one Supercell ID detected; multi-village is not available.')
        time.sleep(6)
        tap(RV_BACK_TAP)
        time.sleep(0.5)
        tap(RV_CLOSE_SETTINGS_TAP)
        time.sleep(0.5)
        return detected_total

    start_idx = max(1, start)
    if count is None:
        end_idx = detected_total
    else:
        end_idx = min(start_idx + count - 1, detected_total)

    for idx in range(start_idx, end_idx + 1):
        x1, y1, x2, y2 = CROP_RECTS[idx - 1]
        crop = img[y1:y2, x1:x2]
        out = PROFILES_DIR / f'account_{idx}.png'
        success, buf = cv2.imencode('.png', crop)
        if not success:
            raise IOError(f'prepare_accounts: imencode failed for {out}')
        out.write_bytes(buf.tobytes())
        dbg(f'prepare_accounts: saved {out}')

    if _get_host() == MEMU:
        clear_memu_screenshots()

    return detected_total


if __name__ == '__main__':
    prepare_accounts()
