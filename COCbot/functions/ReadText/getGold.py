import cv2
import numpy as np
import pytesseract
import re
import os

IMAGE_PATH = "scout.png"
X, Y, W, H = 21, 65, 102, 29

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def get_gold_strict():
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        print(f"❌ Không tìm thấy ảnh: {IMAGE_PATH}")
        return

    # Cắt ảnh
    roi = img[Y:Y+H, X:X+W]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    # Lọc nhị phân
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    thresh = cv2.bitwise_not(thresh)

    # XÓA ICON: Tô trắng khoảng 30 pixel bên trái để xóa cái vòng tròn đen
    # (Vì icon của bạn nằm ở đầu, xóa nó đi Tesseract sẽ đọc số chuẩn hơn)
    thresh[:, 0:30] = 255

    # THÊM VIỀN TRẮNG (Padding) để Tesseract không bị cắt xén chữ
    thresh = cv2.copyMakeBorder(thresh, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)

    # Phóng to
    thresh = cv2.resize(thresh, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite("debug_gold_final.png", thresh)

    # Thử nhiều chế độ đọc, chế độ nào ra nhiều số nhất thì lấy
    best_text = ""
    
    for psm in (7, 6, 8, 13):
        text = pytesseract.image_to_string(
            thresh, 
            config=f"--psm {psm} -c tessedit_char_whitelist=0123456789"
        ).strip()
        
        # Lấy toàn bộ số
        digits = re.sub(r'[^\d]', '', text)
        
        # Nếu đọc được nhiều số hơn kết quả cũ, cập nhật
        if len(digits) > len(best_text):
            best_text = digits

    print(f"--- Số đọc được: '{best_text}' ---")
    
    if best_text and len(best_text) >= 5:  # Gold thường từ 5-6 chữ số
        print(f"✅ Gold: {int(best_text):,}")
    else:
        print("❌ Không đọc được hoặc đọc sai. Hãy xem file debug_gold_final.png.")

if __name__ == "__main__":
    get_gold_strict()