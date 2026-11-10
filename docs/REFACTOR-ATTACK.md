# REFACTOR — Attack pipeline (YOLO redline + MyBot-style layers)

> Chỉ tái cấu trúc **attack/redline** của Simplicity. Không đổi entry point,
> GUI, ADB, OCR, train, routine. `COCbot/attack/api.py` giữ làm shim.

---

## 1. Cấu trúc hiện tại

Xem `docs/ARCHITECTURE.md` để có cây thư mục đầy đủ. Tóm tắt phần attack:

```text
COCbot/
├── attack/
│   ├── api.py        # entry point: run_attack / init_device
│   ├── cycle.py      # một chu kỳ: capture -> redline -> plan -> drop -> verify
│   ├── planner.py    # offset redline + chọn cạnh
│   ├── dropper.py    # thả quân/hero/CC/spell
│   ├── device.py     # tap / uiautomator2 / slot
│   └── army.py       # chuẩn bị quân (PrepareAttack cũ)
└── vision/redline/
    ├── detector.py   # get_redline_edges_ex: YOLO-seg + OpenCV fallback
    ├── geometry.py   # ECD/DCD, offset, side_for_point
    ├── yolo.py       # RedlineSegmenter
    └── dataset_capture.py
```

| File | Trách nhiệm | Tương đương MyBot |
|---|---|---|
| `attack/cycle.py` | capture -> redline -> plan -> drop -> verify | `AttackCycle`, `AttackMain` |
| `attack/planner.py` | offset, chọn 1/2/3/4 cạnh | side selection + RedArea cleanup |
| `attack/dropper.py` | thả quân/hero/CC/spell | `LaunchTroop`, `DropOrderTroops` |
| `vision/redline/detector.py` | YOLO-seg + OpenCV fallback | `_GetRedArea` |
| `vision/redline/yolo.py` | mask -> polygon -> 4 cạnh | model thay DLL |
| `attack/device.py` | tap, slot, badge | `Click`, `AndroidClick` |
| `vision/redline/geometry.py` | ECD/DCD, point-in-poly, offset | `GetAreaForPoint`, diamond |

---

## 2. Luồng attack

```text
run_attack(cfg)
  ├─ capture ảnh (bỏ frame mây trắng)
  ├─ get_redline_edges(img, model_path=cfg.redline_model)
  │    ├─ YOLO-seg: mask base_area → contour → polygon → 4 cạnh
  │    └─ fallback: OpenCV isometric
  ├─ build_attack_plan(edges, cfg, target_xy)
  │    ├─ offset_edges_to_outer(ECD, ratio=0.35)
  │    ├─ side_for_point(target)
  │    └─ choose_edges(side, nb_sides)
  ├─ prepare_attack(img)
  ├─ drop_on_active_edges(active_edges, ...)
  ├─ drop_heroes_v2(primary_edge)
  ├─ drop_cc(primary_edge)
  ├─ drop_spells(active_edges)
  └─ final sweep
```

---

## 3. Redline: YOLO-seg, không dùng DLL

`MyBot.run.dll getRedArea` đã bị bỏ khỏi runtime vì:

- gọi `DetectRedArea.checkLicence()` → `ProcessUtils.closeAndroid()` → `Process.Kill()`;
- flaky trong host Python (`Access denied`);
- có thể kill emulator nếu chạy admin.

Thay bằng:

```json
"redline_model": "models/redline_seg.pt"
```

- Có model → `RedlineSegmenter` (Ultralytics) trả mask `base_area`.
- Không có model / lỗi → OpenCV fallback.
- `test_mybot_dll.py` chỉ còn là file tham khảo, **không import**.

Xem chi tiết train/label: `docs/YOLO-REDLINE-PLAN.md`.

---

## 4. Vì sao segmentation

| Cách | Redline? |
|---|---|
| Detection bbox | ❌ không đủ |
| Keypoint 8–12 điểm | ✅ nhưng label khó |
| **Segmentation `base_area`** | ✅ **khuyến nghị** |
| Building detection + hull | ⚠️ gần đúng |

Mask `base_area` = vùng trong redline. Contour lớn nhất → polygon redline.

---

## 5. Thay đổi so với bản cũ

| Trước | Sau |
|---|---|
| `attacks.py` 26 KB monolith | tách `cycle/planner/dropper/redline/device` |
| `getRedArea` DLL | YOLO-seg + OpenCV fallback |
| redline parser `TL#BL#BR#TR` | giữ nguyên (4 phần) |
| hardcode `edges[3]/edges[2]` | `drop_on_active_edges(active_edges)` |
| offset 40 px fallback | `offset_edges_to_outer(ECD, 0.35)` |
| không có target side | `side_for_point` + `choose_edges` |
| không có YOLO | `redline_yolo.py` + training tools |

---

## 6. Cấu hình

`settings.json`:

```json
"redline_model": "models/redline_seg.pt"
```

Để trống `""` nếu chỉ muốn OpenCV fallback.

Tuỳ chọn target:

```python
cfg['target_xy'] = (430, 366)
```

Planner sẽ chọn cạnh theo `TL/TR/BL/BR`.

---

## 7. Hiệu năng

| Phương pháp | Tốc độ | Ghi chú |
|---|---|---|
| OpenCV fallback | ~5 ms | luôn có |
| YOLO-seg nano CPU | 20–60 ms | tùy máy |
| YOLO-seg GPU | 5–20 ms | nếu có GPU |
| MyBot DLL | 400–6000 ms | đã bỏ |

---

## 8. Kiểm thử

- `py_compile` toàn bộ file: OK.
- Import shim: OK.
- `side_for_point` khớp `GetAreaForPoint`:
  `(430,366)=BR`, `(300,300)=TL`, `(500,300)=TR`,
  `(300,450)=BL`, `(500,450)=BR`, `(100,200)=""`.
- OpenCV fallback: `edges=[5,5,5,5]`.
- YOLO bridge: chờ model `models/redline_seg.pt` để test thật.

---

## 9. Việc cần làm

1. Capture 300–500 ảnh: `python tools/capture_redline_dataset.py`.
2. Label polygon `base_area` bằng CVAT/Roboflow.
3. Train: `python tools/train_redline_yolo.py`.
4. Test model trên ảnh val, đo IoU + drop safety.
5. Copy `best.pt`/`best.onnx` vào `models/redline_seg.pt`.
6. Chạy thử attack trên làng test.

---

## 10. Rollback

- Khôi phục `attacks.py` cũ từ git/backup.
- Xóa `COCbot/attack/{device,dropper,planner,cycle}.py + COCbot/vision/redline/detector.py`.
- Xóa `COCbot/vision/redline/geometry.py`, `redline_yolo.py`.
- Khôi phục `test_mybot_dll.py`, `screenshot_utils.py`, `settings.json`.
