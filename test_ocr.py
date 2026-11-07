# ==== test_ocr_v2.py — Test phương pháp Gentle Upscale ====
import sys
import os
import cv2
import numpy as np

# Khởi tạo PaddleOCR
try:
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(
        text_detection_model_name=None,
        text_recognition_model_name="PP-OCRv6_small_rec",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        enable_mkldnn=False, # Bắt buộc để tránh lỗi trên CPU
        lang='en'
    )
    print("✅ PaddleOCR OK")
except Exception as e:
    print(f"❌ Lỗi PaddleOCR: {e}")
    sys.exit(1)

def gentle_upscale_bgr(crop_bgr):
    """Phóng to ảnh BGR gốc trực tiếp, không nhị phân hóa."""
    # Phóng to 6 lần bằng INTER_CUBIC để làm mượt các hạt pixel
    up = cv2.resize(crop_bgr, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC)
    return up

def gentle_gray_otsu(crop_bgr):
    """Chuyển xám, phóng to, dùng Otsu tự động tìm ngưỡng tốt nhất."""
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    up = cv2.resize(gray, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC)
    
    # Otsu tự động tính toán ngưỡng tối ưu nhất
    _, thresh = cv2.threshold(up, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Đảm bảo chữ đen nền trắng (Paddle thích màu này)
    if np.mean(thresh) < 127:
        thresh = cv2.bitwise_not(thresh)
    return thresh

def cut_x_and_upscale(crop_bgr):
    """Cắt bỏ chữ 'x' (15px bên trái), sau đó phóng to."""
    if crop_bgr.shape[1] > 30:
        crop_bgr = crop_bgr[:, 15:, :]
    return gentle_upscale_bgr(crop_bgr)

def run_ocr(img, name):
    try:
        results = ocr.predict(img)
        if results:
            for res in results:
                texts = getattr(res, 'rec_texts', None) or res.get('rec_texts', [])
                scores = getattr(res, 'rec_scores', None) or res.get('rec_scores', [])
                if texts:
                    for t, s in zip(texts, scores):
                        # Lọc chỉ lấy số
                        digits = ''.join(filter(str.isdigit, t.replace('o','0').replace('O','0')))
                        print(f"  -> {name}: '{t}' (conf={s:.2f}) => Số: {digits}")
                        return
        print(f"  -> {name}: Không đọc được")
    except Exception as e:
        print(f"  -> {name}: Lỗi predict - {e}")

def main():
    if len(sys.argv) < 2:
        print("Cách dùng: python test_ocr_v2.py x20.png")
        return

    img_path = sys.argv[1]
    crop_bgr = cv2.imread(img_path)
    if crop_bgr is None:
        print("❌ Không đọc được ảnh.")
        return

    os.makedirs("test_output_v2", exist_ok=True)

    # 1. Ảnh BGR gốc phóng to (Không nhị phân hóa)
    img1 = gentle_upscale_bgr(crop_bgr)
    cv2.imwrite("test_output_v2/1_gentle_bgr.png", img1)
    run_ocr(img1, "Gentle BGR (Chỉ phóng to)")

    # 2. Ảnh Xám dùng Otsu tự động
    img2 = gentle_gray_otsu(crop_bgr)
    cv2.imwrite("test_output_v2/2_gentle_otsu.png", img2)
    run_ocr(img2, "Gentle Otsu (Tự động)")

    # 3. Cắt chữ X, phóng to BGR
    img3 = cut_x_and_upscale(crop_bgr)
    cv2.imwrite("test_output_v2/3_cut_x_bgr.png", img3)
    run_ocr(img3, "Cắt chữ X + BGR")

    print("\n📸 Đã lưu ảnh xử lý vào thư mục test_output_v2/")

if __name__ == "__main__":
    main()