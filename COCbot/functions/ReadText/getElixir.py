import cv2
import numpy as np
import pytesseract
import re
import os

IMAGE_PATH = "scout.png"

# TỌA ĐỘ DUY NHẤT CỦA ELIXIR
X, Y, W, H = 20, 92, 107, 33

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def get_elixir():
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        print(f"❌ Không tìm thấy ảnh: {IMAGE_PATH}")
        return

    # 1. Cắt chính xác khung Elixir
    roi = img[Y:Y+H, X:X+W]

    # 2. Xử lý ảnh (Lọc lấy chữ trắng)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 190, 255, cv2.THRESH_BINARY)
    
    # Đảo ngược màu (Chữ đen, nền trắng) cho Tesseract dễ đọc
    thresh = cv2.bitwise_not(thresh)

    # 3. Thêm viền trắng (Padding) xung quanh ảnh
    # Viền trái rộng 50px để bảo vệ con số "2" không bị cắt mất
    thresh = cv2.copyMakeBorder(thresh, 30, 30, 50, 30, cv2.BORDER_CONSTANT, value=255)

    # 4. Phóng to 4 lần
    thresh = cv2.resize(thresh, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)

    # Lưu ảnh debug
    cv2.imwrite("debug_elixir.png", thresh)

    # 5. OCR (psm 7 chỉ đọc 1 dòng)
    text = pytesseract.image_to_string(
        thresh, 
        config="--psm 7 -c tessedit_char_whitelist=0123456789"
    ).strip()

    print(f"--- Tesseract đọc Elixir: '{text}' ---")

    # 6. Lấy số
    digits = re.sub(r'[^\d]', '', text)
    if digits:
        print(f"✅ Elixir: {int(digits):,}")
    else:
        print("❌ Không đọc được Elixir. Hãy mở file 'debug_elixir.png' kiểm tra.")

if __name__ == "__main__":
    get_elixir()