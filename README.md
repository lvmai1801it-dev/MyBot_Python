# MRB (Python)

Bot tự động Clash of Clans chạy qua ADB, giao diện PyQt5 (480×670, 6 tab).

## Chạy

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Yêu cầu: Python 3.10–3.13, ADB (đã kèm sẵn tại `COCbot/adb/`), emulator
MEmu / LDPlayer / BlueStacks. Tùy chọn: Tesseract-OCR (một số đường OCR
fallback; engine chính là PaddleOCR cài qua pip).

## Tính năng
- Start tự dò MEmu: đang online → dùng ngay; có cài mà chưa mở → bot tự
  khởi động; không cần chọn giả lập mỗi lần (dialog thủ công chỉ hiện khi
  không tìm thấy MEmu — các giả lập khác để sau).
- Farm tự động: tìm trận → đọc loot → đạt ngưỡng mới đánh → thả theo
  redline → chờ kết thúc → stats → về nhà.
- Redline: model ONNX deploy-zone (3 lớp deployable / no_deploy /
  interface) là nguồn chính; fallback OpenCV nếu không có
  `models/deploy_zone.onnx`. Mọi điểm thả được validate theo mask trước
  khi tap, thả sót thì verify-redrop (3 pass) + final sweep quét 11 slot.
- Chọn hướng thả: 1 / 2 / Nửa Trên-Dưới / Cả 4 hướng / Ngẫu nhiên (mỗi
  trận random 1 hướng). Spell opt-in qua checkbox "Thả spell".
- Auto-upgrade mỗi cycle: tick target trong Village → Upgrade, bot tự
  mở Build panel, nâng theo số builder free (Buildings & Heroes / Army /
  Equipment / Pets), wall nâng qua Build panel theo màu giá.
- Train quân: Smart Train / Quick Train, quản lý preset.
- Xin quân qua Clan Chat; Clan Games và Clan Capital.
- Chuyển account bằng shared_prefs (adbd root): số trận riêng từng
  account, tự chuyển khi đầy 3 kho hoặc hẹn giờ.

## Tài sản không kèm theo repo (giữ local)

`models/*.onnx|*.pt` (model cá nhân), `settings.json` (tạo lại mặc định
lần chạy đầu), `profiles/` (tài khoản), `datasets/`, `docs/`, `walls/`.
Bot vẫn chạy được khi thiếu các mục này: redline fallback OpenCV, config
lấy default.

## Cấu trúc chính

```text
run.py                     # entry point duy nhất
COCbot/
├── app/                   # bootstrap (bot_loop/one_cycle) + upgrade_hook
├── attack/                # capture -> redline -> plan -> drop (verify-redrop)
├── emulator/              # MEmu / LDPlayer / BlueStacks
├── game/                  # village, battle, clan, training, account
├── gui/                   # MainWindow + tabs + theme
├── platform/              # ADB (exe tại COCbot/adb/), tap guard
├── vision/                # capture, OCR số, redline (ONNX + OpenCV)
├── core/                  # thư viện pure cho features/village
├── models/                # dataclass pure (Detection, Frame, ...)
└── features/village/      # auto-upgrade (Build panel) + ResourceReader
tools/                     # dataset/YOLO, crop, audit, smoke, test side modes
Templates/                 # template ảnh runtime (kèm đủ theo repo)
```

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -t .
```

106 test phủ config/model/adb/vision/redline (ONNX mask logic)/upgrades/
wall-panel/planner/runner + architecture rules.
