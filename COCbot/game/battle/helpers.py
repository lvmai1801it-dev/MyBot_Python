# ==== COCbot/game/battle/helpers.py ====
import os
import time
from pathlib import Path

import cv2

import COCbot.app.paths  # noqa: F401
from COCbot.app import state
from COCbot.app.config import (
    BATTLE_KEYWORDS,
    END_BATTLE_TEMPLATE,
    MAX_WAIT_BATTLE,
    NEXT_BTN_TEMPLATE,
    NEXT_THRESH,
    TEMPLATE_DIR,
    TEMPLATE_FILES,
    THRESHOLD,
)
from COCbot.app.coords import (
    ATTACK_CONFIRM_TAP,
    BATTLE_BUTTON_TAP,
    BATTLE_ROI,
    FIND_MATCH_TAP,
    GAIN_DE_L,
    GAIN_DE_R,
    GAIN_ELIXIR_L,
    GAIN_ELIXIR_R,
    GAIN_GOLD_L,
    GAIN_GOLD_R,
    HAMMER_REGION,
    NEXT_BTN_REGION,
    SCOUT_SCREEN_ROI,
    STAR1_ROI,
    STAR2_ROI,
    STAR3_ROI,
    TREASURE_HOME_TAP,
    TREASURE_TAP,
)
from COCbot.game.account.boot_recovery import boot_recovery
from COCbot.platform.adb_utils import tap
from COCbot.platform.unicode import imread_unicode
from COCbot.vision.capture import take_screenshot
from COCbot.vision.ocr import reader
from COCbot.vision.templates import _match_template

BATTLE_X1, BATTLE_Y1, BATTLE_X2, BATTLE_Y2 = BATTLE_ROI


def search_attack():
    print("[SEARCH] Bước 1: Bấm nút Attack! (mở bảng)...")
    tap(BATTLE_BUTTON_TAP[0], BATTLE_BUTTON_TAP[1])
    time.sleep(1.0)

    print("[SEARCH] Bước 2: Bấm Find a Match...")
    tap(FIND_MATCH_TAP[0], FIND_MATCH_TAP[1])
    time.sleep(1.0)

    print("[SEARCH] Bước 3: Bấm Attack Confirm (Bắt đầu quét mây)...")
    tap(ATTACK_CONFIRM_TAP[0], ATTACK_CONFIRM_TAP[1])


def find_next_button():
    """Locate the scout-screen Next button. Returns (x, y, score) or None.

    Using the template center avoids tapping the hard-coded coordinate when the
    UI is not where we think it is (which can open the Shop on the home screen).
    """
    screenshot_file = take_screenshot(output_path='is_next_button.png')
    img = imread_unicode(screenshot_file)
    if img is None:
        return None

    x1, y1, x2, y2 = NEXT_BTN_REGION
    roi = img[y1:y2, x1:x2]
    if roi.size == 0:
        return None

    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    tpl = imread_unicode(NEXT_BTN_TEMPLATE, cv2.IMREAD_GRAYSCALE)
    if tpl is None:
        return None
    if gray_roi.shape[0] < tpl.shape[0] or gray_roi.shape[1] < tpl.shape[1]:
        return None

    res = cv2.matchTemplate(gray_roi, tpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    if max_val < NEXT_THRESH:
        return None

    th, tw = tpl.shape[:2]
    return (x1 + max_loc[0] + tw // 2, y1 + max_loc[1] + th // 2, max_val)


def search_next():
    found = find_next_button()
    if not found:
        print("[SEARCH] Next button not found - skip tap (avoid wrong UI click)")
        return False
    tx, ty, score = found
    print(f"[SEARCH] Next button found at ({tx}, {ty}) score={score:.2f}")
    tap(tx, ty)
    time.sleep(1.5)
    return True


def connection_popup_visible() -> bool:
    shot_path = take_screenshot(output_path='conn.png')
    if shot_path is None:
        return False

    img = imread_unicode(shot_path, cv2.IMREAD_GRAYSCALE)
    if img is None or img.size == 0:
        print('⚠️  connection_popup: screenshot rỗng')
        return False

    for tmpl_name in TEMPLATE_FILES:
        tpl_path = os.path.join(TEMPLATE_DIR, tmpl_name)
        tpl = imread_unicode(tpl_path, cv2.IMREAD_GRAYSCALE)
        if tpl is None or tpl.size == 0:
            print(f'❌ Missing template: {tpl_path}')
            continue

        if tpl.shape[0] > img.shape[0] or tpl.shape[1] > img.shape[1]:
            print(f'⚠️  {tmpl_name} {tpl.shape} > img {img.shape} → cần chụp lại template trên 860×732!')
            continue

        res = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        if max_val >= THRESHOLD:
            print(f'[OK] Detected "{tmpl_name}" (score={max_val:.2f})')
            return True
    return False


def wait_for_scout_screen(timeout=20, interval=2, threshold=0.7) -> bool:
    print('[WAIT] Scouting UI loading…')
    start = time.time()

    tpl = imread_unicode(END_BATTLE_TEMPLATE, cv2.IMREAD_GRAYSCALE)
    if tpl is None:
        print("❌ Lỗi: Không thể đọc file template END_BATTLE_TEMPLATE")
        return False

    tpl_h, tpl_w = tpl.shape[:2]
    x1, y1, x2, y2 = SCOUT_SCREEN_ROI
    attempt = 0

    while time.time() - start < timeout:
        if state.stop_event.is_set():
            print('[STOP] scout wait aborted')
            return False
        attempt += 1
        time.sleep(1.5)
        shot = take_screenshot('scout.png')
        if shot is None:
            print('❌ Screenshot failed.')
            time.sleep(interval)
            continue

        img = imread_unicode(shot)
        if img is None:
            print("❌ Could not load scout screenshot")
            time.sleep(interval)
            continue

        roi = img[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        if gray.shape[0] < tpl_h or gray.shape[1] < tpl_w:
            print(f"  ⚠️ ROI ({gray.shape}) nhỏ hơn Template ({tpl_h}x{tpl_w})")
            continue

        res = cv2.matchTemplate(gray, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)

        print(f"  [Lần {attempt}] Match Score: {max_val:.2f}")

        if max_val >= threshold:
            print('[OK] Scouting UI detected.')
            time.sleep(0.6)
            return True

        time.sleep(interval)

    print('[WARN] Scouting UI never detected.')
    return False


def battle_ended() -> bool:
    img = take_screenshot('battle.png')
    if img is None:
        return False
    crop = img[BATTLE_Y1:BATTLE_Y2, BATTLE_X1:BATTLE_X2]
    upscaled = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    for _, text, _ in reader.readtext(upscaled):
        if any(kw in text.lower() for kw in BATTLE_KEYWORDS):
            print('\n🏁 Battle ended')
            return True
    return False


def wait_battle_end():
    print('⏳ Waiting for battle to finish…')
    start_time = time.time()
    while True:
        if state.stop_event.is_set():
            print('\n[STOP] battle wait aborted')
            return
        if connection_popup_visible():
            print('\n[WARN] Connection lost detected—recovering…')
            boot_recovery()
            return
        if battle_ended():
            print()
            return
        elapsed = time.time() - start_time
        if elapsed >= MAX_WAIT_BATTLE:
            print('\r⏰ Timeout—forcing Return Home.')
            return
        time.sleep(1)


def is_next_button_present() -> bool:
    time.sleep(0.5)
    screenshot_file = take_screenshot(output_path='is_next_button.png')
    img = imread_unicode(screenshot_file)
    if img is None:
        print(f"❌ Could not load screenshot '{screenshot_file}'")
        return False

    x1, y1, x2, y2 = NEXT_BTN_REGION
    roi = img[y1:y2, x1:x2]
    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    tpl = imread_unicode(NEXT_BTN_TEMPLATE, cv2.IMREAD_GRAYSCALE)

    if tpl is None:
        print(f"❌ Cannot load template '{NEXT_BTN_TEMPLATE}'")
        return False

    if gray_roi.shape[0] < tpl.shape[0] or gray_roi.shape[1] < tpl.shape[1]:
        return False

    res = cv2.matchTemplate(gray_roi, tpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)

    print(f'    [MATCH] Next-btn score: {max_val:.2f}')
    return max_val >= NEXT_THRESH


def treasure_event():
    hammer_tmpl = Path(TEMPLATE_DIR) / 'hammer.png'

    print('Checking if treasure event is active. . .')
    shot_path = take_screenshot('treasure_event')
    time.sleep(0.2)
    img = imread_unicode(shot_path)

    hammer_score, _, _ = _match_template(
        img, hammer_tmpl, region=HAMMER_REGION, thresh=0.8
    )

    if hammer_score >= 0.8:
        print('Treasure event detected.')
        print('tapping. . . ')
        for _ in range(4):
            time.sleep(0.2)
            tap(*TREASURE_TAP)
    else:
        return

    time.sleep(4)
    print('Treasure open successfully.')
    print('Going home. . .')
    tap(*TREASURE_HOME_TAP)


def get_stars_from_screen() -> int:
    time.sleep(0.5)
    shot = take_screenshot('resources_gained.png')
    time.sleep(0.5)
    img = imread_unicode(shot)
    if img is None:
        return 0

    def _match(tpl_name: str, roi_tuple) -> bool:
        x1, y1, x2, y2 = roi_tuple
        roi = img[y1:y2, x1:x2]
        tpl_path = os.path.join(TEMPLATE_DIR, tpl_name)
        tpl = imread_unicode(tpl_path)
        if tpl is None or roi.size == 0:
            return False
        res = cv2.matchTemplate(roi, tpl, cv2.TM_CCOEFF_NORMED)
        _, score, _, _ = cv2.minMaxLoc(res)
        return score >= 0.4

    if not _match('one_star.png', STAR1_ROI):
        return 0
    if not _match('two_star.png', STAR2_ROI):
        return 1
    if _match('three_star.png', STAR3_ROI):
        return 3
    return 2


def gain_resources(stars: int) -> tuple[int, int, int]:
    time.sleep(0.5)
    shot = take_screenshot('resources_gained.png')
    time.sleep(0.5)
    img = imread_unicode(shot)
    if img is None:
        return (0, 0, 0)

    def _ocr_sum(x1, y1, x2, y2) -> int:
        from COCbot.vision.read_text.numbers import read_number
        return read_number(img[y1:y2, x1:x2]) or 0

    gold_left = _ocr_sum(*GAIN_GOLD_L)
    elixir_left = _ocr_sum(*GAIN_ELIXIR_L)
    de_left = _ocr_sum(*GAIN_DE_L)

    if stars > 0:
        gold_right = _ocr_sum(*GAIN_GOLD_R)
        elixir_right = _ocr_sum(*GAIN_ELIXIR_R)
        de_right = _ocr_sum(*GAIN_DE_R)
    else:
        gold_right = elixir_right = de_right = 0

    return (
        gold_left + gold_right,
        elixir_left + elixir_right,
        de_left + de_right,
    )
