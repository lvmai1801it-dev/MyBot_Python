# MyBot PHMOD v15.9 (Python)

Bot tự động Clash of Clans chạy qua ADB, giao diện PyQt5 theo thiết kế mới
(480×670, 6 tab).

## Chạy

```powershell
cd "C:\Users\PC\Downloads\Simplicity v3.50.1\src"
.\.venv\Scripts\python.exe run.py
```

Yêu cầu: Python 3.13, ADB (đi kèm trong `adb/`), emulator MEmu/LDPlayer/BlueStacks.

## Tính năng

- Farm tự động: tìm trận, đọc tài nguyên, thả quân, leo wall.
- Train quân: Smart Train / Quick Train, quản lý preset.
- Xin quân qua Clan Chat (không cần root).
- Clan Games và Clan Capital.
- Chuyển account: Supercell ID hoặc Shared_prefs (adbd root).
  - Mỗi account có số trận riêng.
  - Tự chuyển khi đầy 3 kho (template matching).
  - Hẹn giờ chuyển theo số phút.
- Redline: OpenCV fallback; hỗ trợ YOLO-seg nếu có `models/redline_seg.pt`.
- Tự thu ảnh dataset khi scout/attack (JPEG + JSON metadata).

## Cấu trúc chính

```text
run.py                     # entry point
COCbot/
├── app/                   # bootstrap, config, state, coords, stats
├── attack/                # capture -> redline -> plan -> drop
├── emulator/              # MEmu / LDPlayer / BlueStacks
├── game/                  # village, battle, clan, training, account
├── gui/                   # MainWindow + tabs + theme
├── platform/              # ADB, tap guard, unicode helpers
└── vision/                # capture, OCR, redline (OpenCV + YOLO)
tools/                     # dataset / YOLO tooling
datasets/redline/          # ảnh + label (gitignored)
docs/                      # ARCHITECTURE, ACCOUNT-SWITCH, LABELING-GUIDE...
```

## Giao diện

6 tab: **Log**, **Village** (General + Accounts), **Attack plan**,
**Bot settings** (Clan Games / Clan Capital / Debug), **Statistics**, **About**.

## Tài liệu

- `docs/ARCHITECTURE.md` — kiến trúc package.
- `docs/ACCOUNT-SWITCH.md` — chuyển account, quota trận, đầy kho.
- `docs/LABELING-GUIDE.md` — label dataset cho YOLO redline.
- `docs/OCR.md` — OCR tài nguyên.
