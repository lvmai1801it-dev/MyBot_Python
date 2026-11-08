# ==== COCbot/routines/request_troops.py ====
import os
import cv2
import sys
import subprocess
import time

import COCbot.core.paths as paths
import COCbot.core.state as state
from COCbot.utils.ocr_reader import reader
from COCbot.routines.ensure_home_base import ensure_home_base
from COCbot.emulator.adb_config import ADB_BIN
from COCbot.utils.screenshot_utils import take_screenshot
from COCbot.utils.unicode import imread_unicode

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

TEMPLATE_DIR = str(paths.TEMPLATE_DIR)
REQUEST_BTN_TEMPLATE = os.path.join(TEMPLATE_DIR, 'request_button.png')
CLAN_CAKE_TEMPLATE = os.path.join(TEMPLATE_DIR, 'clan_castle_cake.png')
CLAN_CAKE_THRESH = 0.7
REQUEST_THRESH = 0.70

from COCbot.core.coords import (
    RT_ARMY_BUTTON, RT_REQUEST_BUTTON_TAP, RT_SEND_BUTTON, RT_CLOSE_BUTTON,
    RT_ARMY_WINDOW_REGION, RT_REQUEST_BUTTON_REGION,
    RT_CASTLE_CAKE_ROI, RT_CASTLE_CAKE_TAP,
    RT_SAVED_TROOPS_ROI, RT_SAVED_TROOPS_TAP1, RT_SAVED_TROOPS_TAP2,
)

ARMY_BUTTON = RT_ARMY_BUTTON
REQUEST_BUTTON_TAP = RT_REQUEST_BUTTON_TAP
SEND_BUTTON = RT_SEND_BUTTON
CLOSE_BUTTON = RT_CLOSE_BUTTON

ARMY_WINDOW_REGION = RT_ARMY_WINDOW_REGION
REQUEST_BUTTON_REGION = RT_REQUEST_BUTTON_REGION

WINDOW_KEYWORDS = ['ARMY', 'RECIPES', 'MY', 'SAVED']


def _get_host():
    if state.host:
        return state.host
    try:
        import COCbot.core.main as main
        if getattr(main, 'host', None):
            return main.host
    except Exception:
        pass
    try:
        import main
        if getattr(main, 'host', None):
            return main.host
    except Exception:
        pass
    return None


def _step_log(step_num, title):
    print(f"\n{'='*15} [BƯỚC {step_num}] {title.upper()} {'='*15}")


def _grab(tag='_tmp_grab'):
    try:
        p = take_screenshot(output_path=tag)
        return imread_unicode(p, cv2.IMREAD_COLOR)
    except Exception as e:
        print(f"  [LỖI] Chụp màn hình thất bại: {e}")
        return None


def _tap(x, y, label):
    print(f"  👉 [TAP] {label} → Tọa độ ({x}, {y})")
    host = _get_host()
    cmd = [ADB_BIN]
    if host:
        cmd += ['-s', host]
    cmd += ['shell', 'input', 'tap', str(x), str(y)]
    subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW
    )


def _get_screen_state(img):
    if img is None:
        return 'UNKNOWN'
    h, w = img.shape[:2]

    # 1. Kiểm tra bảng Army (quét vùng Header)
    x1, y1, x2, y2 = ARMY_WINDOW_REGION
    crop_army = img[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
    try:
        army_text = ' '.join(reader.readtext(crop_army, detail=0)).upper()
        if any(k in army_text for k in WINDOW_KEYWORDS):
            return 'ARMY'
    except Exception:
        pass

    # 2. Kiểm tra bảng Battle (quét vùng giữa màn hình)
    crop_battle = img[int(h * 0.45):int(h * 0.8), int(w * 0.1):int(w * 0.6)]
    try:
        battle_text = ' '.join(reader.readtext(crop_battle, detail=0)).upper()
        if 'FIND A MATCH' in battle_text or 'RANKED' in battle_text or 'SIGN UP' in battle_text:
            return 'BATTLE'
    except Exception:
        pass

    return 'HOME'


def _close_until_home(max_attempts=4):
    for i in range(1, max_attempts + 1):
        scr = _grab()
        state_name = _get_screen_state(scr)
        print(f"  [KIỂM TRA] Trạng thái màn hình: {state_name}")

        if state_name == 'HOME':
            print("  ✅ Đã về Home Base.")
            return True
        elif state_name == 'ARMY':
            print(f"  ℹ️ Đang ở bảng Army. Bấm nút Close (Lần {i})...")
            _tap(CLOSE_BUTTON[0], CLOSE_BUTTON[1], f"close_army_{i}")
            time.sleep(0.7)
        elif state_name == 'BATTLE':
            print("  ⚠️ Đang ở màn hình Battle. Tự động bấm phím Back để thoát...")
            host = _get_host()
            cmd = [ADB_BIN]
            if host:
                cmd += ['-s', host]
            cmd += ['shell', 'input', 'keyevent', '4']
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW
            )
            time.sleep(0.7)
        else:
            print("  ⚠️ Trạng thái không xác định. Thử bấm Close...")
            _tap(CLOSE_BUTTON[0], CLOSE_BUTTON[1], f"close_unknown_{i}")
            time.sleep(0.7)

    print(f"  ❌ Không thể xác định trạng thái Home sau {max_attempts} lần.")
    return False


def _check_header(img):
    h, w = img.shape[:2]
    x1, y1, x2, y2 = ARMY_WINDOW_REGION
    crop = img[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]

    try:
        results = reader.readtext(crop, detail=0)
        text = ' '.join(results).upper()
    except Exception as e:
        print(f"  [LỖI OCR] {e}")
        return ''
    print(f"  [OCR] Đọc được Header: '{text}'")
    return text


def _check_request_btn(img):
    x1, y1, x2, y2 = REQUEST_BUTTON_REGION
    roi = img[y1:y2, x1:x2]

    tpl = imread_unicode(REQUEST_BTN_TEMPLATE, cv2.IMREAD_COLOR)
    if tpl is None:
        print(f"  ❌ Không tìm thấy file mẫu: {REQUEST_BTN_TEMPLATE}")
        return False

    if roi.shape[0] < tpl.shape[0] or roi.shape[1] < tpl.shape[1]:
        print(f"  ❌ Lỗi kích thước: ROI {roi.shape} nhỏ hơn Template {tpl.shape}")
        return False

    res = cv2.matchTemplate(roi, tpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    print(f"  [MATCH] Điểm khớp nút Request: {max_val:.2f} (Yêu cầu: {REQUEST_THRESH})")

    return max_val >= REQUEST_THRESH


def _check_cake(img) -> bool:
    x1, y1, x2, y2 = RT_CASTLE_CAKE_ROI
    roi = img[y1:y2, x1:x2]

    tpl = imread_unicode(CLAN_CAKE_TEMPLATE, cv2.IMREAD_COLOR)
    if tpl is None:
        return False

    if roi.shape[0] < tpl.shape[0] or roi.shape[1] < tpl.shape[1]:
        return False

    res = cv2.matchTemplate(roi, tpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    print(f"  [MATCH] Điểm khớp Bánh sinh nhật: {max_val:.2f} (Yêu cầu: {CLAN_CAKE_THRESH})")

    if max_val < CLAN_CAKE_THRESH:
        return False

    _tap(RT_CASTLE_CAKE_TAP[0], RT_CASTLE_CAKE_TAP[1], "castle_cake")
    time.sleep(0.7)

    scr = _grab()
    if scr is not None:
        sx1, sy1, sx2, sy2 = RT_SAVED_TROOPS_ROI
        cc_roi = scr[sy1:sy2, sx1:sx2]

        try:
            cc_roi_up = cv2.resize(cc_roi, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
            texts = reader.readtext(cc_roi_up, detail=0)
            joined = ' '.join([t.lower() for t in texts])
            print(f"  [OCR] Đọc chữ vùng Saved Troops: '{joined}'")
        except Exception:
            joined = ''

        if any(k in joined for k in ('tap', 'choose', 'requested', 'reinforcements')):
            _tap(RT_SAVED_TROOPS_TAP1[0], RT_SAVED_TROOPS_TAP1[1], "saved_troops_1")
            print('  ℹ️ Chưa có quân lưu sẵn. Chuyển sang request thường.')
            return False

    _tap(RT_SAVED_TROOPS_TAP2[0], RT_SAVED_TROOPS_TAP2[1], "saved_troops_2")
    time.sleep(0.7)

    _close_until_home()
    print('  ✅ Đã gửi request qua Bánh sinh nhật.')
    return True


def auto_request():
    _step_log(1, "KIỂM TRA HOME BASE")
    if not ensure_home_base():
        print("  ❌ Thất bại: Không tìm thấy Home Base. Bỏ qua bước xin quân.")
        return False

    _step_log(2, "MỞ BẢNG ARMY")
    _tap(ARMY_BUTTON[0], ARMY_BUTTON[1], "army_button")
    time.sleep(0.8)

    img = _grab()
    if img is None:
        return False

    _step_log(3, "XÁC MINH BẢNG ARMY")
    header = _check_header(img)
    if not any(k in header for k in WINDOW_KEYWORDS):
        print(f"  ❌ Thất bại: Bảng Army không mở (Header: '{header}'). Bỏ qua.")
        return False
    print("  ✅ Xác nhận bảng Army đang mở.")

    _step_log(4, "KIỂM TRA NÚT REQUEST")
    has_request_btn = _check_request_btn(img)

    if not has_request_btn:
        print("  ⚠️ Không tìm thấy nút Request sẵn sàng.")
        print("  ℹ️ Lý do: Đang Cooldown (đã xin rồi) HOẶC Chưa vào Clan. Bỏ qua và coi như Thành công.")
        _close_until_home()
        return True

    print("  ✅ Nút Request đã sẵn sàng.")

    _step_log(5, "KIỂM TRA EVENT BÁNH SINH NHẬT")
    if _check_cake(img):
        return True
    print("  ℹ️ Không có bánh. Chuyển sang Request thường.")

    _step_log(6, "THỰC HIỆN REQUEST THƯỜNG")
    _tap(REQUEST_BUTTON_TAP[0], REQUEST_BUTTON_TAP[1], "request_button")
    time.sleep(0.7)

    _step_log(7, "GỬI REQUEST (SEND)")
    _tap(SEND_BUTTON[0], SEND_BUTTON[1], "send_button")
    time.sleep(0.7)

    _step_log(8, "ĐÓNG BẢNG ARMY (LẶP TỚI KHI VỀ HOME)")
    _close_until_home()

    print("\n  ✅ HOÀN TẤT: Đã gửi yêu cầu xin quân thành công.")
    return True


if __name__ == '__main__':
    auto_request()
