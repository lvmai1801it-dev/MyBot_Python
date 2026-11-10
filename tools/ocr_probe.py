"""ocr_engine.py — MyBot.run.dll OCR bridge

Chế độ 1 — Import (Python 32-bit, in-process):
    from ocr_engine import get_engine
    e = get_engine()
    gold = e.gold_village(img_bgr, x=48, y=69)

Chế độ 2 — Subprocess (bất kỳ Python, giao tiếp qua RAM, BATCH):
    py -3.11-32 ocr_engine.py --stdin --json \\
        --task "gold:coc-v-g:48:69:90:16:ns" \\
        --task "elixir:coc-v-e:48:98:90:16:ns" \\
        --task "trophy:coc-v-t:48:168:75:18:ns" < img.png
    # → {"gold": "1130589", "elixir": "7475000", "trophy": "4527"}

Task opts (ngăn cách bởi dấu phẩy):
    ns   = no-space (xóa khoảng trắng)
    nb   = no-b (xóa ký tự 'b' do OCR nhầm)
    num  = numeric-only (chỉ giữ 0-9)
    img  = dùng DoOCR (ImgLoc) thay vì ocr chuẩn

Chế độ 3 — Test:
    py -3.11-32 ocr_engine.py
"""

import ctypes
import ctypes.wintypes
import struct
import os
import sys
import io
import json
import re
import time
import subprocess
import argparse

# ================== CONFIG ==================
ADB_PORT = "21503"
DLL_NAME = "MyBot.run.dll"
# ============================================


# ============================================================
# DLL + ADB (cached sau lần đầu)
# ============================================================
_dll_instance = None
_dll_init_attempted = False


def _find_dll_path():
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (
        os.path.join(here, DLL_NAME),
        os.path.join(here, "lib", DLL_NAME),
        os.path.join(os.path.dirname(here), "lib", DLL_NAME),
    ):
        if os.path.exists(p):
            return p
    return None


def _get_memu_pid():
    pid = None

    def enum_proc(hwnd, lParam):
        nonlocal pid
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            if "MEmu" in buf.value:
                pv = ctypes.wintypes.DWORD()
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pv))
                pid = pv.value
                return False
        return True

    proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    ctypes.windll.user32.EnumWindows(proc(enum_proc), 0)
    return pid


def _init_dll():
    global _dll_instance, _dll_init_attempted
    if _dll_init_attempted:
        return _dll_instance
    _dll_init_attempted = True

    if struct.calcsize("P") * 8 != 32:
        return None

    dll_path = _find_dll_path()
    if not dll_path:
        return None

    try:
        dll = ctypes.WinDLL(dll_path)
        # ocr(hBmp, lang, debug) -> str
        dll.ocr.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        dll.ocr.restype = ctypes.c_char_p
        # DoOCR(hBmp, lang) -> str
        dll.DoOCR.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        dll.DoOCR.restype = ctypes.c_char_p
        # license init
        dll.setAndroidPID.argtypes = [
            ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
        ]
        dll.setAndroidPID.restype = ctypes.c_char_p
        dll.SetBotGuiPID.argtypes = [ctypes.c_int]
        dll.SetBotGuiPID.restype = ctypes.c_char_p

        pid = _get_memu_pid()
        if pid:
            dll.setAndroidPID(pid, b"15.9", b"MEmu", b"9.5.6.1", b"MEmu")
            dll.SetBotGuiPID(os.getpid())

        _dll_instance = dll
        return dll
    except Exception as e:
        print(f"[ocr_engine] DLL load failed: {e}", file=sys.stderr)
        return None


# ============================================================
# IMAGE → DIB32
# ============================================================
class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32), ("biHeight", ctypes.c_int32),
        ("biPlanes", ctypes.c_uint16), ("biBitCount", ctypes.c_uint16),
        ("biCompression", ctypes.c_uint32), ("biSizeImage", ctypes.c_uint32),
        ("biXPelsPerMeter", ctypes.c_int32), ("biYPelsPerMeter", ctypes.c_int32),
        ("biClrUsed", ctypes.c_uint32), ("biClrImportant", ctypes.c_uint32),
    ]


class _RGBQUAD(ctypes.Structure):
    _fields_ = [
        ("rgbBlue", ctypes.c_uint8), ("rgbGreen", ctypes.c_uint8),
        ("rgbRed", ctypes.c_uint8), ("rgbReserved", ctypes.c_uint8),
    ]


class _BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", _BITMAPINFOHEADER), ("bmiColors", _RGBQUAD * 1)]


def _to_bgr(img):
    """Chuẩn hóa đầu vào: PIL Image / numpy array / str path → numpy BGR."""
    import numpy as np
    if isinstance(img, str):
        from PIL import Image
        img = Image.open(img)
    if hasattr(img, "convert"):
        arr = np.array(img.convert("RGB"))
    else:
        arr = np.asarray(img)
        if arr.ndim == 2:
            arr = np.stack([arr] * 3, axis=-1)
        elif arr.shape[2] == 4:
            arr = arr[:, :, :3]
    if arr.dtype != np.uint8:
        arr = arr.astype(np.uint8)
    # Nếu đầu vào là RGB, chuyển sang BGR; nếu đã là BGR thì bỏ qua (caller tự biết)
    # Ta giả định đầu vào là BGR (OpenCV convention) để tránh double swap
    return arr


def _create_dib32_from_bgr(img_bgr):
    import numpy as np
    height, width = img_bgr.shape[:2]

    bmi = _BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = width
    bmi.bmiHeader.biHeight = -height
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0

    ctypes.windll.user32.GetDC.restype = ctypes.c_void_p
    ctypes.windll.gdi32.CreateDIBSection.restype = ctypes.c_void_p
    ctypes.windll.gdi32.CreateDIBSection.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint,
        ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p, ctypes.c_uint32,
    ]
    ctypes.windll.gdi32.DeleteObject.argtypes = [ctypes.c_void_p]
    ctypes.windll.gdi32.DeleteObject.restype = ctypes.c_bool

    ppv = ctypes.c_void_p()
    hdc = ctypes.windll.user32.GetDC(0)
    h = ctypes.windll.gdi32.CreateDIBSection(hdc, ctypes.byref(bmi), 0, ctypes.byref(ppv), None, 0)
    ctypes.windll.user32.ReleaseDC(0, hdc)
    if not h:
        raise RuntimeError("CreateDIBSection failed")

    bgra = np.dstack([img_bgr, np.full((height, width), 255, dtype=np.uint8)])
    ctypes.memmove(ppv, bgra.tobytes(), bgra.nbytes)
    return h


# ============================================================
# HẬU XỬ LÝ KẾT QUẢ OCR
# ============================================================
def _post_process(text, remove_space=False, strip_b=False, numeric_only=False):
    if not text:
        return ""
    if strip_b:
        text = text.replace("b", "").replace("B", "")
    if numeric_only:
        text = re.sub(r"[^0-9]", "", text)
    if remove_space:
        text = text.replace(" ", "")
    else:
        text = " ".join(text.split())
    return text


# ============================================================
# OCR ENGINE
# ============================================================
class OcrEngine:
    """Wrapper cho MyBot.run.dll — cache DIB, tự cleanup."""

    def __init__(self):
        self._dll = None

    def _ensure_dll(self):
        if self._dll is None:
            self._dll = _init_dll()
        return self._dll

    def available(self):
        return self._ensure_dll() is not None

    def ocr(self, img, language, x=0, y=0, w=None, h=None,
            remove_space=False, strip_b=False, numeric_only=False,
            use_imgloc=False):
        """Low-level OCR. img: PIL / numpy BGR / path."""
        dll = self._ensure_dll()
        if dll is None:
            return ""

        arr = _to_bgr(img)
        if w is not None and h is not None:
            y2 = min(arr.shape[0], y + h)
            x2 = min(arr.shape[1], x + w)
            arr = arr[max(0, y):y2, max(0, x):x2]
            if arr.size == 0:
                return ""

        try:
            h_dib = _create_dib32_from_bgr(arr)
        except Exception as e:
            print(f"[ocr_engine] DIB failed: {e}", file=sys.stderr)
            return ""

        try:
            lang_b = language.encode("utf-8")
            if use_imgloc:
                res = dll.DoOCR(h_dib, lang_b)
            else:
                res = dll.ocr(h_dib, lang_b, 0)
        finally:
            ctypes.windll.gdi32.DeleteObject(h_dib)

        raw = res.decode("utf-8", errors="ignore") if res else ""
        return _post_process(raw, remove_space, strip_b, numeric_only)

    # ---------- Convenience (giống AutoIt getXXX) ----------

    def gold_village(self, img, x=48, y=69):
        return self.ocr(img, "coc-v-g", x, y, 90, 16, remove_space=True)

    def elixir_village(self, img, x=48, y=98):
        return self.ocr(img, "coc-v-e", x, y, 90, 16, remove_space=True)

    def dark_elixir_village(self, img, x=48, y=126):
        return self.ocr(img, "coc-v-de", x, y, 75, 18, remove_space=True)

    def trophy_village(self, img, x=48, y=168):
        return self.ocr(img, "coc-v-t", x, y, 75, 18, remove_space=True)

    def trophy_main_screen(self, img, x, y):
        """Fallback chain như AutoIt: coc-ms → coc-cc-trophy → coc-t-b → coc-profile → coc-v-t."""
        digits = self.ocr(img, "coc-ms", x, y, 50, 16, numeric_only=True)
        if 3 <= len(digits) <= 5:
            return digits
        for lang in ("coc-cc-trophy", "coc-t-b", "coc-profile", "coc-v-t"):
            digits = self.ocr(img, lang, x - 1, y - 1, 58, 18, numeric_only=True)
            if 3 <= len(digits) <= 5:
                return digits
        return digits

    def resources_main_screen(self, img, x, y):
        return self.ocr(img, "coc-ms", x, y, 125, 16).replace("-", "")

    def resources_loot(self, img, x, y):
        return self.ocr(img, "coc-loot", x, y, 160, 22)

    def resources_loot_de(self, img, x, y):
        return self.ocr(img, "coc-loot", x, y, 120, 22)

    def resources_loot_trophy(self, img, x, y):
        return self.ocr(img, "coc-loot", x, y, 50, 22)

    def resources_bonus(self, img, x, y):
        return self.ocr(img, "coc-bonus", x, y, 98, 20)

    def yellow_level(self, img, x, y):
        return self.ocr(img, "coc-YellowLevel", x, y, 170, 20, numeric_only=True)

    def building_name(self, img, x, y):
        """coc-build (ImgLoc) + fallback coc-build2 nếu thiếu '(Level N)'."""
        text = self.ocr(img, "coc-build", x, y, 420, 27, use_imgloc=True)
        if text and re.search(r"(?i)\(\s*Level\s+\d+\s*\)", text):
            return text
        alt = self.ocr(img, "coc-build2", x, y - 27, 420, 27, use_imgloc=True)
        if alt and re.search(r"(?i)\(\s*Level\s+\d+\s*\)", alt):
            return alt
        # Chuẩn hóa "ii" (glyph 8) trong Level field
        text = re.sub(r"(?i)ii", "8", text)
        return text

    def builders(self, img, x, y, wide=False, bb=False):
        """Trả về '5#5' hoặc '3#5' — free#total."""
        w = 45 if wide else 40
        h = 24 if wide else (18 if bb else 20)
        return self.ocr(img, "coc-Builders", x, y, w, h)

    def overall_damage(self, img, x, y):
        return self.ocr(img, "coc-overalldamage", x, y, 50, 20)

    def guard_shield(self, img, x, y):
        return self.ocr(img, "coc-guardshield", x, y, 68, 15)

    def remain_hero(self, img, x, y):
        return self.ocr(img, "coc-remainhero", x, y, 55, 13, strip_b=True)

    def upgrade_cost(self, img, x, y):
        return self.ocr(img, "coc-CostsUpgrades", x, y, 120, 18, numeric_only=True)

    def upgrade_cost_red(self, img, x, y):
        return self.ocr(img, "coc-u-r", x, y, 120, 18, strip_b=True)

    def bldg_upgrade_time(self, img, x, y):
        text = self.ocr(img, "coc-uptime", x, y, 105, 18)
        return re.sub(r"[^0-9wdhms]", "", text.lower())

    def chat_string(self, img, x, y, language="coc-chat"):
        return self.ocr(img, language, x, y, 320, 16)

    def language_check(self, img, x, y):
        return self.ocr(img, "coc-ms-testl", x, y, 93, 16)


# Singleton
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = OcrEngine()
    return _engine


# Module-level shortcuts
def get_gold_village_search(img, x=48, y=69):        return get_engine().gold_village(img, x, y)
def get_elixir_village_search(img, x=48, y=98):      return get_engine().elixir_village(img, x, y)
def get_dark_elixir_village_search(img, x=48, y=126):return get_engine().dark_elixir_village(img, x, y)
def get_trophy_village_search(img, x=48, y=168):     return get_engine().trophy_village(img, x, y)
def get_trophy_main_screen(img, x, y):               return get_engine().trophy_main_screen(img, x, y)
def get_resources_main_screen(img, x, y):            return get_engine().resources_main_screen(img, x, y)
def get_resources_loot(img, x, y):                   return get_engine().resources_loot(img, x, y)
def get_yellow_level(img, x, y):                     return get_engine().yellow_level(img, x, y)
def get_building_name(img, x, y):                    return get_engine().building_name(img, x, y)
def get_builders(img, x, y, wide=False, bb=False):   return get_engine().builders(img, x, y, wide, bb)
def get_overall_damage(img, x, y):                   return get_engine().overall_damage(img, x, y)
def get_remain_hero(img, x, y):                      return get_engine().remain_hero(img, x, y)
def get_upgrade_cost(img, x, y):                     return get_engine().upgrade_cost(img, x, y)
def get_upgrade_cost_red(img, x, y):                 return get_engine().upgrade_cost_red(img, x, y)
def get_bldg_upgrade_time(img, x, y):                return get_engine().bldg_upgrade_time(img, x, y)


# ============================================================
# CLI: SUBPROCESS BATCH MODE
# ============================================================
def _parse_opts(opts):
    if not opts:
        return {}
    flags = set(opts.split(","))
    return {
        "remove_space": "ns" in flags,
        "strip_b": "nb" in flags,
        "numeric_only": "num" in flags,
        "use_imgloc": "img" in flags,
    }


def _cli_stdin_batch(args):
    """Đọc PNG từ stdin, chạy nhiều task, xuất JSON dict {name: text}."""
    try:
        import numpy as np
        from PIL import Image
    except ImportError as e:
        print(json.dumps({"error": f"missing lib: {e}"}))
        return 1

    png_bytes = sys.stdin.buffer.read()
    if not png_bytes:
        print(json.dumps({"error": "empty stdin"}))
        return 1

    try:
        pil = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        img_bgr = np.array(pil)[:, :, ::-1].copy()
    except Exception as e:
        print(json.dumps({"error": f"PNG decode failed: {e}"}))
        return 1

    engine = get_engine()
    if not engine.available():
        print(json.dumps({"error": "DLL not available"}))
        return 1

    results = {}
    for task in args.task:
        # Format: "name:language:x:y:w:h:opts"  (opts có thể rỗng, nhưng vẫn cần ':' cuối)
        try:
            parts = task.split(":")
            if len(parts) < 7:
                results[parts[0]] = ""
                continue
            name, lang, x_s, y_s, w_s, h_s = parts[:6]
            opts_str = ":".join(parts[6:])
            x, y, w, h = int(x_s), int(y_s), int(w_s), int(h_s)
            opts = _parse_opts(opts_str)
            results[name] = engine.ocr(
                img_bgr, lang, x, y, w, h,
                remove_space=opts.get("remove_space", False),
                strip_b=opts.get("strip_b", False),
                numeric_only=opts.get("numeric_only", False),
                use_imgloc=opts.get("use_imgloc", False),
            )
        except Exception as e:
            results[task.split(":")[0] if ":" in task else task] = f"error: {e}"

    print(json.dumps(results, ensure_ascii=False, separators=(",", ":")))
    return 0


# ============================================================
# CLI: TEST MODE
# ============================================================
def _setup_adb(adb_path, port):
    subprocess.run(["taskkill", "/F", "/IM", "adb/adb.exe", "/T"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.5)
    subprocess.run([adb_path, "start-server"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.5)
    subprocess.run([adb_path, "connect", f"127.0.0.1:{port}"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.5)
    res = subprocess.run([adb_path, "devices"], capture_output=True, text=True)
    for line in res.stdout.splitlines():
        if "device" in line and not line.startswith("List"):
            return line.split()[0]
    return None


def _capture_adb(adb_path, serial):
    from PIL import Image
    res = subprocess.run([adb_path, "-s", serial, "exec-out", "screencap", "-p"],
                         capture_output=True)
    if res.returncode != 0 or len(res.stdout) < 1000:
        return None
    return Image.open(io.BytesIO(res.stdout)).convert("RGBA")


def _cli_test(args):
    import numpy as np
    if struct.calcsize("P") * 8 != 32:
        print("[-] Test mode cần Python 32-bit (dùng py -3.11-32)")
        return 1

    pid = _get_memu_pid()
    if not pid:
        print("[-] MEmu not found")
        return 1
    print(f"[+] MEmu PID: {pid}")

    engine = get_engine()
    if not engine.available():
        print("[-] DLL load failed")
        return 1
    print("[+] DLL initialized")

    adb_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "adb", "adb.exe"
    )
    if not os.path.exists(adb_path):
        print(f"[-] adb.exe not found: {adb_path}")
        return 1

    serial = _setup_adb(adb_path, ADB_PORT)
    if not serial:
        print("[-] ADB failed")
        return 1
    print(f"[+] ADB Device: {serial}")

    img_rgba = _capture_adb(adb_path, serial)
    if img_rgba is None:
        print("[-] screencap failed")
        return 1
    img_bgr = np.array(img_rgba.convert("RGB"))[:, :, ::-1].copy()
    print(f"[+] Image: {img_bgr.shape[1]}x{img_bgr.shape[0]}")

    print("\n=== Test toàn bộ OCR phổ biến ===")
    print(f"Gold village:    '{engine.gold_village(img_bgr, 48, 69)}'")
    print(f"Elixir village:  '{engine.elixir_village(img_bgr, 48, 98)}'")
    print(f"DE village:      '{engine.dark_elixir_village(img_bgr, 48, 126)}'")
    print(f"Trophy village:  '{engine.trophy_village(img_bgr, 48, 168)}'")
    print(f"Overall damage:  '{engine.overall_damage(img_bgr, 0, 0)}'")
    print(f"Language check:  '{engine.language_check(img_bgr, 0, 0)}'")
    return 0


# ============================================================
# ENTRY
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MyBot.run.dll OCR bridge")
    parser.add_argument("--stdin", action="store_true", help="Đọc PNG từ stdin")
    parser.add_argument("--json", action="store_true", help="Xuất JSON")
    parser.add_argument("--task", action="append", default=[],
                        help="name:lang:x:y:w:h:opts (opts: ns,nb,num,img)")
    args = parser.parse_args()

    if args.stdin or args.json:
        sys.exit(_cli_stdin_batch(args))
    else:
        sys.exit(_cli_test(args))