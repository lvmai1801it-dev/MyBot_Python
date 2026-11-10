# OCR đọc tài nguyên (Gold / Elixir / Dark)

## 1. Kết luận nhanh

Dùng **PaddleOCR (PP-OCRv6)** cho các con số trong game. Đây là engine đọc đúng
nhất trên ảnh thật 860×732, kể cả khi số nằm trên thanh tài nguyên sáng màu.

| Engine | Home Gold | Home Elixir | Home DE | Scout Gold | Scout Elixir | Scout DE |
|---|---|---|---|---|---|---|
| **PaddleOCR PP-OCRv6** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Tesseract (ROI cũ) | ❌ thiếu số | ❌ đọc nhầm hàng DE | ❌ | ✅ | ✅ | ✅ |
| Tesseract + white-mask | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| EasyOCR | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| RapidOCR (đã thử) | ❌ tách số | ❌ | ❌ | ❌ | ❌ | ❌ |

Ground truth dùng để test:

```text
home  : gold=5577555  elixir=5803412  de=43892
scout : gold=817090   elixir=650888   de=7563
```

PaddleOCR trả đúng **6/6**, confidence `0.98–0.9999`.

## 2. Module

```text
COCbot/vision/read_text/numbers.py
```

API:

```python
from COCbot.vision.read_text.numbers import read_number, read_region

value = read_number(crop_bgr)          # int | None
value = read_region(img, (x1,y1,x2,y2))
```

- PaddleOCR được khởi tạo **lazy** (không load lúc import).
- Nếu PaddleOCR lỗi/không có → tự fallback Tesseract với white-mask.
- Trên Windows, `torch` phải được import **trước PyQt5**. `COCbot/gui/app.py`
  làm việc này ở đầu file; nếu đảo thứ tự, torch `c10.dll` lỗi `WinError 1114`
  và PaddleOCR sẽ fallback Tesseract.

## 3. ROI đã sửa

`COCbot/app/coords.py`:

```python
HR_GOLD_REGION   = (660, 12, 828, 46)
HR_ELIXIR_REGION = (660, 45, 828, 80)
HR_DE_REGION     = (660, 79, 828, 114)
```

Lỗi cũ:

- `HR_GOLD_REGION=(670,20,808,55)` cắt mất chữ số cuối.
- `HR_ELIXIR_REGION=(670,89,823,143)` đọc nhầm hàng **Dark Elixir** thay vì Elixir.
- ROI cũ bao luôn icon coin/gem ở mép phải; PaddleOCR đôi khi đọc ánh sáng
  của icon thành thêm một chữ số. ROI mới dừng ở `x=828`.

ROI scout (`RES_GOLD_ROI`, `RES_ELIXIR_ROI`, `RES_DE_ROI`) vẫn đúng vì đọc
"Available Loot" ở góc trên-trái; `extract_loot_number()` bỏ 30 px icon bên trái
trước khi đưa vào OCR.

## 4. Nơi đã áp dụng

| File | Dùng cho |
|---|---|
| `game/battle/target.py` | loot địch trên scout screen |
| `game/village/home_routine.py` | gold/elixir/DE ở nhà |
| `game/battle/helpers.py` | resources gained sau trận |
| `game/training/smart_train_ocr.py` | số lượng quân trong smart train |

## 5. Kiểm tra nhanh

```powershell
.venv\Scripts\python.exe -c "from COCbot.vision.read_text.numbers import read_region; import cv2; img=cv2.imread('home.png'); print(read_region(img,(655,12,850,46)), read_region(img,(655,45,850,80)), read_region(img,(655,79,850,114)))"
```

Kết quả đúng phải khớp số trên màn hình.

## 6. Nếu vẫn đọc sai

1. Chụp lại màn hình, kiểm tra ROI có cắt đủ số không.
2. Tăng vùng ROI thêm 5–10 px mỗi phía.
3. Kiểm tra log `[OCR] PaddleOCR unavailable` — nếu có, Paddle bị lỗi nên đang fallback Tesseract.
4. Với loot địch, đảm bảo đang ở màn hình **scout** (có chữ `Available Loot:`).
