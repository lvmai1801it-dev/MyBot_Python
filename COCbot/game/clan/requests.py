# ==== COCbot/game/clan/requests.py ====
"""Xin quân (request troops) qua Clan Chat.

UI Clash of Clans hiện tại không còn nút "Army" riêng trên màn hình home,
và bảng Army Overview cũng không có nút Request. Cách đúng (giống MyBot)
là: mở Clan Chat -> bấm icon Clan Castle ở footer chat -> Send.
"""
import os
import subprocess
import sys
import time

import cv2

import COCbot.app.paths as paths
from COCbot.vision.ocr import reader
from COCbot.game.battle.ensure_home_base import ensure_home_base
from COCbot.platform.adb_config import ADB_BIN
from COCbot.vision.capture import take_screenshot
from COCbot.platform.unicode import imread_unicode

from COCbot.app.coords import (
    RT_CHAT_OPEN_TAP,
    RT_CHAT_WAR_CLOSE_TAP,
    RT_CHAT_REQUEST_TAP,
    RT_CHAT_REQUEST_SEND,
    RT_CHAT_EXIT_CANCEL,
    RT_WAR_POPUP_ROI,
    RT_REQUEST_DIALOG_ROI,
    RT_CHAT_FOOTER_ROI,
    RT_EXIT_DIALOG_ROI,
)

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0


def _get_host():
    from COCbot.app import state
    if state.host:
        return state.host
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
    from COCbot.platform.tap_guard import blocked
    if blocked(x, y, f"request:{label}"):
        return
    print(f"  👉 [TAP] {label} → Tọa độ ({x}, {y})")
    host = _get_host()
    cmd = [ADB_BIN]
    if host:
        cmd += ['-s', host]
    cmd += ['shell', 'input', 'tap', str(x), str(y)]
    subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )


def _key_back():
    host = _get_host()
    cmd = [ADB_BIN]
    if host:
        cmd += ['-s', host]
    cmd += ['shell', 'input', 'keyevent', '4']
    subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )


def _ocr_text(img, roi):
    """OCR một ROI nhỏ; trả về chữ thường, rỗng nếu lỗi/rỗng."""
    if img is None:
        return ''
    x1, y1, x2, y2 = roi
    h, w = img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    crop = img[y1:y2, x1:x2]
    if crop.size == 0:
        return ''
    try:
        up = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        return ' '.join(reader.readtext(up, detail=0)).lower()
    except Exception as e:
        print(f"  [OCR] lỗi: {e}")
        return ''


def _has_text(img, roi, keywords):
    text = _ocr_text(img, roi)
    if text:
        print(f"  [OCR] {text[:120]}")
    return any(k in text for k in keywords)


def _chat_open(img) -> bool:
    return _has_text(img, RT_CHAT_FOOTER_ROI, ('clan message', 'challenge'))


def _close_chat():
    """Đóng chat bằng BACK; nếu BACK mở hộp Confirm Exit thì bấm Cancel."""
    for _ in range(2):
        _key_back()
        time.sleep(0.8)
        img = _grab('_tmp_close_chat')
        if img is None:
            return
        if _has_text(img, RT_EXIT_DIALOG_ROI, ('confirm exit', 'quit the game')):
            _tap(*RT_CHAT_EXIT_CANCEL, 'cancel_exit')
            return
        if not _chat_open(img):
            return


def auto_request():
    _step_log(1, "KIỂM TRA HOME BASE")
    if not ensure_home_base():
        print("  ❌ Thất bại: Không tìm thấy Home Base. Bỏ qua bước xin quân.")
        return False

    _step_log(2, "MỞ CLAN CHAT")
    _tap(*RT_CHAT_OPEN_TAP, 'clan_chat')
    time.sleep(1.2)
    img = _grab('_tmp_chat')
    if img is None:
        return False

    # Popup Clan War che mất footer chat → đóng bằng X nếu thấy.
    if _has_text(img, RT_WAR_POPUP_ROI, ('clan war', 'join war')):
        _tap(*RT_CHAT_WAR_CLOSE_TAP, 'close_war_popup')
        time.sleep(0.7)
        img = _grab('_tmp_chat') or img

    _step_log(3, "MỞ HỘP XIN QUÂN")
    _tap(*RT_CHAT_REQUEST_TAP, 'request_tower')
    time.sleep(1.0)
    img = _grab('_tmp_request')
    if img is None:
        return False

    _step_log(4, "XÁC NHẬN HỘP REQUEST")
    if not _has_text(img, RT_REQUEST_DIALOG_ROI, ('request', 'reinforcement')):
        print("  ℹ️ Không thấy hộp Request (cooldown/full?) → bỏ qua.")
        _close_chat()
        return True
    print("  ✅ Hộp Request đã mở.")

    _step_log(5, "GỬI REQUEST")
    _tap(*RT_CHAT_REQUEST_SEND, 'send_request')
    time.sleep(1.0)

    _step_log(6, "ĐÓNG CLAN CHAT")
    _close_chat()

    print("\n  ✅ HOÀN TẤT: Đã gửi yêu cầu xin quân thành công.")
    return True


if __name__ == '__main__':
    auto_request()
