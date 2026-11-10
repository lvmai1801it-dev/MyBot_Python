# HƯỚNG DẪN LABEL REDLINE CHO YOLO-SEG

> Mục tiêu: tạo mask `base_area` (vùng trong redline) trên ảnh 860×732.
> Biên mask = redline. Không label trực tiếp "điểm thả".

---

## 1. Chuẩn bị dữ liệu

```powershell
cd "C:\Users\PC\Downloads\Simplicity v3.50.1\src"
python tools/capture_redline_dataset.py --count 300 --interval 2
```

Ảnh nằm ở:

```
datasets/redline/images/raw/
```

Nên có:
- 60% base thường (TH6–TH18).
- 20% base khó: TH ngoài, ring base, spread.
- 10% snow theme.
- 10% ảnh negative: mây, loading, UI, lỗi mạng.

---

## 1.5. Kiểm tra nhanh môi trường

```powershell
python tools/setup_redline_yolo.py
python tools/setup_redline_yolo.py --download-base
```

Script kiểm tra ultralytics, torch, model, dataset và sinh `datasets/redline/redline.local.yaml`.

---

## 2. Tạo project label

### Roboflow (dễ nhất)

1. Tạo project **Instance Segmentation**.
2. Upload `images/raw`.
3. Class: `base_area`.
4. Vẽ polygon.
5. Export **YOLO v8/v11 Segmentation**.
6. Giải nén vào:
   ```
   datasets/redline/images/raw
   datasets/redline/labels/raw
   ```

### CVAT

1. Tạo task, upload ảnh.
2. Label type: **Polygon**.
3. Label `base_area`.
4. Export **YOLO 1.1** / **Ultralytics YOLO Segmentation**.
5. Đưa file `.txt` vào `labels/raw`.

### Label Studio

- Dùng template **Object Detection with Polygons**.
- Export YOLO segmentation.

---

## 3. Quy tắc vẽ polygon

### Đúng

- Polygon khép kín, đi theo **mép ngoài redline**.
- Bao trùm toàn bộ công trình trong redline.
- Không bao bãi cỏ, cây, biển, UI.
- Sai số ±3–5 px chấp nhận được.
- Một polygon cho một làng.

### Sai

- Vẽ theo viền ngoài cùng của bản đồ (yellow border).
- Vẽ bounding box thay polygon.
- Bỏ sót công trình lẻ trong redline.
- Bao luôn thanh quân/UI phía dưới.
- Polygon tự cắt nhau.

### Trường hợp đặc biệt

| Trường hợp | Cách label |
|---|---|
| Redline bị UI che | Ước lượng theo công trình, vẽ phần còn lại |
| TH nằm ngoài redline | Vẫn bao TH nếu nó là phần của base |
| Base có công trình lẻ xa | Bao gồm nếu nằm trong redline |
| Snow theme | Vẫn label bình thường |
| Mây/loading | Không label (negative) |
| Builder Base | Có thể thêm class `bb_base_area` nếu train chung |

---

## 4. Chia train/val

Sau khi label xong, chuyển `.txt` vào `labels/raw` rồi chạy:

```powershell
python tools/split_redline_dataset.py --val-ratio 0.2 --clean
```

Kết quả:

```
images/train, images/val
labels/train, labels/val
```

Kiểm tra số lượng:

```
images=300 labeled=280 missing_label=20
train=224 val=56
```

Ảnh thiếu label sẽ bị bỏ qua. Nên label 100% trước khi split.

---

## 5. Train

```powershell
pip install ultralytics
python tools/train_redline_yolo.py --model yolov8n-seg.pt --epochs 150 --imgsz 736 --batch 8 --device 0
```

Nếu GPU yếu:

```powershell
python tools/train_redline_yolo.py --model yolov8n-seg.pt --epochs 100 --imgsz 640 --batch 4
```

Model được copy vào:

```
models/redline_seg.pt
models/redline_seg.onnx
```

---

## 6. Đánh giá

```powershell
python tools/eval_redline_yolo.py --model models/redline_seg.pt
```

Đọc kết quả:

```
mask IoU     : 0.87
drop safety  : 0.995
coverage     : 0.78
latency      : 35.2 ms/image
```

- **mask IoU** > 0.85: mask khớp redline.
- **drop safety** > 0.99: điểm thả nằm ngoài base.
- **coverage** > 0.7: phủ được phần lớn redline.
- **latency** < 60 ms CPU: chấp nhận được.

Nếu safety thấp: model đang bao quá rộng (mask lấn ra ngoài redline) → cần chỉnh label hoặc tăng `redline_offset_ratio`.

---

## 7. Auto-capture khi scout / attack

`settings.json`:

```json
"auto_capture_dataset": true,
"auto_capture_dir": "datasets/redline/images/raw",
"auto_capture_min_interval_sec": 2.0,
"auto_capture_max_files": 2000,
"auto_capture_on_scout": true,
"auto_capture_scout_sample": 1.0,
"auto_capture_on_attack": false,
"auto_capture_only_on_fallback": true,
"auto_capture_success_sample": 0.1,
"auto_capture_format": "jpg",
"auto_capture_jpeg_quality": 92,
"auto_capture_webp_quality": 90
```

- `on_scout=true`: chụp ngay lúc bot đọc/so sánh tài nguyên. Base đang hiện đầy đủ,
  không có hiệu ứng tấn công → **nguồn dataset chính**.
- `scout_sample=1.0`: chụp mọi base được kiểm tra (good và skip).
- `on_attack=false`: tắt chụp lúc thả quân để tránh trùng/lẫn hiệu ứng.
- `only_on_fallback=true`: nếu bật chụp attack, chỉ chụp khi YOLO fail / chưa có model.
- `success_sample=0.1`: khi YOLO thành công, chỉ chụp 10% frame attack.
- Ảnh tự lưu vào `images/raw` + file `.json` metadata (gold/elixir/dark, good_base...).
- Có dedup MD5, rate limit, max files.


### Nén ảnh dataset

Ảnh PNG gốc ~1.4-1.6 MB. Dùng JPEG/WebP:

```json
"auto_capture_format": "jpg",
"auto_capture_jpeg_quality": 92,
"auto_capture_webp_quality": 90
```

Chuyển ảnh cũ:

```powershell
python tools/compress_dataset.py --dry-run
python tools/compress_dataset.py
python tools/compress_dataset.py --format webp --quality 90
```

Thực tế: 268 MB -> 66 MB (JPEG q92), tiết kiệm ~75%.

Sau một thời gian chạy bot:

```powershell
# label các ảnh mới trong images/raw
python tools/split_redline_dataset.py --val-ratio 0.2 --clean
python tools/train_redline_yolo.py --model yolov8n-seg.pt --epochs 80 --imgsz 736
```

---

## 8. Mẹo tăng chất lượng

1. Label 150 ảnh trước, train thử, xem lỗi.
2. Ưu tiên ảnh fallback (khó) do auto-capture sinh ra.
3. Thêm ảnh negative (không có base) để giảm false positive.
4. Giữ guideline cố định giữa các người label.
5. Review 10% ảnh ngẫu nhiên.
6. Khi game update UI, thu thập 100–200 ảnh mới và fine-tune.

---

## 9. Lỗi thường gặp

| Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|
| Model không detect | thiếu data/negative | thêm ảnh, tăng epochs |
| Mask bao cả UI | label sai | không label UI, clamp y<615 |
| Mask nhỏ hơn redline | label thụt vào | vẽ theo mép ngoài redline |
| Drop safety thấp | mask lấn ra ngoài | tăng offset ratio, chỉnh label |
| Latency cao | model lớn | dùng nano, export ONNX |
| Model chỉ nhận TH cao | data lệch | thêm TH thấp |
