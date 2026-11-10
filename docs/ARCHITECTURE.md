# KIẾN TRÚC DỰ ÁN (MyBot-like layout)

Tài liệu này mô tả cấu trúc sau refactor. Mục tiêu: tách lớp rõ ràng, import một chiều,
dễ test từng phần, giữ nguyên hành vi bot.

## 1. Cây thư mục

```text
src/
├── run.py                  # entry point chính (GUI)
├── settings.json           # cấu hình runtime (gitignored)
├── COCbot/
│   ├── app/                # lõi ứng dụng: config, state, paths, coords, stats
│   │   ├── bootstrap.py    # vòng lặp chính (trước là core/main.py)
│   │   ├── config.py
│   │   ├── controls.py     # start/stop/pause
│   │   ├── coords.py
│   │   ├── paths.py
│   │   ├── state.py        # host, emulator_key, ld_index, events
│   │   ├── stats.py
│   │   ├── army_presets.py
│   │   ├── troop_registry.py
│   │   ├── updater.py
│   │   └── version.py
│   ├── platform/           # tương tác nền tảng
│   │   ├── adb_config.py
│   │   ├── adb_utils.py
│   │   ├── ahk.py
│   │   └── unicode.py
│   ├── emulator/           # quản lý giả lập
│   │   ├── setup.py
│   │   ├── memu.py
│   │   ├── ldplayer.py
│   │   └── bluestacks.py
│   ├── vision/             # thị giác máy tính
│   │   ├── capture.py      # screenshot + ScreenshotArray
│   │   ├── ocr.py          # EasyOCR lazy reader
│   │   ├── templates.py    # template matching
│   │   ├── read_text/      # đọc tài nguyên (gold/elixir/dark)
│   │   └── redline/        # redline detection
│   │       ├── detector.py       # YOLO-seg + OpenCV fallback
│   │       ├── geometry.py       # chia 4 cạnh, offset
│   │       ├── yolo.py           # RedlineSegmenter
│   │       └── dataset_capture.py
│   ├── game/               # logic trò chơi
│   │   ├── battle/         # helpers, target, home base
│   │   ├── village/        # home routine, collectors, zoom
│   │   ├── clan/           # capital, games, requests
│   │   ├── training/       # quick_train, smart_train, OCR
│   │   └── account/        # boot recovery, ready villages
│   ├── attack/             # pipeline tấn công
│   │   ├── api.py          # điểm vào run_attack / init_device
│   │   ├── cycle.py        # một chu kỳ attack
│   │   ├── device.py       # tap / chọn quân
│   │   ├── dropper.py      # thả quân
│   │   ├── planner.py      # lập kế hoạch thả
│   │   └── army.py         # chuẩn bị quân
│   └── gui/
│       ├── app.py          # QApplication + MainWindow
│       ├── tabs/           # army_recipe, debug, stats, village_wizard
│       └── services/       # wizard_bridge, qt_thread
├── tools/                  # script hỗ trợ (dataset, OCR probe, icon)
├── datasets/redline/       # dataset YOLO (images/labels/runs)
├── models/                 # redline_seg.pt / .onnx
├── Templates/              # template ảnh runtime
├── profiles/               # cấu hình làng
├── walls/                  # ảnh wall
├── docs/                   # tài liệu
└── legacy/mybot/           # DLL MyBot cũ (chỉ tham khảo, không dùng runtime)
```

## 2. Quy tắc import

- Mọi import nội bộ dùng `COCbot.*`.
- Không import `core`, `routines`, `utils`, `attacks`, `functions` (đã xoá).
- Không thêm `COCbot/` vào `sys.path` — sẽ shadow stdlib `platform`.
  Chỉ thêm `SRC_DIR` để `import COCbot` hoạt động.
- Module nào cần state dùng `from COCbot.app import state`.
- Shim cũ `import main` được thay bằng `from COCbot.app import state as main`.

## 3. Luồng chạy

```text
run.py
  └─ COCbot.gui.app.main_gui()
       └─ MainWindow -> start_worker
            └─ COCbot.app.bootstrap.run_cycle()
                 ├─ setup_emulator()
                 ├─ boot_recovery()
                 ├─ home routine / collectors / training
                 ├─ search next / extract_resources()
                 │    └─ auto-capture scout frames (good + skipped)
                 └─ attack: COCbot.attack.api.run_attack()
                      └─ cycle.run_attack()
                           ├─ capture screenshot
                           ├─ redline: YOLO-seg -> OpenCV fallback
                           ├─ auto-capture attack frames (tuỳ chọn)
                           ├─ planner -> dropper
```

## 4. Redline

- `vision/redline/detector.py`:
  - Có `redline_model` và file tồn tại → YOLO-seg `base_area`.
  - Không có / lỗi → OpenCV fallback.
  - Trả `(edges, source)` qua `get_redline_edges_ex()`.
- `attack/cycle.py` tự lưu ảnh vào dataset khi bật `auto_capture_dataset`.
- `MyBot.run.dll` / `getRedArea` **không** dùng trong runtime (license check có thể kill emulator).

### Công cụ YOLO

```text
tools/setup_redline_yolo.py    # kiểm tra ultralytics/model/dataset + tải base model
tools/split_redline_dataset.py # chia train/val, sinh redline.local.yaml
tools/compress_dataset.py      # nén ảnh dataset sang JPEG/WebP
tools/train_redline_yolo.py    # train (mặc định yolov8n-seg.pt) + export ONNX
tools/eval_redline_yolo.py     # IoU, drop safety, coverage, latency
```

- `models/yolov8n-seg.pt`: base model (COCO), dùng để fine-tune.
- `models/redline_seg.pt`: model đã train, runtime ưu tiên file này.
- `datasets/redline/redline.local.yaml`: tự sinh với `path` tuyệt đối.
- `ultralytics` nằm trong `requirements.txt`.

## 4.1. An toàn thao tác (tránh mở Shop)

- `app/coords.py` khai báo `SHOP_BUTTON_BOX = (760, 315, 858, 420)`.
- `platform/tap_guard.py` chặn mọi tap rơi vào vùng Shop ở các luồng home/train/request/collector.
- `game/village/ui_state.py` (`close_open_panels`) tự đóng Shop/Army/Settings nếu một panel đang mở,
  trước mỗi chu kỳ và ngay sau khi khởi động game.
- `search_next()` không còn tap cứng `(782, 597)`; nó tìm `next_button.png` trong
  `NEXT_BTN_REGION` rồi tap đúng tâm. Không thấy nút thì bỏ qua thay vì tap bừa.
- `BOOT_DISMISS_TAP` dùng phím BACK + vùng trời an toàn, không còn tap vào nút Clan chat.

## 4.2. Check quân (Army tab)

- Checkbox **Check quân** trong tab Army, mặc định **không tích**.
- Không tích: bỏ qua `smart_train`/`quick_train`, đi thẳng tìm trận đủ điều kiện tài nguyên rồi đánh.
- Có tích: chạy kiểm tra/train quân như cũ.
- Giá trị lưu trong `settings.json` (`"check_troops": false`).

---

## 4.3. OCR tài nguyên

- Engine chính: **PaddleOCR PP-OCRv6** (`COCbot/vision/read_text/numbers.py`).
- Fallback: Tesseract với white-mask (nếu PaddleOCR lỗi/không có).
- ROI đã sửa trong `app/coords.py`: `HR_GOLD_REGION`, `HR_ELIXIR_REGION`, `HR_DE_REGION`.
- Chi tiết benchmark + cách kiểm tra: `docs/OCR.md`.

---

## 4.4. GUI theme & layout

- `COCbot/gui/theme.py`: palette sáng theo Figma — nền `#F2F5F3`, title bar
  `#142C2B`, card `#FFFFFF`, primary `#13775F`, viền `#DCE5E1`.
- Cửa sổ 480×670, frameless title bar kéo được, nút minimize / maximize / close.
- 6 tab: **Log**, **Village** (General + Accounts), **Attack plan**,
  **Bot settings** (Clan Games / Clan Capital / Debug), **Statistics**, **About**.
- Log tab: Bot log (filter INFO/SUCCESS/WARNING/ERROR, Export) + Attack log
  (TIME/MODE/GOLD/ELIXIR/DARK/TROPHIES/BONUS) + Start/Pause/Stop/Search mode.
- `Templates/coc_icon.ico` / `coc_icon.png`: icon cửa sổ.
- `Templates/ui_check.png` / `ui_radio.png`: checkbox/radio asset.
- Không còn thương hiệu "Simplicity" trong GUI.

---

## 4.5. Chuyển account

- **Supercell ID** (mặc định, không cần root): dùng `switch_to_village(slot)`
  trong `game/account/ready_villages.py`.
- **Shared_prefs** (dùng adbd root sẵn có): `game/account/shared_prefs.py`, lưu folder như MyBot.
- Cấu hình: `game/account/switch_config.py` → `profiles/switch_accounts.json`.
- GUI: tab **Accounts** (Pull/Push/Switch, account rows, switch log).
- Auto-switch: theo **số trận riêng từng account** và/hoặc **thời gian** (mỗi X phút), cho cả 2 mode.
- **Đầy 3 kho** (gold/elixir/DE): template matching trong `game/village/storage_full.py`; nếu không còn account khác thì treo online và kiểm tra lại sau X phút.
- Đây là cơ chế chuyển account duy nhất; không còn Multi-Village/multi-account riêng.
- Chi tiết: `docs/ACCOUNT-SWITCH.md`.

---

## 5. Trạng thái & sự kiện

`COCbot.app.state` giữ:

```python
host, emulator_key, ld_index, ld_name
stop_event, pause_event
_saved_wall_offset, wall_save
```

`bootstrap.py` đồng bộ các biến module-level với `state` để code cũ đọc/ghi vẫn đúng.

## 6. Chạy & kiểm tra

```powershell
.venv\Scripts\python.exe run.py
.venv\Scripts\python.exe -m compileall -q COCbot tools
```

Smoke test import:

```powershell
.venv\Scripts\python.exe -c "import COCbot.app.bootstrap, COCbot.gui.app, COCbot.attack.cycle"
```

## 7. Ghi chú refactor

- Bản backup trước refactor: `_backup_refactor_20261109_133911/` (có thể xoá khi ổn định).
- Các file rác runtime (`screen.png`, `battle.png`, `*.html`, ...) đã chuyển vào `artifacts/`.
- `settings.json` và dataset lớn nằm trong `.gitignore`.
