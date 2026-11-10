"""DEPRECATED: not used by the runtime attack pipeline.

The runtime now uses YOLO-seg (`redline_model`) or the OpenCV fallback.
This file is kept only as a historical DLL experiment and triggers MyBot's
license check (DetectRedArea.checkLicence -> Process.Kill).
"""

import ctypes
import ctypes.wintypes
import struct
import subprocess
import os
import sys
import time
import io
import json
import argparse
from PIL import Image, ImageDraw

# ================== CONFIG ==================
ADB_PORT = "21503"
# getRedArea(hBitmap, xSkip, ySkip, colorVariation)
# Verified on 860x732: cv=40 + ySkip=5 is ~0.46s, cv=50 is ~6s and noisy.
CV = 40          # color variation
X_SKIP = 1       # horizontal scan step
Y_SKIP = 5       # vertical scan step (NOT an outward distance)
DISTANCE = Y_SKIP  # kept for backward compatibility
# ============================================

def is_32bit():
    return struct.calcsize("P") * 8 == 32

def get_emulator_pid():
    pid = None
    def enum_windows_proc(hwnd, lParam):
        nonlocal pid
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.lower()
            # Do not match the MyBot window ("MyBot PH MOD v15.9 (MEmu)") or game windows.
            if "mybot" in title or "clash" in title:
                return True
            for emu in ["memu", "ldplayer", "dnplayer", "bluestacks", "nox", "mumu"]:
                if emu in title:
                    pid_val = ctypes.wintypes.DWORD()
                    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_val))
                    pid = pid_val.value
                    return False  # stop
        return True
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    ctypes.windll.user32.EnumWindows(EnumWindowsProc(enum_windows_proc), 0)
    return pid or os.getpid()

get_memu_pid = get_emulator_pid

def setup_adb(adb_path, port):
    # Do NOT kill every adb.exe: MyBot.run / other bots may be using it.
    print("[*] Start/reuse adb server...")
    subprocess.run([adb_path, "start-server"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.5)
    print(f"[*] Connect 127.0.0.1:{port}...")
    subprocess.run([adb_path, "connect", f"127.0.0.1:{port}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.5)
    res = subprocess.run([adb_path, "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for line in res.stdout.splitlines():
        if "device" in line and not line.startswith("List"):
            return line.split()[0]
    return None

def capture_adb(adb_path, serial):
    print("[*] ADB screencap...")
    res = subprocess.run([adb_path, "-s", serial, "exec-out", "screencap", "-p"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0 or len(res.stdout) < 1000:
        print("[-] ADB screencap failed")
        print(res.stderr.decode('utf-8', errors='ignore'))
        return None
    return Image.open(io.BytesIO(res.stdout)).convert("RGBA")

def create_dib32(img_rgba):
    """Tao DIB 32bpp top-down tu PIL Image hoac numpy array"""
    try:
        import numpy as np
        if isinstance(img_rgba, np.ndarray):
            h, w = img_rgba.shape[:2]
            if len(img_rgba.shape) == 2:
                import cv2
                bgra = cv2.cvtColor(img_rgba, cv2.COLOR_GRAY2BGRA)
            elif img_rgba.shape[2] == 3:
                import cv2
                bgra = cv2.cvtColor(img_rgba, cv2.COLOR_BGR2BGRA)
            else:
                bgra = img_rgba.copy()
            bgra[:, :, 3] = 255
            data_bytes = bgra.tobytes()
            width, height = w, h
        else:
            width, height = img_rgba.size
            raw_data = bytearray(img_rgba.tobytes())
            for i in range(3, len(raw_data), 4):
                raw_data[i] = 255  # alpha
            for i in range(0, len(raw_data), 4):
                raw_data[i], raw_data[i+2] = raw_data[i+2], raw_data[i]
            data_bytes = bytes(raw_data)
    except Exception:
        width, height = img_rgba.size
        raw_data = bytearray(img_rgba.tobytes())
        for i in range(3, len(raw_data), 4):
            raw_data[i] = 255
        for i in range(0, len(raw_data), 4):
            raw_data[i], raw_data[i+2] = raw_data[i+2], raw_data[i]
        data_bytes = bytes(raw_data)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", ctypes.c_uint32),
            ("biWidth", ctypes.c_int32),
            ("biHeight", ctypes.c_int32),
            ("biPlanes", ctypes.c_uint16),
            ("biBitCount", ctypes.c_uint16),
            ("biCompression", ctypes.c_uint32),
            ("biSizeImage", ctypes.c_uint32),
            ("biXPelsPerMeter", ctypes.c_int32),
            ("biYPelsPerMeter", ctypes.c_int32),
            ("biClrUsed", ctypes.c_uint32),
            ("biClrImportant", ctypes.c_uint32)
        ]

    class RGBQUAD(ctypes.Structure):
        _fields_ = [
            ("rgbBlue", ctypes.c_uint8),
            ("rgbGreen", ctypes.c_uint8),
            ("rgbRed", ctypes.c_uint8),
            ("rgbReserved", ctypes.c_uint8)
        ]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [
            ("bmiHeader", BITMAPINFOHEADER),
            ("bmiColors", RGBQUAD * 1)
        ]

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = width
    bmi.bmiHeader.biHeight = -height  # top-down
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0  # BI_RGB

    ctypes.windll.user32.GetDC.restype = ctypes.c_void_p
    ctypes.windll.user32.GetDC.argtypes = [ctypes.c_void_p]
    ctypes.windll.user32.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    ctypes.windll.gdi32.CreateDIBSection.restype = ctypes.c_void_p
    ctypes.windll.gdi32.CreateDIBSection.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p, ctypes.c_uint32]
    ctypes.windll.gdi32.DeleteObject.argtypes = [ctypes.c_void_p]
    ctypes.windll.gdi32.DeleteObject.restype = ctypes.c_bool

    ppvBits = ctypes.c_void_p()
    hdc = ctypes.windll.user32.GetDC(0)
    hDib = ctypes.windll.gdi32.CreateDIBSection(hdc, ctypes.byref(bmi), 0, ctypes.byref(ppvBits), None, 0)
    ctypes.windll.user32.ReleaseDC(0, hdc)

    if not hDib:
        raise RuntimeError("CreateDIBSection failed")

    ctypes.memmove(ppvBits, data_bytes, len(data_bytes))
    return hDib

_dll_cached = None

def get_mybot_dll():
    global _dll_cached
    if _dll_cached is not None:
        return _dll_cached

    if not is_32bit():
        return None

    cur_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(cur_dir, "MyBot.run.dll"),
        os.path.join(cur_dir, "..", "MyBot.run.dll"),
        os.path.join(cur_dir, "COCbot", "attacks", "MyBot.run.dll"),
    ]
    dll_path = None
    for c in candidates:
        if os.path.exists(c):
            dll_path = c
            break

    if not dll_path:
        return None

    try:
        dll = ctypes.WinDLL(dll_path)
        dll.setAndroidPID.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        dll.setAndroidPID.restype = ctypes.c_char_p

        dll.SetBotGuiPID.argtypes = [ctypes.c_int]
        dll.SetBotGuiPID.restype = ctypes.c_char_p

        dll.getRedArea.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        dll.getRedArea.restype = ctypes.c_char_p

        # The DLL export is setGlobalVar, not debugMBRFunctions.
        try:
            dll.setGlobalVar.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
            dll.setGlobalVar.restype = ctypes.c_char_p
            dll.setGlobalVar(0, 0, 0)
        except Exception:
            pass

        # getRedArea does NOT need setAndroidPID/SetBotGuiPID. Passing a wrong
        # window PID can crash the mixed-mode DLL, so keep this bridge minimal.
        # (test_ocr.py can initialize Android separately if needed.)
        # pid = get_emulator_pid()
        # dll.setAndroidPID(pid, b"v15.9", b"MEmu", b"7.1.2", b"MEmu")
        # dll.SetBotGuiPID(os.getpid())

        _dll_cached = dll
        return _dll_cached
    except Exception as e:
        print(f"[-] Load MyBot.run.dll failed: {e}")
        return None

def parse_red_area_raw(raw_str):
    """
    Parse chuoi ket qua tu getRedArea thanh dict:
    parts[0] -> TL (Top-Left)
    parts[1] -> BL (Bottom-Left)
    parts[2] -> BR (Bottom-Right)
    parts[3] -> TR (Top-Right)
    """
    if (not raw_str
            or raw_str.startswith("Error")
            or raw_str.startswith("-1")
            or raw_str.startswith("-2")
            or raw_str.startswith("<GetAsyncResult>")):
        return None

    # getRedArea returns exactly 4 sides: TL#BL#BR#TR.
    parts = raw_str.split("#")
    if len(parts) != 4:
        return None

    names = ["TL", "BL", "BR", "TR"]
    result = {}

    for name, side_str in zip(names, parts):
        pixels = []
        for token in side_str.split("|"):
            token = token.strip()
            if not token:
                continue
            xy = token.split("-")
            if len(xy) == 2:
                try:
                    x, y = int(xy[0]), int(xy[1])
                    if 0 <= x <= 900 and 0 <= y <= 800:
                        pixels.append((x, y))
                except ValueError:
                    pass

        # Sap xep diem theo trat tu doc theo canh
        if name in ("TL", "TR"):
            pixels.sort(key=lambda p: (p[0], p[1]))
        else:
            pixels.sort(key=lambda p: (p[0], -p[1]))

        result[name] = pixels

    # Reject incomplete redlines; let the OpenCV fallback handle them.
    if any(len(result[name]) < 2 for name in names):
        return None

    return result

def get_red_area_from_image(img_or_path, cv_val=CV, x_skip=X_SKIP, y_skip=Y_SKIP, distance=None):
    """
    Lay toa do Redline tu anh bang MyBot.run.dll.

    getRedArea signature: getRedArea(hBitmap, xSkip, ySkip, colorVariation).
    `distance` is kept only as a backward-compatible alias for ySkip, NOT an
    outward offset from the red line.
    """
    if not is_32bit():
        return None

    if distance is not None:
        y_skip = distance

    dll = get_mybot_dll()
    if not dll:
        return None

    if isinstance(img_or_path, str):
        if not os.path.exists(img_or_path):
            return None
        img_rgba = Image.open(img_or_path).convert("RGBA")
    elif hasattr(img_or_path, 'convert'):
        img_rgba = img_or_path.convert("RGBA")
    else:
        # Numpy array (BGR from OpenCV / ScreenshotArray)
        img_rgba = img_or_path

    hDib = 0
    try:
        hDib = create_dib32(img_rgba)
        res = dll.getRedArea(hDib, int(x_skip), int(y_skip), int(cv_val))

        if not res:
            return None

        raw_str = res.decode('utf-8', errors='ignore')
        return parse_red_area_raw(raw_str)
    except Exception as e:
        print(f"[-] get_red_area_from_image error: {e}")
        return None
    finally:
        if hDib:
            ctypes.windll.gdi32.DeleteObject(hDib)

def main():
    if not is_32bit():
        print("[-] LOI: Ban phai chay Python 32-bit de load duoc MyBot.run.dll!")
        print("    Hien tai Python cua ban la", struct.calcsize("P") * 8, "bit.")
        print("    -> Dung lenh: py -3-32 src/test_mybot_dll.py")
        return

    pid = get_emulator_pid()
    print(f"[+] Emulator PID: {pid}")

    dll = get_mybot_dll()
    if not dll:
        print("[-] Khong load duoc DLL!")
        return
    print("[+] DLL loaded va khoi tao thanh cong")

    cur_dir = os.path.dirname(os.path.abspath(__file__))
    candidates_adb = [
        os.path.join(cur_dir, "adb.exe"),
        os.path.join(cur_dir, "adb", "adb.exe"),
        os.path.join(cur_dir, "COCbot", "adb", "adb.exe"),
    ]
    adb_path = None
    for c in candidates_adb:
        if os.path.exists(c):
            adb_path = c
            break

    if not adb_path:
        adb_path = "adb"

    serial = setup_adb(adb_path, ADB_PORT)
    if not serial:
        print("[-] Khong the ket noi ADB!")
        return
    print(f"[+] ADB Device: {serial}")

    img = capture_adb(adb_path, serial)
    if not img:
        return
    print(f"[+] Image: {img.size[0]}x{img.size[1]}")

    pts_dict = get_red_area_from_image(img, cv_val=CV, x_skip=X_SKIP, y_skip=Y_SKIP)
    if not pts_dict:
        print("[-] getRedArea khong tra ve toa do hop le")
        return

    img_draw = img.convert("RGB")
    draw = ImageDraw.Draw(img_draw)
    colors = {
        "TL": (0, 255, 0),
        "BL": (0, 255, 255),
        "BR": (255, 255, 0),
        "TR": (255, 0, 255),
    }

    total = 0
    print("=== Ket qua ===")
    for name in ["TL", "BL", "BR", "TR"]:
        pixels = pts_dict.get(name, [])
        for (x, y) in pixels:
            draw.rectangle([x-1, y-1, x+1, y+1], fill=colors[name])
        total += len(pixels)
        print(f"    {name}: {len(pixels)} pixels")

    print(f"[+] Total: {total} pixels")

    out_file = f"debug_python_cv{CV}.png"
    img_draw.save(out_file)
    print(f"[+] Saved: {out_file}")
    print("    -> Mo file nay de xem ket qua!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=str, help="Duong dan anh de nhan dien Redline")
    parser.add_argument("--stdin", action="store_true", help="Doc anh tu stream stdin (khong luu file)")
    parser.add_argument("--json", action="store_true", help="Xuat ket qua ra JSON")
    parser.add_argument("--cv", type=int, default=CV, help="Color variation")
    parser.add_argument("--dist", type=int, default=Y_SKIP,
                        help="Vertical scan step (ySkip); not an outward distance")
    args = parser.parse_args()

    if args.stdin:
        if not is_32bit():
            if args.json:
                print(json.dumps({"error": "not_32bit"}))
            else:
                print("[-] Error: Python is not 32-bit")
            sys.exit(1)
        raw_bytes = sys.stdin.buffer.read()
        if raw_bytes:
            img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
            pts = get_red_area_from_image(img, cv_val=args.cv, distance=args.dist)
            if args.json:
                print(json.dumps(pts if pts else {}))
            else:
                print(f"[+] Result: {pts}")
        else:
            if args.json:
                print(json.dumps({}))
        sys.exit(0)

    if args.image:
        if not is_32bit():
            if args.json:
                print(json.dumps({"error": "not_32bit"}))
            else:
                print("[-] Error: Python is not 32-bit")
            sys.exit(1)

        pts = get_red_area_from_image(args.image, cv_val=args.cv, distance=args.dist)
        if args.json:
            print(json.dumps(pts if pts else {}))
        else:
            print(f"[+] Result: {pts}")
    else:
        main()