# ==== COCbot/utils/screenshot_utils.py ====
import subprocess
import sys
import time

import cv2
import numpy as np

import COCbot.core.paths  # noqa: F401
import COCbot.core.state as state
from COCbot.emulator.adb_config import ADB_BIN
from COCbot.routines.boot_recovery import boot_recovery

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
PNG_MAGIC = b'\x89PNG\r\n\x1a\n'


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


def take_screenshot(output_path='screen.png', max_retries=4, retry_delay=5.0):
    host = _get_host()
    if not host:
        raise RuntimeError('No emulator selected (state.host is None)')

    for attempt in range(1, max_retries + 1):
        proc = subprocess.Popen(
            [ADB_BIN, '-s', host, 'exec-out', 'screencap', '-p'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW,
        )
        raw, err = proc.communicate()

        if proc.returncode != 0:
            print(f'❌ adb stream error (attempt {attempt}): {err.decode(errors="ignore").strip()}')
            if attempt < max_retries:
                time.sleep(retry_delay)
                continue
            boot_recovery()

        idx = raw.find(PNG_MAGIC)
        if idx < 0:
            print(f'❌ PNG signature not found (attempt {attempt})')
            if attempt < max_retries:
                time.sleep(retry_delay)
                continue
            boot_recovery()

        png_data = raw[idx:]
        arr = np.frombuffer(png_data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)

        if img is None:
            print(f'❌ Failed to decode image (attempt {attempt})')
            if attempt < max_retries:
                time.sleep(retry_delay)
                continue
            boot_recovery()

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        _, stddev = cv2.meanStdDev(gray)
        if stddev[0][0] < 1.0:
            print(f'⚠️ Blank screen detected (std={stddev[0][0]:.2f}) on attempt {attempt}')
            if attempt < max_retries:
                time.sleep(retry_delay)
                continue
            print('❌ Max retries reached with blank screens')
            boot_recovery()

        with open(output_path, 'wb') as f:
            f.write(png_data)
        return output_path

    # Fallback: file-based screencap + pull
    remote_path = f'/sdcard/{output_path}'
    subprocess.run(
        [ADB_BIN, '-s', host, 'shell', 'screencap', '-p', remote_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )
    subprocess.run(
        [ADB_BIN, '-s', host, 'pull', remote_path, output_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )
    return output_path


if __name__ == '__main__':
    take_screenshot()
