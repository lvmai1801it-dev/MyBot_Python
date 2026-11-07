# ==== routines/IsTarget.py ====
import os
import cv2
import sys
import subprocess

import core.paths
from routines.smart_train_ocr import read_number_ocr
from emulators.adb_config import ADB_BIN
from utils.screenshot_utils import take_screenshot
from utils.unicode import imread_unicode
from core.coords import RES_GOLD_ROI, RES_ELIXIR_ROI, RES_DE_ROI

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
SCRIPT_DIR = str(core.paths.SRC_DIR)

coords = {
    'Gold': RES_GOLD_ROI,
    'Elixir': RES_ELIXIR_ROI,
    'Dark Elixir': RES_DE_ROI,
}

def preprocess_for_scout(crop_img):
    """
    Tiền xử lý tối ưu: Chuyển xám, làm mờ nhẹ và dùng Otsu Threshold tự động.
    """
    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    
    # Dùng THRESH_OTSU tự động thích ứng với ánh sáng màn hình
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Chuyển ngược lại thành ảnh 3 kênh màu (BGR) cho PaddleOCR
    return cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)

def extract_resources():
    os.chdir(SCRIPT_DIR)
    
    take_screenshot(output_path='enemy_resources.png')
    img = imread_unicode('enemy_resources.png')
    if img is None:
        print("[ERROR] Không thể đọc ảnh enemy_resources.png")
        return '0', '0', '0'
        
    h_img, w_img = img.shape[:2]
    results = {}

    for label, (x1, y1, x2, y2) in coords.items():
        # Căn chỉnh tọa độ (clamp) để đảm bảo không bị lỗi tràn viền màn hình
        x1c = max(0, x1)
        y1c = max(0, y1)
        x2c = min(w_img, x2)
        y2c = min(h_img, y2)
        
        raw_crop = img[y1c:y2c, x1c:x2c]
        if raw_crop.size == 0:
            results[label] = '0'
            continue
            
        # Tiền xử lý trực tiếp không lưu file debug
        processed_crop = preprocess_for_scout(raw_crop)
        
        # Gọi hàm OCR trực tiếp
        num_value = read_number_ocr(processed_crop)
        results[label] = str(num_value)

    return results['Gold'], results['Elixir'], results['Dark Elixir']

if __name__ == '__main__':
    gold, elixir, dark_elixir = extract_resources()
    print(f'Gold:        {gold}')
    print(f'Elixir:      {elixir}')
    print(f'Dark Elixir: {dark_elixir}')