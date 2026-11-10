# ==== COCbot/game/village/collectors.py ====
import cv2
import os
import sys
import subprocess
import time

import COCbot.app.paths as paths
import COCbot.app.state as state
from COCbot.platform.adb_config import ADB_BIN
from COCbot.vision.capture import take_screenshot
from COCbot.platform.unicode import imread_unicode

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

TEMPLATE_DIR = str(paths.TEMPLATE_DIR)
DEVICE_SCREENSHOT = '/sdcard/Collectors.png'
LOCAL_SCREENSHOT = os.path.join(paths.SRC_DIR, 'Collectors.png')

TEMPLATE_FILES = ['elixir_collector.png', 'DE_collector.png', 'gold_collector.png']
TEMPLATES = [os.path.join(TEMPLATE_DIR, fn) for fn in TEMPLATE_FILES]

AVAILABLE_THRESHOLD = 0.65
TAP_DELAY = 0.5


def _get_host():
    if state.host:
        return state.host
    try:
        import COCbot.app.bootstrap as main
        if getattr(main, 'host', None):
            return main.host
    except Exception:
        pass
    try:
        from COCbot.app import state as main
        if getattr(main, 'host', None):
            return main.host
    except Exception:
        pass
    return None


def run_adb(cmd_list):
    host = _get_host()

    if host:
        cmd = [ADB_BIN, '-s', host] + cmd_list
    else:
        cmd = [ADB_BIN] + cmd_list

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=CREATE_NO_WINDOW,
    )

    if proc.returncode != 0:
        err = proc.stderr.decode(errors='ignore').strip()
        print(f"[ERROR] ADB failed: {' '.join(cmd_list)}\n  {err}")
        return False
    return True


def find_and_tap_collectors():
    # 1. Chụp màn hình
    screenshot_path = take_screenshot(output_path='Collectors_resources.png')
    image = imread_unicode(screenshot_path, cv2.IMREAD_COLOR)

    if image is None:
        print('[ERROR] Could not load screenshot. Aborting.')
        return

    gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    total_tapped = 0
    summary = []  # list (template_name, score, (cx,cy), tapped: bool)

    for template_path in TEMPLATES:
        tpl_name = os.path.basename(template_path)

        template = imread_unicode(template_path, cv2.IMREAD_GRAYSCALE)

        if template is None:
            print(f'[ERROR] Missing template: {template_path}')
            continue

        if (template.shape[0] > gray_img.shape[0]
                or template.shape[1] > gray_img.shape[1]):
            print(f'[SKIP] {tpl_name}: template {template.shape} lớn hơn ảnh {gray_img.shape}')
            summary.append((tpl_name, 0.0, None, False))
            continue

        result = cv2.matchTemplate(gray_img, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        th, tw = template.shape[:2]
        cx = max_loc[0] + tw // 2
        cy = max_loc[1] + th // 2

        print(f"[MATCH] {tpl_name}: score={max_val:.3f} @ top-left={max_loc} → center=({cx},{cy})")

        # Quyết định tap hay không
        if max_val <= AVAILABLE_THRESHOLD:
            print(f"  → dưới ngưỡng {AVAILABLE_THRESHOLD}, bỏ qua")
            summary.append((tpl_name, max_val, (cx, cy), False))
            continue

        print(f'  → tapping ({cx},{cy})…')
        from COCbot.platform.tap_guard import blocked
        if blocked(cx, cy, f"collector:{tpl_name}"):
            summary.append((tpl_name, max_val, (cx, cy), False))
            continue
        run_adb(['shell', 'input', 'tap', str(cx), str(cy)])
        time.sleep(TAP_DELAY)
        total_tapped += 1
        summary.append((tpl_name, max_val, (cx, cy), True))

    # In bảng tổng kết
    print("\n" + "=" * 70)
    print(f"{'Template':<24} {'Score':<8} {'Tap coord':<16} {'Tapped':<8}")
    print("-" * 70)
    for name, score, coord, tapped in summary:
        coord_str = f"({coord[0]},{coord[1]})" if coord else "—"
        print(f"{name:<24} {score:<8.3f} {coord_str:<16} {'✅' if tapped else '❌':<8}")
    print("=" * 70)
    print(f"[RESULT] Tapped {total_tapped}/{len(TEMPLATES)} collectors")
    print('All done.')


if __name__ == '__main__':
    find_and_tap_collectors()
