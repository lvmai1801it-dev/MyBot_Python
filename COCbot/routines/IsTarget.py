# ==== COCbot/routines/IsTarget.py ====
import os
import cv2
import sys
import subprocess
import numpy as np
import pytesseract
import re
from datetime import datetime

import core.paths
from COCbot.emulator.adb_config import ADB_BIN
from utils.screenshot_utils import take_screenshot
from utils.unicode import imread_unicode
from core.coords import RES_GOLD_ROI, RES_ELIXIR_ROI, RES_DE_ROI

# Cấu hình Tesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
SCRIPT_DIR = str(core.paths.SRC_DIR)

# Định dạng tọa độ chuẩn của bạn: (X, Y, W, H)
coords = {
    'Gold': RES_GOLD_ROI,
    'Elixir': RES_ELIXIR_ROI,
    'Dark Elixir': RES_DE_ROI,
}

BASE_DEBUG_DIR = os.path.join(SCRIPT_DIR, "debug_ocr")


def _save_debug_image(img, filepath):
    """Hàm lưu ảnh debug chống lỗi Unicode."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        if cv2.imwrite(filepath, img):
            return True
    except Exception:
        pass
    
    try:
        ok, encoded = cv2.imencode('.png', img)
        if ok:
            with open(filepath, 'wb') as f:
                f.write(encoded.tobytes())
            return True
    except Exception as e:
        print(f"    ❌ LỖI lưu ảnh {filepath}: {e}")
    return False


def extract_loot_number(crop_img, label="unknown", debug_dir=None):
    """Hàm OCR tối ưu, nhận vào mảng ảnh (numpy array)."""
    debug = debug_dir is not None
    
    if crop_img is None or crop_img.size == 0:
        if debug:
            print(f"    [{label}] ❌ Ảnh cắt bị RỖNG!")
        return "0"

    # --- DEBUG BƯỚC 1: Lưu ảnh gốc vừa cắt ---
    if debug:
        print(f"    [{label}] Ảnh gốc shape: {crop_img.shape}")
        _save_debug_image(crop_img, os.path.join(debug_dir, f"{label}_1_raw.png"))

    # 1. Chuyển xám và lọc nhị phân
    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    thresh = cv2.bitwise_not(thresh)

    # 2. XÓA ICON bên trái (Tô trắng 30 pixel đầu)
    if thresh.shape[1] > 30:
        thresh[:, 0:30] = 255

    # 3. THÊM VIỀN TRẮNG (Padding)
    thresh = cv2.copyMakeBorder(thresh, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)

    # 4. Phóng to 4 lần
    thresh = cv2.resize(thresh, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)

    if debug:
        _save_debug_image(thresh, os.path.join(debug_dir, f"{label}_2_processed.png"))

    # 5. Quét đa chế độ (psm) để tìm kết quả tốt nhất
    best_text = ""
    for psm in (7, 6, 8, 13):
        try:
            text = pytesseract.image_to_string(
                thresh, 
                config=f"--psm {psm} -c tessedit_char_whitelist=0123456789"
            ).strip()
        except Exception as e:
            if debug:
                print(f"    [{label}] psm={psm} ❌ Lỗi Tesseract: {e}")
            continue
        
        digits = re.sub(r'[^\d]', '', text)
        
        if debug:
            print(f"    [{label}] psm={psm} -> Raw: '{text}' | Digits: '{digits}'")
        
        if len(digits) > len(best_text):
            best_text = digits

    return best_text if best_text else "0"


def extract_resources(debug=False):
    os.chdir(SCRIPT_DIR)
    
    debug_dir = None
    if debug:
        # Tạo thư mục con theo timestamp (VD: debug_ocr/20231107_200300)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_dir = os.path.join(BASE_DEBUG_DIR, timestamp)
        os.makedirs(debug_dir, exist_ok=True)
        
        print(f"\n{'='*60}")
        print(f"=== DEBUG MODE (Định dạng X, Y, W, H) ===")
        print(f"Thư mục debug: {debug_dir}")
        print(f"{'='*60}")

    # Chụp ảnh
    try:
        take_screenshot(output_path='enemy_resources.png')
    except Exception as e:
        print(f"[ERROR] take_screenshot lỗi: {e}")
        return '0', '0', '0'

    if not os.path.exists('enemy_resources.png'):
        print(f"[ERROR] File 'enemy_resources.png' KHÔNG được tạo!")
        return '0', '0', '0'

    img = imread_unicode('enemy_resources.png')
    if img is None:
        print("[ERROR] Không thể đọc ảnh enemy_resources.png")
        return '0', '0', '0'

    h_img, w_img = img.shape[:2]

    if debug:
        print(f"Kích thước màn hình chụp: W={w_img}, H={h_img}")
        # Lưu ảnh chụp màn hình gốc để đối chiếu
        _save_debug_image(img, os.path.join(debug_dir, "full_screenshot.png"))
        # Tạo bản copy để vẽ khung
        debug_full = img.copy()

    results = {}

    if debug:
        print("\n=== BẮT ĐẦU QUÁ TRÌNH ĐỌC TÀI NGUYÊN ===")

    for label, (x, y, w, h) in coords.items():
        if debug:
            print(f"\n[{label}] Tọa độ cắt (X,Y,W,H): X={x}, Y={y}, W={w}, H={h}")

        # Cắt ảnh đúng chuẩn (X, Y, W, H)
        raw_crop = img[y:y+h, x:x+w]
        
        # Vẽ khung lên ảnh gốc để xem đã cắt đúng vùng chưa
        if debug:
            color = (0, 255, 0) if label == 'Gold' else (0, 0, 255) if label == 'Elixir' else (255, 0, 0)
            cv2.rectangle(debug_full, (x, y), (x+w, y+h), color, 2)
            cv2.putText(debug_full, label, (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        num_value = extract_loot_number(raw_crop, label=label, debug_dir=debug_dir)
        results[label] = num_value

    if debug:
        # Lưu ảnh có vẽ khung để dễ nhìn
        _save_debug_image(debug_full, os.path.join(debug_dir, "full_screenshot_boxes.png"))
        print(f"\n👉 Đã lưu TẤT CẢ ảnh debug vào: {debug_dir}")

    return results['Gold'], results['Elixir'], results['Dark Elixir']


if __name__ == '__main__':
    gold, elixir, dark_elixir = extract_resources(debug=True)
    
    print("\n" + "=" * 60)
    print("=== KẾT QUẢ CUỐI CÙNG ===")
    print(f'Gold:        {gold}')
    print(f'Elixir:      {elixir}')
    print(f'Dark Elixir: {dark_elixir}')
    print("=" * 60)