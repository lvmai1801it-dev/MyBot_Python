# KẾ HOẠCH: YOLO-SEG CHO REDLINE / VÙNG KHÔNG ĐƯỢC THẢ

> Mục tiêu: thay `MyBot.run.dll getRedArea` bằng model YOLO tự train, xác định
> **redline** và **vùng không được thả quân** trên ảnh 860×732.
>
> Kết luận ngắn: **nên dùng YOLO segmentation**, không phải detection.

---

## 1. Vì sao segmentation, không phải detection

| Cách | Output | Có lấy được redline? |
|---|---|---|
| YOLO detection (bbox) | hình chữ nhật | ❌ không đủ cho redline lồi lõm |
| YOLO keypoint | 8–12 điểm | ✅ nhưng label khó |
| **YOLO segmentation** | mask polygon | ✅ **tốt nhất** |
| Building detection + convex hull | hull từ tâm công trình | ⚠️ gần đúng, cần nhiều class |

**Đề xuất:** segment **một class `base_area`** = vùng nằm **trong redline**
(công trình, tường, lõi làng). Biên của mask chính là redline.

```
ảnh 860x732
  → YOLO-seg
  → mask base_area
  → contour lớn nhất
  → approxPolyDP
  → polygon redline
  → offset ra ECD 35%
  → 4 cạnh thả quân
```

---

## 2. Định nghĩa nhãn (rất quan trọng)

### Class 0: `base_area`

- Là **toàn bộ vùng bên trong redline**: nhà, tường, công trình, lõi.
- **Không** tính bãi cỏ, cây, biển, UI.
- Biên ngoài của polygon **trùng với redline**.
- Với làng có công trình lẻ bên ngoài: vẫn bao gồm nếu nằm trong redline.
- Với Builder Base: có thể train riêng hoặc thêm class `bb_base_area`.

### Ảnh negative (không có làng)

- Màn hình load, mây, UI, màn hình nhà mình, lỗi mạng → không label gì.
- Thêm 5–10% ảnh negative để model không đoán bừa.

### Quy tắc label

- Polygon khép kín, đi theo **mép ngoài của redline**.
- Không cần chính xác từng pixel; sai số ±3–5 px chấp nhận được.
- Một ảnh có thể có nhiều polygon nếu làng bị chia cắt bởi UI? Thường chỉ 1.
- Dùng CVAT / Roboflow / Label Studio, export YOLO-seg format.

---

## 3. Thu thập dữ liệu

### Công cụ

```powershell
cd "C:\Users\PC\Downloads\Simplicity v3.50.1\src"
python tools/capture_redline_dataset.py --count 300 --interval 2
```

Lưu ảnh gốc ADB PNG vào:

```
datasets/redline/images/raw/
```

### Cần bao nhiêu ảnh?

| Giai đoạn | Số ảnh label | Ghi chú |
|---|---:|---|
| PoC | 150–300 | đủ xem model có học được không |
| MVP | 500–1000 | đa dạng TH, base layout |
| Ổn định | 1500–3000 | thêm snow, UI, góc nhìn lạ |

### Đa dạng cần có

- TH6 → TH18, mọi layout (compact, ring, spread).
- Base có TH ngoài, TH trong, TH lệch.
- Snow theme / normal theme.
- UI che một phần redline.
- Làng đang tấn công, làng đang scout, làng nhà mình (negative).
- Ảnh hơi mờ, nén, màu khác do emulator.

### 3.1 Auto-capture khi scout (nguồn chính) và attack (tuỳ chọn)

`bootstrap.py` chụp ngay lúc đọc/so sánh tài nguyên; `cycle.py` có thể chụp thêm
lúc attack nếu bật.

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

- `on_scout=true`: base đang hiện đầy đủ, không hiệu ứng → ảnh sạch nhất.
  Chụp cả base tốt (`scout_good`) và base bị skip (`scout_skip`).
- `scout_sample=1.0`: chụp mọi base được kiểm tra; giảm xuống 0.5 nếu quá nhiều.
- `on_attack=false`: tắt chụp lúc thả quân để tránh ảnh trùng/hiệu ứng.
- `only_on_fallback=true` + `success_sample=0.1`: dùng khi bật `on_attack`.
- Ảnh gốc ADB PNG + file `.json` metadata (gold/elixir/dark, `good_base`).
- Có dedup MD5, rate limit, giới hạn `max_files`.
- Ghi PNG chạy trên thread riêng, không block vòng lặp chính.


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

Sau khi có ảnh mới:

```powershell
python tools/split_redline_dataset.py --val-ratio 0.2 --clean
python tools/train_redline_yolo.py --model yolov8n-seg.pt --epochs 80 --imgsz 736
```

---

## 4. Chia dataset

```
datasets/redline/
├── images/
│   ├── raw/          # ảnh gốc chưa label
│   ├── train/        # 80%
│   └── val/          # 20%
├── labels/
│   ├── train/        # .txt YOLO-seg
│   └── val/
└── redline.yaml
```

`redline.yaml` đã có sẵn:

```yaml
path: datasets/redline
train: images/train
val: images/val
names:
  0: base_area
```

Label format:

```
0 x1 y1 x2 y2 x3 y3 ...   # normalized 0..1
```

---

## 5. Train

```powershell
pip install ultralytics
python tools/train_redline_yolo.py --model yolov8n-seg.pt --epochs 150 --imgsz 736 --batch 8 --device 0
```

- Model gốc mặc định: `yolov8n-seg.pt` (có thể đổi sang `yolo11n-seg.pt`).
- `imgsz=736` (chia hết 32) gần với 860×732.
- Nếu GPU yếu: `--batch 4`, `--model yolov8n-seg.pt`.
- Nếu chỉ CPU: train chậm; có thể thuê GPU/Colab.

Kết quả:

```
runs/redline/seg/weights/best.pt
runs/redline/seg/weights/best.onnx
models/redline_seg.pt
models/redline_seg.onnx
```

Script tự copy vào `models/`.

---

## 6. Tích hợp runtime

Đã có:

- `COCbot/vision/redline/yolo.py`
  - `RedlineSegmenter` load `.pt`/`.onnx` qua Ultralytics.
  - `predict_polygon()` → mask → contour → polygon.
  - `polygon_to_edges()` → 4 cạnh `[TR, BR, BL, TL]`.
- `COCbot/vision/redline/detector.py`
  - `get_redline_edges(img, model_path=...)`.
  - Có model → YOLO; không có/lỗi → OpenCV fallback.
- `settings.json`:

```json
"redline_model": "models/redline_seg.pt"
```

- `cycle.py` truyền `cfg['redline_model']`.

**Không còn dùng `test_mybot_dll.py` / `getRedArea`.**

---

## 7. Đánh giá model

### Pixel-level

- Mask IoU / Dice với ground truth.
- mAP50 / mAP50-95 của YOLO-seg.

### Hành vi attack (quan trọng hơn)

- **Drop safety**: sample 100 điểm trên 4 cạnh; đếm số điểm nằm **ngoài**
  `base_area` mask. Mục tiêu > 99%.
- **Coverage**: % chiều dài safe band được dùng.
- **Side accuracy**: so `side_for_point` với nhãn góc thật.
- **Stability**: chạy 100 ảnh liên tiếp, không crash, thời gian ổn định.

### So sánh

| Phương pháp | Tốc độ | Độ chính xác | Rủi ro |
|---|---|---|---|
| OpenCV fallback | ~5 ms | trung bình | không |
| YOLO-seg nano | 20–60 ms CPU | cao nếu đủ data | model drift |
| MyBot DLL | 400–6000 ms | cao | license/kill Android |

---

## 8. Rủi ro & cách xử lý

| Rủi ro | Xử lý |
|---|---|
| Model đoán sai khi UI che | thêm ảnh UI, dùng fallback nếu mask area < ngưỡng |
| Redline mờ/snow | thêm ảnh snow, augment màu |
| Mask dính UI | giới hạn ROI `y < 615`, lọc contour |
| Model quá chậm | dùng `yolo11n-seg` + ONNX + CPU; hoặc GPU |
| Model drift khi game update | thu thập lại 100–200 ảnh, fine-tune |
| Label không nhất quán | viết guideline, review 10% ảnh |
| Nhiều làng trong 1 ảnh | chọn contour lớn nhất gần tâm |

---

## 9. Alternative (nếu segmentation quá khó label)

### Keypoint model

- Label 8–12 điểm dọc redline.
- YOLO pose/keypoint → polygon trực tiếp.
- Ít pixel hơn, nhưng label điểm dễ sai và khó bao quát redline lồi lõm.

### Building detection + convex hull

- Train YOLO detect TH/Eagle/Inferno/XBow/Monolith...
- Convex hull + margin → redline.
- Nhiều class hơn, nhưng có thể tái dùng cho chọn target.

### Hybrid

- YOLO-seg `base_area` + OpenCV refine biên bằng màu đỏ/cam.
- Có thể tăng độ chính xác ở cạnh redline.

---

## 10. Công cụ đã có

```text
tools/capture_redline_dataset.py   # chụp ảnh gốc ADB
tools/setup_redline_yolo.py        # ki?m tra ultralytics/model/dataset
tools/split_redline_dataset.py     # chia train/val
tools/train_redline_yolo.py        # train + export ONNX
tools/eval_redline_yolo.py         # IoU, drop safety, coverage, latency
```

Chi tiết label: `docs/LABELING-GUIDE.md`.

---

## 11. Lộ trình

| Phase | Việc | Thời gian |
|---|---|---|
| 0 | Capture 300 ảnh, label 150 | 1–2 ngày |
| 1 | Train nano-seg, evaluate IoU | 1 ngày |
| 2 | Tích hợp `redline_model`, test attack | 1–2 ngày |
| 3 | Bổ sung 500–1000 ảnh, retrain | 3–7 ngày |
| 4 | ONNX export, tối ưu CPU/GPU | 1 ngày |
| 5 | Thêm class target (TH/drill) nếu cần | 3–5 ngày |

---

## 11. Kết luận

- **Nên dùng YOLO-seg**, class `base_area`.
- Không dùng detection bbox cho redline.
- Giữ OpenCV fallback để bot không chết khi thiếu model.
- Bỏ hẳn `getRedArea`/`test_mybot_dll.py` khỏi runtime.
- Chất lượng phụ thuộc **label**, không phụ thuộc model size.
