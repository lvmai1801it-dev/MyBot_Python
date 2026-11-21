# KIẾN TRÚC DỰ ÁN (MyBot-like layout)

Tài liệu này mô tả cấu trúc sau refactor. Mục tiêu: tách lớp rõ ràng, import một chiều,
dễ test từng phần, giữ nguyên hành vi bot.

## 1. Cây thư mục

> Cập nhật sau purge MVVM (2026-11-21). `python run.py` là entry point duy
> nhất; toàn bộ shell MVVM nằm trong `_archive_old_code/mvvm_purge_20261121/`.

```text
src/
├── run.py                     # entry point GUI (duy nhất)
├── settings.json              # cấu hình runtime (gitignored)
├── COCbot/
│   ├── app/                   # lõi runtime legacy
│   │   ├── bootstrap.py       # bot_loop + one_cycle
│   │   ├── upgrade_hook.py    # auto-upgrade mỗi cycle (cài từ GUI on_start)
│   │   ├── config.py, coords.py, paths.py, state.py
│   │   ├── army_presets.py, troop_registry.py, stats.py
│   │   └── controls.py, updater.py, version.py
│   ├── attack/                # pipeline tấn công (đường thật)
│   │   ├── cycle.py           # run_attack: ONNX redline + sanitize
│   │   │                      # + verify-redrop + final sweep
│   │   ├── planner.py         # chọn 1/2/3/4 hướng + offset
│   │   ├── dropper.py         # thả quân/hero/CC/spell (opt-in)
│   │   ├── device.py           # tap qua adb input (u2 chỉ là fallback)
│   │   ├── army.py            # quét thanh quân (prepare_attack)
│   │   └── api.py              # re-export công khai
│   ├── emulator/              # MEmu / LDPlayer / BlueStacks (legacy)
│   ├── game/
│   │   ├── account/           # boot recovery, shared_prefs, switch config
│   │   ├── battle/            # home detect, scout, battle helpers, loot OCR
│   │   ├── clan/              # capital, games, request troops
│   │   ├── training/          # quick/smart train, validators, OCR
│   │   └── village/            # main village, collectors, walls, zoom, UI state
│   ├── gui/                   # MainWindow + tabs + theme + Qt thread
│   ├── platform/              # adb_utils, tap_guard, unicode (adb.exe tại
│   │                          # COCbot/adb/)
│   ├── vision/                # capture, OCR số, templates
│   │   └── redline/
│   │       ├── detector.py    # ưu tiên: deploy_zone.onnx -> YOLO -> OpenCV
│   │       ├── deploy_zone.py # SDK ONNX: mask 3 lớp + sanitize theo mask
│   │       └── geometry.py, yolo.py, dataset_capture.py
│   ├── core/                  # thư viện cho features/village (pure, no Qt)
│   │   ├── adb/               # AdbClient + TapGuard
│   │   ├── vision/            # ScreenCapture, NumberOcr, TemplateMatcher
│   │   ├── config/            # schema settings.json, paths, coordinates
│   │   ├── ports.py           # 5 protocol đang dùng (Adb/Capture/Ocr/Clock/Logger)
│   │   └── clock.py, errors.py
│   ├── models/                # dataclass pure: Detection, Frame, geometry,
│   │                          # resources, enums
│   └── features/village/      # auto-upgrade (giữ lại sau purge)
│       ├── upgrades.py        # HeroDefenseUpgrader + wall qua Build panel
│       ├── runner.py          # UpgradeRunner theo số builder free
│       ├── planner.py, targets.py
│       └── resources.py       # ResourceReader (GLM-OCR + Tesseract)
├── tools/                     # dataset/YOLO, crop, probe tap, test side
│                              # modes, audit structure, smoke GUI
├── models/                    # deploy_zone.onnx (gitignored)
├── datasets/redline/          # ảnh + label (gitignored)
├── Templates/, profiles/, walls/, docs/
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

- `vision/redline/detector.py` — `get_redline_edges_ex()` trả `(edges, source)`
  với 3 tầng ưu tiên:
  1. `models/deploy_zone.onnx` (mặc định, `deploy_zone_model` trong
     `settings.json`): U-Net 3 lớp của `deploy_zone_sdk` — mask `no_deploy`
     (IoU ~0.99) → polygon → resample 35px → 4 cạnh. Đây là nguồn chính.
  2. `models/redline_seg.pt` (`redline_model`): YOLO-seg `base_area` nếu
     đã train.
  3. OpenCV fallback (hình thoi ước lượng) — luôn có sẵn.
- Sau khi planner offset cạnh ra ngoài, `attack/cycle.py` gọi
  `deploy_zone.sanitize_plan_edges()`: điểm rơi vào red-zone / UI / ngoài
  map sẽ được **nudge ra ngoài** hoặc **loại bỏ** theo mask ONNX — không tap
  điểm nào model chấm là không thả được.
- `attack/cycle.py` tự lưu ảnh vào dataset khi bật `auto_capture_dataset`.
- Không dùng DLL ngoài; toàn bộ redline chạy Python/OpenCV/ONNX/YOLO.
- Smoke chạy thật trên 12 ảnh scout: `tools/smoke_deploy_zone.py`
  (ONNX thắng 12/12, mọi điểm thả đều deployable, ~1.6–3.2s/frame CPU).

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
- 6 tab: **Log**, **Village** (General + Upgrade + Accounts), **Attack plan**,
  **Bot settings** (Clan Games / Clan Capital / Debug), **Statistics**, **About**.
- **Village → Upgrade** có 6 tab con: **Wall upgrade**, **Hero upgrade**,
  **Defense**, **Army**, **Resource**, **Other**. Hiện chỉ Wall upgrade có logic
  tự động; các tab còn lại lưu cấu hình cho các phiên bản sau (có ghi chú rõ
  trong UI).
- Log tab: Bot log (filter INFO/SUCCESS/WARNING/ERROR, Export) + Attack log
  (TIME/MODE/GOLD/ELIXIR/DARK/TROPHIES/BONUS) + Start/Pause/Stop/Search mode.
- `Templates/coc_icon.ico` / `coc_icon.png`: icon cửa sổ.
- `Templates/ui_check.png` / `ui_radio.png`: checkbox/radio asset.
- Không còn thương hiệu "Simplicity" trong GUI.

---

## 4.4b. Kiểm tra làng chính khi vào game

- `game/village/main_village.py` → `prepare_main_village()`:
  1. Quét toàn màn hình tìm `Templates/btn_close.png`; nếu thấy thì tap để
     đóng popup/overlay và lặp lại đến khi không còn.
  2. Chỉ sau đó mới xác nhận Home Village: có UI Shop/Build **và** đọc được
     thanh Dark Elixir. Builder Base không có thanh DE nên bị loại.
  3. `multi_zoom_out()` để nhìn toàn làng.
  4. `get_home_resources()` đọc Gold / Elixir / DE, lưu vào
     `COCbot.app.state.current_resources`.
- `emulator/memu.py` (`ensure_memu`) tự mở MEmu nếu chưa chạy; nếu đang chạy
  thì đưa về màn hình chính của emulator trước khi `setup_emulator()` mở game.
- `bootstrap.bot_loop()` gọi bước này ngay khi vào game; nếu không xác nhận
  được làng chính thì dừng bot để tránh thao tác sai.

---

## 4.5. Chuyển account

- Chỉ dùng **Shared_prefs** (adbd root sẵn có): `game/account/shared_prefs.py`,
  lưu folder như MyBot. Không còn Supercell ID.
- Cấu hình: `game/account/switch_config.py` → `profiles/switch_accounts.json`.
- GUI: tab **Accounts** (Pull/Push/Switch, account rows, trạng thái thao tác).
- Khi mới Start: dùng account đang mở sẵn, **không tự chuyển**; bộ đếm trận và
  mốc thời gian được reset cho phiên mới.
- Auto-switch chỉ khi thỏa điều kiện: **số trận riêng từng account**, **thời
  gian (mỗi X phút)**, hoặc **đầy 3 kho** (gold/elixir/DE).
- Đầy kho: `game/village/storage_full.py`; nếu không còn account khác thì treo
  online và kiểm tra lại sau X phút.
- Đây là cơ chế chuyển account duy nhất; không còn Multi-Village/multi-account.
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
