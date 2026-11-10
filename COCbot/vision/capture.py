# ==== COCbot/vision/capture.py ====
import subprocess
import sys
import time

import cv2
import numpy as np

import COCbot.app.paths  # noqa: F401
from COCbot.app import state
from COCbot.game.account.boot_recovery import boot_recovery
from COCbot.platform.adb_config import ADB_BIN

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
PNG_MAGIC = b'\x89PNG\r\n\x1a\n'


class ScreenshotArray(np.ndarray):
    """Numpy ndarray wrapper cho phep danh gia bool(img) va tuong thich path-like.

    png_bytes giu nguyen PNG goc tu ADB. MyBot.run.dll getRedArea hoat dong
    on dinh voi PNG goc; anh bi re-encode (cv2/PIL) co the lam DLL loi.
    """
    path: str = 'screen.png'
    png_bytes: bytes = b''

    def __new__(cls, input_array, path='screen.png', png_bytes=b''):
        obj = np.asarray(input_array).view(cls)
        obj.path = str(path)
        obj.png_bytes = png_bytes or b''
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.path = getattr(obj, 'path', 'screen.png')
        self.png_bytes = getattr(obj, 'png_bytes', b'')

    def __bool__(self):
        return self.size > 0

    def __str__(self):
        return self.path

    def __fspath__(self):
        return self.path



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


def take_screenshot(output_path='screen.png', max_retries=4, retry_delay=5.0, save_to_disk=False):
    """
    Chup anh man hinh gia lap toc do cao.

    Mac dinh CHI giu anh trong RAM (ScreenshotArray) va khong ghi file.
    Dat save_to_disk=True khi can debug thu cong; file chi duoc ghi khi
    thuc su can thiet, tranh sinh hang loat anh rac o thu muc goc.
    """
    target = str(output_path or 'screen.png')
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
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

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

        if save_to_disk:
            try:
                with open(target, 'wb') as f:
                    f.write(png_data)
            except Exception:
                pass

        return ScreenshotArray(img, path=target, png_bytes=png_data)

    # Fallback: exec-out cat
    remote_path = '/sdcard/screen_tmp.png'
    subprocess.run(
        [ADB_BIN, '-s', host, 'shell', 'screencap', '-p', remote_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )
    res = subprocess.run(
        [ADB_BIN, '-s', host, 'exec-out', 'cat', remote_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )
    if res.stdout:
        arr = np.frombuffer(res.stdout, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is not None:
            if save_to_disk:
                try:
                    with open(target, 'wb') as f:
                        f.write(res.stdout)
                except Exception:
                    pass
            return ScreenshotArray(img, path=target, png_bytes=res.stdout)
    return None


shot_path = take_screenshot
capture_screen = take_screenshot


if __name__ == '__main__':
    take_screenshot()
