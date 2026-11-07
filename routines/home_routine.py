# ==== home_routine.py ====
import os
import sys
import cv2
import subprocess
import time
import numpy as np
import math
import re
from skimage import feature
from pathlib import Path

import core.paths
from utils.ocr_reader import reader
from utils.screenshot_utils import take_screenshot
from emulators.adb_config import ADB_BIN
from utils.unicode import imread_unicode
from core.coords import (
    HR_GOLD_REGION, HR_ELIXIR_REGION, HR_VALIDATE_REGION, HR_POPUP_REGION,
    HR_DISMISS_COORD, HR_GOLD_UPGRADE, HR_ELIXIR_UPGRADE, HR_CONFIRM_UPGRADE,
    HR_WALL_ROI, HR_HOME_TAP, HR_SWIPE_START, HR_SWIPE_END,
    HR_VALIDATION_ROI, HR_SAFE_TAP, HR_CLOSE_TAP,
    HR_RETRY_SWIPE_START, HR_RETRY_SWIPE_END,
)

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

BASE_DIR = str(core.paths.SRC_DIR)
ROOT = BASE_DIR
TEMPLATE_DIR = str(core.paths.TEMPLATE_DIR)

CLOSE_TEMPLATES = [
    os.path.join(TEMPLATE_DIR, fn)
    for fn in (
        'close_button_layout.png',
        'close_button_profile.png',
        'close_button_setting.png',
        'close_button_shield.png',
        'close_button_shop.png',
    )
]

CLOSE_BTN_THRESH = 0.75

GOLD_REGION = HR_GOLD_REGION
ELIXIR_REGION = HR_ELIXIR_REGION
GOLD_THRESHOLD = 5000000
ELIXIR_THRESHOLD = 5000000

BORDER_TOP, BORDER_BOTTOM = (20, 20)
BORDER_LEFT, BORDER_RIGHT = (30, 30)
UPSCALE = 2

VALIDATE_REGION = HR_VALIDATE_REGION
POPUP_REGION = HR_POPUP_REGION
DISMISS_COORD = HR_DISMISS_COORD
GOLD_UPGRADE = HR_GOLD_UPGRADE
ELIXIR_UPGRADE = HR_ELIXIR_UPGRADE
CONFIRM_UPGRADE = HR_CONFIRM_UPGRADE

ANGLE_LO = 35
ANGLE_HI = 55
HOUGH_CFG = dict(
    rho=1,
    theta=np.pi / 180,
    threshold=100,
    minLineLength=60,
    maxLineGap=6,
)
CANNY_THRESH = (50, 150)


def ocr_number(img):
    texts = reader.readtext(img, detail=0)
    combined = (
        ''.join(texts)
        .replace('I', '1')
        .replace('l', '1')
        .replace('O', '0')
    )
    digits = re.sub('[^0-9]', '', combined)
    if digits:
        return int(digits)
    return None


def get_home_resources():
    time.sleep(1)
    take_screenshot(output_path='res.png')

    img = imread_unicode(Path('res.png'))
    h_img, w_img = img.shape[:2]

    x1, y1, x2, y2 = GOLD_REGION
    h, w = (x2 - x1), (y2 - y1)
    gold_raw = img[y1:y1 + h, x1:x1 + w]
    cv2.imwrite('gold_crop_debug.png', gold_raw)

    gold_b = cv2.copyMakeBorder(
        gold_raw,
        BORDER_TOP,
        BORDER_BOTTOM,
        BORDER_LEFT,
        BORDER_RIGHT,
        cv2.BORDER_CONSTANT,
        value=[0, 0, 0],
    )

    gold_proc = cv2.resize(
        gold_b,
        None,
        fx=UPSCALE,
        fy=UPSCALE,
        interpolation=cv2.INTER_CUBIC,
    )

    gold = ocr_number(gold_proc) or 0

    x1, y1, x2, y2 = ELIXIR_REGION
    h, w = (x2 - x1), (y2 - y1)
    elixir_raw = img[y1:y1 + h, x1:x1 + w]
    cv2.imwrite('elixir_crop_debug.png', elixir_raw)

    elixir = ocr_number(elixir_raw) or 0

    print(f'[RESOURCES] Gold={gold}, Elixir={elixir}')
    return gold, elixir


ROI_X0, ROI_Y0, ROI_X1, ROI_Y1 = HR_WALL_ROI
TAP_HOME_X, TAP_HOME_Y = HR_HOME_TAP
SWIPE_START_X, SWIPE_START_Y = HR_SWIPE_START
SWIPE_END_X, SWIPE_END_Y = HR_SWIPE_END
SWIPE_DURATION_MS = 600
THRESHOLD = 0.9


def _get_main():
    import main
    return main


def prepare_wall_search():
    host = _get_main().host

    time.sleep(0.5)
    subprocess.run(
        [ADB_BIN, '-s', host, 'shell', 'input', 'tap',
         str(TAP_HOME_X), str(TAP_HOME_Y)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )
    time.sleep(1)

    for _ in range(6):
        subprocess.run(
            [ADB_BIN, '-s', host, 'shell', 'input', 'swipe',
             str(SWIPE_START_X), str(SWIPE_START_Y),
             str(SWIPE_END_X), str(SWIPE_END_Y),
             str(SWIPE_DURATION_MS)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )

    time.sleep(0.5)


def _match_coords_single(gray_roi, tpl_path, threshold):
    coords = []
    raw = imread_unicode(tpl_path, cv2.IMREAD_UNCHANGED)
    if raw is None:
        return coords

    if raw.ndim == 3 and raw.shape[2] == 4:
        bgr = raw[..., :3]
        alpha = raw[..., 3]
        tpl_gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        mask = (alpha > 0).astype(np.uint8)
    else:
        tpl_gray = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)
        mask = None

    th, tw = tpl_gray.shape
    res = cv2.matchTemplate(gray_roi, tpl_gray, cv2.TM_CCOEFF_NORMED, mask=mask)
    dilated = cv2.dilate(res, np.ones((3, 3), np.uint8))
    ys, xs = np.where((res == dilated) & (res >= threshold))

    for y, x in zip(ys, xs):
        cx = ROI_X0 + x + tw // 2
        cy = ROI_Y0 + y + th // 2
        coords.append((cx, cy))
    return coords


def _dedupe_coords(coords, tol=10):
    out = []
    for cx, cy in coords:
        if any(abs(cx - ox) <= tol and abs(cy - oy) <= tol for ox, oy in out):
            continue
        out.append((cx, cy))
    return out


def find_all_wall_coords(threshold: float = 0.9, max_attempts: int = 7):
    host = _get_main().host
    prepare_wall_search()

    template_names = ['wall.png', 'wall_2.png', 'wall_3.png', 'wall_4.png']
    template_paths = []
    for name in template_names:
        p = os.path.join(TEMPLATE_DIR, name)
        if not os.path.exists(p):
            continue
        template_paths.append(p)

    if not template_paths:
        raise FileNotFoundError(f'No wall templates found in {TEMPLATE_DIR}')

    for attempt in range(max_attempts):
        if attempt > 0:
            subprocess.run(
                [ADB_BIN, '-s', host, 'shell', 'input', 'swipe',
                 str(HR_RETRY_SWIPE_START[0]), str(HR_RETRY_SWIPE_START[1]),
                 str(HR_RETRY_SWIPE_END[0]), str(HR_RETRY_SWIPE_END[1]),
                 str(SWIPE_DURATION_MS)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW,
            )
            time.sleep(0.8)

        shot = take_screenshot(output_path='wall_search.png')
        img = imread_unicode(shot, cv2.IMREAD_COLOR)
        if img is None or img.size == 0:
            raise RuntimeError('Screenshot failed')

        roi_bgr = img[ROI_Y0:ROI_Y1, ROI_X0:ROI_X1]
        if roi_bgr.size == 0:
            raise ValueError('ROI is empty — check ROI bounds')

        roi_gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
        merged = []
        for tpl_path in template_paths:
            merged.extend(_match_coords_single(roi_gray, tpl_path, threshold))

        if not merged:
            continue

        coords = _dedupe_coords(merged, tol=10)
        coords.sort(key=lambda p: (p[1], p[0]))
        return coords

    return []


def validate_wall_tap(wall_level: int) -> bool:
    global GOLD_UPGRADE, ELIXIR_UPGRADE

    host = _get_main().host

    time.sleep(1)
    take_screenshot(output_path='validate.png')

    img = imread_unicode('validate.png', cv2.IMREAD_GRAYSCALE)
    if img is None:
        return False

    best_val = 0
    best_tpl = None
    best_loc = None
    for tpl_path in CLOSE_TEMPLATES:
        tpl = imread_unicode(tpl_path, cv2.IMREAD_GRAYSCALE)
        if tpl is None:
            continue
        res = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val > best_val:
            best_val = max_val
            best_tpl = tpl
            best_loc = max_loc

    if best_val >= CLOSE_BTN_THRESH and best_tpl is not None:
        h, w = best_tpl.shape[:2]
        if not host:
            raise RuntimeError('Emulator host not set for popup dismissal')

        subprocess.run(
            [ADB_BIN, '-s', host, 'shell', 'input', 'tap',
             str(best_loc[0] + w // 2),
             str(best_loc[1] + h // 2)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
            check=True,
        )
        print('[WARN] Pop-up window detected. Dismissing popup…')
        return False

    img_color = imread_unicode('validate.png', cv2.IMREAD_COLOR)
    if img_color is None:
        return False

    x0, y0, x1, y1 = HR_VALIDATION_ROI
    roi_color = img_color[y0:y1, x0:x1]

    tpl_path = os.path.join(
        ROOT, 'walls', str(wall_level), 'Validate_Upgrade', 'verify_wall_level.png'
    )
    tpl_color = imread_unicode(tpl_path, cv2.IMREAD_COLOR)
    if tpl_color is not None:
        res = cv2.matchTemplate(roi_color, tpl_color, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        tpl_h, tpl_w = tpl_color.shape[:2]
        center_x = x0 + max_loc[0] + tpl_w // 2
        GOLD_UPGRADE = (center_x + 175, GOLD_UPGRADE[1])
        ELIXIR_UPGRADE = (center_x + 350, ELIXIR_UPGRADE[1])

        if max_val >= 0.88:
            print(f'[INFO] color template validation passed (score={max_val:.3f})')
            return True
        print(f'[INFO] color template score {max_val:.3f} < 0.88 → falling back to OCR')
    else:
        print(f'[WARN] fallback template not found: {tpl_path} → falling back to OCR')

    crop = img[VALIDATE_REGION[1]:VALIDATE_REGION[3],
               VALIDATE_REGION[0]:VALIDATE_REGION[2]]
    texts = reader.readtext(crop, detail=0)
    lowered = [t.lower() for t in texts]

    keyword = any('wall' in t or 'level' in t for t in lowered)
    level_ok = any(
        (num := re.sub('[^0-9]', '', t)) and num.isdigit() and int(num) == wall_level
        for t in lowered
    )

    if keyword and level_ok:
        return True

    print('[WARN] validation failed → tapping safe coordinate & retrying')
    time.sleep(1)
    return False


def validate_upgrade_window():
    take_screenshot(output_path='popup.png')
    img = imread_unicode('popup.png', cv2.IMREAD_GRAYSCALE)
    if img is None:
        return False

    crop = img[POPUP_REGION[1]:POPUP_REGION[3],
               POPUP_REGION[0]:POPUP_REGION[2]]
    texts = reader.readtext(crop, detail=0)
    lowered = [t.lower() for t in texts]
    return any('upgrade' in t for t in lowered)


def upgrade_wall(resource, wall_level):
    global GOLD_UPGRADE, ELIXIR_UPGRADE

    print(f'Scanning for wall level: {wall_level}. . .')
    m = _get_main()
    host = m.host
    tried_coords = []
    valid_coord = None
    attempts = 0

    while attempts < 3:
        all_coords = find_all_wall_coords()

        coords = [
            (cx, cy) for cx, cy in all_coords
            if not any(abs(cy - ty) <= 20 for _, ty in tried_coords)
        ]

        if not coords:
            print(f'[WARN] Tried all nearby positions but none validated. Skipping {resource}.')
            subprocess.run(
                [ADB_BIN, '-s', host, 'shell', 'input', 'tap',
                 str(HR_SAFE_TAP[0]), str(HR_SAFE_TAP[1])],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW,
            )
            return False

        try:
            if m.wall_save:
                cx, cy = coords[m._saved_wall_offset]
            else:
                cx, cy = coords[-1 - attempts]
        except IndexError:
            print(f'[WARN] Not enough coords ({len(coords)}) for attempt {attempts}.')
            return False

        subprocess.run(
            [ADB_BIN, '-s', host, 'shell', 'input', 'tap', str(cx), str(cy)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        time.sleep(1)
        subprocess.run(
            [ADB_BIN, '-s', host, 'shell', 'input', 'tap',
             str(TAP_HOME_X), str(TAP_HOME_Y)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )

        if validate_wall_tap(wall_level):
            valid_coord = (cx, cy)
            if not m.wall_save:
                m._saved_wall_offset = -1 - attempts
                m.wall_save = True
            break
        else:
            subprocess.run(
                [ADB_BIN, '-s', host, 'shell', 'input', 'tap',
                 str(DISMISS_COORD[0]), str(DISMISS_COORD[1])],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW,
            )
            attempts += 1

    if valid_coord is None:
        print(f'[WARN] No valid wall after {attempts} attempts. Skipping {resource}.')
        return False

    x, y = GOLD_UPGRADE if resource == 'gold' else ELIXIR_UPGRADE
    subprocess.run(
        [ADB_BIN, '-s', host, 'shell', 'input', 'tap', str(x), str(y)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )
    time.sleep(1)

    if not validate_upgrade_window():
        print('[WARN] Upgrade popup not detected. Aborting upgrade.')
        return False

    subprocess.run(
        [ADB_BIN, '-s', host, 'shell', 'input', 'tap',
         str(CONFIRM_UPGRADE[0]), str(CONFIRM_UPGRADE[1])],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )
    subprocess.run(
        [ADB_BIN, '-s', host, 'shell', 'input', 'tap',
         str(HR_CLOSE_TAP[0]), str(HR_CLOSE_TAP[1])],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )

    print(f'[OK] Wall upgraded using {resource}.')
    time.sleep(1)
    return True


def handle_home_resources(wall_level, wall_gold_threshold, wall_elixir_threshold):
    gold, elixir = get_home_resources()

    if gold >= wall_gold_threshold:
        upgrade_wall('gold', wall_level)

    if elixir >= wall_elixir_threshold:
        upgrade_wall('elixir', wall_level)


if __name__ == '__main__':
    handle_home_resources(
        wall_level=17,
        wall_gold_threshold=5000000,
        wall_elixir_threshold=5000000,
    )
