# ==== routines/smart_train_ocr.py ====
import cv2
from utils.ocr_reader import reader

PADDLE_AVAILABLE = False
_ocr_engine = None
try:
    from paddleocr import PaddleOCR
    _ocr_engine = PaddleOCR(
        text_detection_model_name=None,
        text_recognition_model_name="PP-OCRv6_small_rec",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        enable_mkldnn=False,
        lang='en'
    )
    PADDLE_AVAILABLE = True
    print("[OCR] ✅ PaddleOCR PP-OCRv6_small (Gentle Upscale)")
except Exception as e:
    print(f"[OCR] ⚠️ Không có PaddleOCR ({type(e).__name__}). Dùng EasyOCR dự phòng.")

def _preprocess_for_ocr(crop_bgr):
    return cv2.resize(crop_bgr, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC)

def _read_with_paddle(crop_bgr):
    try:
        img = _preprocess_for_ocr(crop_bgr)

        results = _ocr_engine.predict(img)
        if not results:
            return 0

        for res in results:
            texts = getattr(res, 'rec_texts', None) or res.get('rec_texts', [])
            scores = getattr(res, 'rec_scores', None) or res.get('rec_scores', [])
            if not texts:
                continue

            best_idx = max(range(len(scores)), key=lambda i: scores[i]) if scores else 0
            best_text = texts[best_idx] if best_idx < len(texts) else texts[0]
            best_score = scores[best_idx] if best_idx < len(scores) else 0.0

            fixed = best_text.replace('o', '0').replace('O', '0')
            digits = ''.join(filter(str.isdigit, fixed))

            print(f"      [Paddle] '{best_text}' score={best_score:.2f} → '{digits}'")

            if digits:
                return int(digits)
        return 0
    except Exception as e:
        print(f"      [Paddle] Lỗi: {e}")
        return _read_with_easyocr(crop_bgr)

def _read_with_easyocr(crop_bgr):
    img = _preprocess_for_ocr(crop_bgr)

    best_result = 0
    best_conf = 0.0
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        results = reader.readtext(gray, allowlist='0123456789', detail=1, paragraph=True)
        for item in results:
            text = item[1] if len(item) >= 2 else ""
            conf = item[2] if len(item) >= 3 else 0.0
            digits = ''.join(filter(str.isdigit, str(text)))
            if digits and conf > best_conf:
                best_conf = conf
                best_result = int(digits)
    except Exception:
        pass

    if best_result > 0:
        print(f"      [EasyOCR] Kết quả={best_result} conf={best_conf:.2f}")
    return best_result

def read_number_ocr(crop_bgr):
    if crop_bgr is None or crop_bgr.size == 0:
        return 0
    if PADDLE_AVAILABLE:
        return _read_with_paddle(crop_bgr)
    return _read_with_easyocr(crop_bgr)

def read_troop_count(roi_img, match_loc, tpl_size):
    w, h = tpl_size
    x, y = match_loc
    ocr_y1, ocr_y2 = 10, 27
    ocr_x1 = max(0, x - 2)
    ocr_x2 = min(roi_img.shape[1], x + w + 5)
    num_crop = roi_img[ocr_y1:ocr_y2, ocr_x1:ocr_x2]
    return read_number_ocr(num_crop)