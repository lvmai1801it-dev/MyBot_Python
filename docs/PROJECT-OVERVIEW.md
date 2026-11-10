# TỔNG QUAN DỰ ÁN — MyBot PHMOD v15.9 (Python)

> Tài liệu này tóm tắt kiến trúc, số lượng hàm, ý nghĩa các hàm chính và luồng
> hoạt động thực tế của bot. Cập nhật theo code hiện tại (commit `6749288` +
> các thay đổi UI/entry-check sau đó).

---

## 1. Giới thiệu

MyBot PHMOD v15.9 là bot tự động Clash of Clans chạy qua ADB, giao diện PyQt5
480×670. Bot điều khiển emulator (MEmu / LDPlayer / BlueStacks), đọc màn hình
bằng OpenCV + OCR, thả quân theo redline, huấn luyện quân, xin quân, làm Clan
Games / Clan Capital và chuyển account bằng shared_prefs.

Điểm vào:

```text
run.py
└── COCbot/gui/app.py :: main_gui()
    └── MainWindow()
        └── on_start()
            └── COCbot/app/bootstrap.py :: bot_loop()   (worker thread)
                └── one_cycle()  (lặp đến khi Stop)
```

---

## 2. Số liệu tổng quan

### 2.1. Đếm bằng AST (không tính hàm lồng trong hàm)

| Package | Files | Hàm top-level | Method | Dòng |
|---|---:|---:|---:|---:|
| `COCbot/app` | 12 | 41 | 2 | 1.527 |
| `COCbot/attack` | 7 | 24 | 0 | 1.036 |
| `COCbot/emulator` | 5 | 72 | 0 | 2.056 |
| `COCbot/game` | 28 | 104 | 31 | 4.720 |
| `COCbot/gui` | 9 | 6 | 114 | 4.137 |
| `COCbot/platform` | 6 | 8 | 0 | 226 |
| `COCbot/vision` | 14 | 43 | 13 | 1.327 |
| **Tổng COCbot** | **82** | **298** | **160** | **15.033** |
| `tools/` | 11 | 57 | 44 | 2.124 |
| **Tổng toàn dự án** | **93** | **355** | **204** | **17.157** |

- **COCbot: 458 hàm/method** (298 hàm top-level + 160 method).
- **Toàn dự án: 559 hàm/method** (355 + 204).
- Có **20 class** trong COCbot (chưa kể class trong `tools/`).
- Con số AST **không tính các hàm lồng bên trong hàm** (ví dụ helper trong
  `__init__` của GUI), nên thực tế nhiều hơn.

### 2.2. Đếm bằng GitNexus graph

| Loại node | Số lượng |
|---|---:|
| Function | 390 |
| Method | 204 |
| Tổng callable | 594 |
| File / Node / Edge | 111 / 1.503 / 3.551 |
| Communities / Processes | 68 / 127 |

GitNexus đếm cả hàm lồng và method của class; vì vậy 594 > 458 của AST.

---

## 3. Cấu trúc thư mục

```text
src/
├── run.py                     # entry point GUI
├── settings.json              # cấu hình runtime (gitignored)
├── COCbot/
│   ├── app/                   # lõi: bootstrap, config, state, coords, stats
│   ├── attack/                # capture -> redline -> plan -> drop
│   ├── emulator/              # MEmu / LDPlayer / BlueStacks
│   ├── game/
│   │   ├── account/           # boot recovery, shared_prefs, switch config
│   │   ├── battle/            # home detect, scout, battle helpers, target OCR
│   │   ├── clan/              # capital, games, request troops
│   │   ├── training/          # quick/smart train, validators, OCR
│   │   └── village/           # main village, collectors, walls, zoom, UI state
│   ├── gui/                   # MainWindow, tabs, theme, Qt thread
│   ├── platform/              # ADB, tap guard, unicode, AHK
│   └── vision/                # capture, OCR, redline (OpenCV + YOLO), dataset
├── tools/                     # dataset/YOLO tooling, crop/OCR probe
├── datasets/redline/          # images/raw + labels (gitignored)
├── Templates/                 # template ảnh cho bot + upgrade icons + hero
├── profiles/                  # shared_prefs profiles, switch_accounts.json
├── walls/                     # template tường theo level
└── docs/                      # tài liệu dự án
```

---

## 4. Luồng khởi động (startup)

1. `MainWindow.on_start()`:
   - kiểm tra emulator đã chọn, tạo `QtThreadCompat(target=bot_loop)`.
   - gọi `_collect_cfg()` và lưu `settings.json`.
2. `bot_loop(cfg)`:
   - `sync_state()` — đồng bộ `host`, `emulator_key`, `ld_index` giữa module
     `bootstrap` và `COCbot.app.state`.
   - `setup_emulator()`:
     - `ensure_memu()` / `ensure_ldplayer()` / `ensure_bluestacks()`.
     - MEmu chưa chạy → tự mở; đang chạy → đưa về màn hình chính emulator.
     - kiểm tra package `com.supercell.clashofclans`, force-stop rồi launch lại.
   - `init_device()` — khởi tạo uiautomator2 (fallback ADB tap).
   - `prepare_main_village()`:
     1. Quét toàn màn hình tìm `Templates/btn_close.png`; tap để đóng popup,
        lặp đến khi không còn.
     2. `is_main_village()` — có UI Shop/Build **và** đọc được thanh Dark
        Elixir. Builder Base không có thanh DE nên bị loại.
     3. `multi_zoom_out()` — zoom toàn làng.
     4. `read_current_resources()` — đọc Gold / Elixir / DE, lưu
        `state.current_resources`.
     5. Nếu không xác nhận được làng chính sau 90 giây → dừng bot.
   - Reset phiên switch: `state._switch_attack_counts = {}`,
     `last_switch_ts = now` (nếu bật hẹn giờ). **Không tự chuyển account khi
     mới start.**
   - Vào vòng `while not stop_event: one_cycle(cfg)`.

---

## 5. Luồng một chu kỳ — `one_cycle()`

Thứ tự thực tế trong `COCbot/app/bootstrap.py`:

```text
close_open_panels()                 # đóng Shop/Army/Settings/overlay
_check_stop / pause
_maybe_switch_account(attack=False) # chỉ theo thời gian, đã reset khi start
treasure_event()                    # nhận treasure nếu có
ensure_home_base()                  # xác nhận home + chống kẹt
tap(MENU_TAP)                       # tap vùng trống để dismiss
connection_popup_visible()?         # nếu mất kết nối -> boot_recovery
multi_zoom_out()                    # zoom toàn làng
_maybe_switch_full_storages()       # đầy 3 kho -> chuyển account
Clan Capital loop (nếu bật)         # clan_capital() + reboot giữa các pass
kiểm tra quân:
  - check_troops=False  -> bỏ qua
  - quick_train         -> mỗi 5 cycle
  - smart_train         -> mỗi 3 cycle
handle_home_resources()             # nâng tường nếu bật
run_events_open()                   # Clan Games nếu bật
auto_request()                      # xin quân qua Clan Chat
find_and_tap_collectors()           # thu hoạch collector
search_attack()                     # mở tìm trận
vòng scout:
  wait_for_scout_screen()
  is_next_button_present() (retry 3)
  extract_resources()               # OCR loot đối thủ
  auto-capture dataset (scout)
  nếu đủ ngưỡng -> run_attack() -> wait_battle_end()
  cập nhật stats (nếu bật)
  _maybe_switch_account(attack=True)  # đủ số trận -> chuyển
  return_home()
```

Ghi chú:
- `MENU_TAP` hiện là tap vùng cỏ trống, chủ yếu để dismiss.
- `find_and_tap_collectors()` dùng template `gold/elixir/DE_collector.png`.
- Nếu loot dưới ngưỡng → `search_next()` chuyển base kế tiếp.

---

## 6. Luồng tấn công — `COCbot/attack/cycle.py`

```text
run_attack(cfg)
├── _capture_attack_image()          # chụp tối đa 5 lần, tránh mây trắng
├── get_redline_edges_ex(img)
│   ├── có models/redline_seg.pt     -> YOLO-seg (mask -> polygon -> 4 edges)
│   └── không có                     -> OpenCV fallback
│       ├── red pixel mask trong ROI làng
│       ├── percentile dx/dy quanh tâm (433,353)
│       ├── 4 đỉnh hình thoi
│       └── offset ra ngoài 40px, chia mỗi cạnh 5 điểm
├── get_capture(cfg).maybe_capture() # lưu dataset nếu bật
├── build_attack_plan(edges, cfg)
│   ├── offset_edges_to_outer(ECD, ratio=0.35)
│   └── chọn active_edges theo attack_sides / target_xy / legacy
├── prepare_attack(img)              # quét thanh quân, nhận troop/hero/CC
├── _sort_troops()                   # tank trước, main attack sau
├── select_drop_troop() + drop_on_active_edges()
├── drop_heroes_v2()
├── drop_cc()
└── drop_spells()
```

Redline OpenCV dùng các hằng trong `app/coords.py` và `vision/redline/geometry.py`
(`ECD`, `offset_edge_to_outer`, `side_for_point`, `choose_edges`).

---

## 7. Luồng chuyển account (shared_prefs only)

- Không còn Supercell ID; module `ready_villages.py` đã xoá.
- `SharedPrefsManager` (`game/account/shared_prefs.py`):
  - `root_mode()` — kiểm tra adbd root (`adb shell id`).
  - `list_profiles()` / `profile_names()` — đọc `profiles/accounts/*/meta.json`.
  - `pull_profile(name)` — lưu shared_prefs hiện tại thành profile.
  - `push_profile(name, current_profile)` — pull account hiện tại trước, rồi
    push profile đích; game restart.
  - `switch_profile(current, target)` — pull + push.
  - `_update_storage_new()` — sửa language/zoom/rated như MyBot.
- Khi start: dùng account đang mở, **không chuyển**; reset bộ đếm trận và
  `last_switch_ts`.
- Auto switch khi:
  - đủ **số trận** của account hiện tại (`attacks` riêng hoặc fallback
    `consecutive_attacks`),
  - hoặc đủ **X phút**,
  - hoặc **đầy 3 kho** (template `*_collector_full.png`, threshold 0.85).
- Nếu đầy kho mà chỉ còn 1 account: treo online, kiểm tra lại sau
  `storage_full_wait_minutes`.

---

## 8. Luồng dataset & YOLO

- `DatasetCapture` (`vision/redline/dataset_capture.py`):
  - singleton cấu hình từ `settings.json` (`auto_capture_*`).
  - ảnh scout/attack **dùng lại screenshot đã chụp**, không chụp thêm.
  - ghi JPEG/WebP + JSON metadata trên thread riêng.
  - MD5 dedup, rate-limit, max files.
- Dataset hiện tại: `datasets/redline/images/raw/*.jpg` + `.json`.
- Label polygon `base_area` cần đưa vào `datasets/redline/labels/raw/*.txt`.
- Quy trình:
  ```text
  label -> split_redline_dataset.py -> train_redline_yolo.py
        -> eval_redline_yolo.py -> models/redline_seg.pt
  ```
- Khi có model, `get_redline_edges_ex()` tự dùng YOLO; không có thì fallback
  OpenCV.

---

## 9. Ý nghĩa các hàm theo package

### 9.1. `COCbot/app`

| Hàm | Ý nghĩa |
|---|---|
| `sync_state` | Đồng bộ host/emulator/ld_index giữa bootstrap và state. |
| `_account_key_and_quota` | Trả key + quota trận của profile shared_prefs hiện tại. |
| `_reset_attack_count` | Reset bộ đếm trận của 1 account sau khi chuyển. |
| `_switch_to_next_account` | Pull account hiện tại + push profile kế tiếp. |
| `_maybe_switch_account` | Kiểm tra điều kiện trận/thời gian để chuyển. |
| `_wait_with_stop` | Sleep nhưng phản hồi Stop/Pause. |
| `_maybe_switch_full_storages` | Đầy 3 kho → chuyển; không còn acc → chờ X phút. |
| `one_cycle` | Một chu kỳ bot hoàn chỉnh. |
| `bot_loop` | Khởi động emulator/game, entry check, vòng lặp chính. |
| `pause_bot` / `resume_bot` / `_check_stop` | Điều khiển pause/resume/stop. |
| `attack_sides_for_label` | Map hướng thả trong GUI sang code planner. |
| `normalize_recipe` / `load_presets` / `save_presets` / `get_active_preset` | Quản lý preset quân. |
| `_stats_file_path` / `_load_stats_from_disk` / `zero_all_stats_files` | Đọc/ghi/xoá stats. |
| `canonical_troop` / `canonical_spell` / `canonical_siege` | Chuẩn hoá tên quân/phép. |
| `troop_icon_file` / `spell_icon_file` / `siege_icon_file` | Tên file icon tương ứng. |
| `get_troop_space` / `get_spell_space` / `get_siege_space` | Housing space. |
| `Updater.check_for_update` | Kiểm tra bản cập nhật. |

### 9.2. `COCbot/attack`

| Hàm | Ý nghĩa |
|---|---|
| `run_attack` | Pipeline tấn công hoàn chỉnh. |
| `_capture_attack_image` | Chụp frame không mây trắng. |
| `_sort_troops` | Ưu tiên tank trước, main attack sau. |
| `prepare_attack` | Quét thanh quân, nhận troop/hero/CC. |
| `_read_quantity` | OCR số lượng quân trên badge. |
| `_get_templates` / `_norm_template` | Nạp/chuẩn hoá template quân. |
| `init_device` / `get_device` / `reset_device` | Quản lý uiautomator2. |
| `tap` / `set_sleep` / `select_drop_troop` / `check_slot_has_troops` | Thao tác thanh quân. |
| `get_spread_points_along_edge` | Rải điểm thả dọc cạnh. |
| `drop_multipoint_concurrent` | Thả nhiều điểm song song. |
| `drop_on_edge` / `drop_on_active_edges` / `drop_on_edges` | Thả quân theo cạnh. |
| `drop_heroes_v2` / `drop_cc` / `drop_spells` | Thả hero / CC / phép. |
| `build_attack_plan` | Chọn cạnh, offset, target-aware. |
| `legacy_edge_selection` | Quy tắc chọn cạnh cũ. |

### 9.3. `COCbot/emulator`

| Hàm | Ý nghĩa |
|---|---|
| `setup_emulator` | Chọn emulator, kiểm tra/khởi động CoC. |
| `ensure_memu` | Cấu hình, mở MEmu, ADB, màn hình chính. |
| `find_memu_tools` / `get_instance_index` / `apply_resolution` | Tìm MEmu, VM, đặt resolution. |
| `start_and_connect` / `stop_memu` / `is_memu_running` | Bật/tắt/kết nối MEmu. |
| `wait_for_settings_icon` | Chờ màn hình chính emulator. |
| `ensure_ldplayer` / `list_ld_instances` / `find_ldplayer_tools` | Quản lý LDPlayer. |
| `_adb_connect_spin` / `_enable_root` / `_ensure_adb_tcp` | ADB/root/port cho LDPlayer. |
| `ensure_bluestacks` / `find_bluestacks_tools` / `start_and_connect` | Quản lý BlueStacks. |

### 9.4. `COCbot/game/account`

| Hàm / method | Ý nghĩa |
|---|---|
| `boot_recovery` | Restart game/emulator khi kẹt hoặc mất kết nối. |
| `SharedPrefsManager.root_mode` / `root_label` | Kiểm tra quyền adbd root. |
| `list_profiles` / `has_profile` / `delete_profile` | Quản lý profile. |
| `pull_profile` | Lưu shared_prefs hiện tại. |
| `push_profile` | Đưa profile vào game. |
| `switch_profile` | Pull hiện tại + push đích. |
| `_update_storage_new` | Sửa language/zoom/rated. |
| `load_switch_config` / `save_switch_config` / `default_config` | Cấu hình auto switch. |
| `enabled_profiles` | Danh sách profile đang bật. |

### 9.5. `COCbot/game/battle`

| Hàm | Ý nghĩa |
|---|---|
| `detect_home_base` | 3 check: Shop/Build, Settings icon, OCR Shop/Build. |
| `ensure_home_base` | Đóng panel, retry, reboot nếu không thấy home. |
| `search_attack` / `search_next` / `find_next_button` | Tìm trận / base kế. |
| `wait_for_scout_screen` | Chờ màn hình scout. |
| `is_next_button_present` | Kiểm tra nút Next. |
| `connection_popup_visible` | Phát hiện mất kết nối. |
| `battle_ended` / `wait_battle_end` | Chờ kết thúc trận. |
| `treasure_event` | Nhận treasure nếu có. |
| `get_stars_from_screen` / `gain_resources` | Đọc sao và loot nhận được. |
| `extract_resources` / `extract_loot_number` | OCR loot đối thủ. |

### 9.6. `COCbot/game/training`

| Hàm | Ý nghĩa |
|---|---|
| `quick_train` | Train nhanh theo slot. |
| `smart_train` | Train thông minh theo recipe/preset. |
| `_validate_army_window` | Kiểm tra bảng Army đang mở. |
| `validate_troops` / `validate_spells` / `validate_siege` | So khớp quân/phép/siege. |
| `train_troops` / `train_spells` / `train_siege` | Bấm train từng tab. |
| `tap_icon_in_tab` | Tap icon quân trong tab. |
| `find_template_path` / `match` / `match_multiscale` / `roi` | Helper template. |
| `read_number_ocr` / `read_troop_count` | OCR số lượng. |

### 9.7. `COCbot/game/clan`

| Hàm | Ý nghĩa |
|---|---|
| `clan_capital` + `phase2/3/4` | Các bước đánh Clan Capital. |
| `get_glow_drop_points` / `get_glow_drop_points_poly` | Điểm thả theo glow. |
| `popup_warning` | Đóng popup cảnh báo CC. |
| `run_events_open` | Mở Events / Clan Games. |
| `choose_game` | Chọn game trong Events. |
| `auto_request` | Xin quân qua Clan Chat. |
| `_chat_open` / `_close_chat` / `_ocr_text` / `_has_text` | Helper chat + OCR. |

### 9.8. `COCbot/game/village`

| Hàm | Ý nghĩa |
|---|---|
| `is_main_village` | Xác nhận Home Village (Shop/Build + DE bar). |
| `read_current_resources` | Đọc Gold/Elixir/DE của làng hiện tại. |
| `close_btn_close_popups` | Quét và đóng mọi `btn_close`. |
| `prepare_main_village` | Entry flow: popup → main village → zoom → resources. |
| `find_and_tap_collectors` | Thu hoạch collector. |
| `get_home_resources` | OCR tài nguyên làng. |
| `prepare_wall_search` / `find_all_wall_coords` | Tìm tường để nâng. |
| `validate_wall_tap` / `validate_upgrade_window` | Xác nhận đúng tường/popup. |
| `upgrade_wall` / `handle_home_resources` | Nâng tường theo ngưỡng. |
| `detect_full_storages` | Match 3 icon full kho. |
| `close_open_panels` | Đóng Shop/Army/Settings/overlay. |
| `multi_zoom_out` | Pinch zoom out nhiều lần. |

### 9.9. `COCbot/gui`

| Hàm / method | Ý nghĩa |
|---|---|
| `main_gui` | Tạo QApplication, MainWindow, chạy event loop. |
| `MainWindow.on_start` / `on_end` | Start/Stop worker. |
| `_collect_cfg` | Gom cấu hình từ widget thành dict cho bot. |
| `_append_log` / `_append_log_row` | Nhận stdout, đẩy vào bảng log + badge level. |
| `_add_attack_row` | Parse `[LOOT]` thành dòng Attack log. |
| `_export_log` | Xuất log ra file. |
| `_build_accounts_tab` / `_acc_pull` / `_acc_push` / `_acc_switch` | UI shared_prefs. |
| `_load_switch_ui` / `_save_switch_ui` | Đọc/ghi cấu hình auto switch. |
| `ArmyRecipeTab` | Quản lý preset quân, hướng thả, recipe. |
| `StatsTab` | Hiển thị thống kê tài nguyên/sao. |
| `DebugTab` | Chạy test từng module. |
| `QtThreadCompat` | Cầu QThread ↔ threading. |
| `TitleBar` | Kéo cửa sổ frameless. |
| `TimestampStream` | Redirect stdout/stderr có timestamp. |

### 9.10. `COCbot/platform` & `vision`

| Hàm / class | Ý nghĩa |
|---|---|
| `adb_utils.tap` / `run_adb` / `return_home` | Thao tác ADB. |
| `tap_guard.in_shop_zone` / `blocked` | Chặn tap nhầm nút Shop. |
| `imread_unicode` | Đọc ảnh an toàn Unicode trên Windows. |
| `take_screenshot` | Chụp ADB, trả `ScreenshotArray` (giữ PNG gốc). |
| `get_paddle_engine` / `read_number` / `read_region` | OCR số bằng Paddle/Tesseract. |
| `get_redline_edges_cv` | Redline fallback OpenCV. |
| `get_redline_edges_ex` | Chọn YOLO hay OpenCV. |
| `polygon_to_edges` / `RedlineSegmenter.predict_polygon` | YOLO-seg → polygon/edges. |
| `DatasetCapture.maybe_capture` | Lưu ảnh dataset + metadata. |
| `point_in_poly` / `offset_edge_to_outer` / `choose_edges` | Hình học redline. |

### 9.11. `tools/`

| File | Ý nghĩa |
|---|---|
| `capture_redline_dataset.py` | Chụp ảnh thủ công cho dataset. |
| `setup_redline_yolo.py` | Kiểm tra ultralytics/torch/model/dataset. |
| `split_redline_dataset.py` | Chia train/val từ ảnh + label. |
| `train_redline_yolo.py` | Train YOLO-seg. |
| `eval_redline_yolo.py` | Đánh giá model. |
| `compress_dataset.py` | Nén ảnh dataset sang JPG/WebP. |
| `redline_common.py` | Path/helper dùng chung. |
| `crop_tool.py` | Công cụ cắt template/toạ độ. |
| `ocr_probe.py` | Thử OCR trên ảnh. |

---

## 10. Bảng tra nhanh theo tác vụ

| Muốn làm gì | Xem file / hàm |
|---|---|
| Chạy bot | `run.py` → `gui/app.py:main_gui` |
| Vòng lặp chính | `app/bootstrap.py:bot_loop`, `one_cycle` |
| Kiểm tra làng chính | `game/village/main_village.py:prepare_main_village` |
| Đọc tài nguyên làng | `game/village/home_routine.py:get_home_resources` |
| Đọc loot đối thủ | `game/battle/target.py:extract_resources` |
| Tìm/đánh trận | `game/battle/helpers.py:search_attack`, `attack/cycle.py:run_attack` |
| Redline | `vision/redline/detector.py`, `geometry.py`, `yolo.py` |
| Rải quân | `attack/dropper.py` |
| Train quân | `game/training/quick_train.py`, `smart_train.py` |
| Xin quân | `game/clan/requests.py:auto_request` |
| Nâng tường | `game/village/home_routine.py:handle_home_resources` |
| Chuyển account | `game/account/shared_prefs.py`, `app/bootstrap.py` |
| Cấu hình switch | `game/account/switch_config.py` |
| Thu dataset | `vision/redline/dataset_capture.py` |
| GUI Accounts | `gui/app.py:_build_accounts_tab` |
| Log/Attack log | `gui/app.py:_append_log`, `_add_attack_row` |
| Theme | `gui/theme.py:GLOBAL_QSS` |

---

## 11. Trạng thái & giới hạn hiện tại

- **Wall upgrade**: hoạt động tự động.
- **Hero / Defense / Army / Resource / Other upgrade**: mới là UI + lưu cấu
  hình, chưa có logic tự động nâng.
- **Redline**: ưu tiên YOLO-seg nếu có `models/redline_seg.pt`; chưa có thì
  dùng OpenCV fallback (hình thoi ước lượng).
- **Dataset**: đã tự thu ảnh scout/attack; **chưa có label** nên chưa train
  được YOLO.
- **Account switching**: chỉ shared_prefs; cần adbd root. Khi start không tự
  chuyển account.
- **Entry check**: nếu không xác nhận được Home Village (ví dụ đang ở Builder
  Base), bot dừng để tránh thao tác sai.
- **GitNexus**: repo đã index; FTS/BM25 đang tắt do thiếu DLL runtime, nhưng
  Cypher/context/impact vẫn dùng được.

---

## 12. State & cấu hình

`COCbot.app.state` giữ:

```python
host, emulator_key, ld_index, ld_name
stop_event, pause_event
_cycle_count
_switch_attack_counts   # {profile: số trận đã đánh}
current_resources       # Gold/Elixir/DE đọc gần nhất
_saved_wall_offset, wall_save
```

File cấu hình:

| File | Nội dung |
|---|---|
| `settings.json` | loot threshold, wall, clan games/capital, redline, auto-capture, upgrade config |
| `profiles/switch_accounts.json` | auto switch, profile hiện tại, quota trận |
| `profiles/accounts/<name>/` | shared_prefs + meta.json |
| `army_presets.json` | preset quân |

---

## Phụ lục A — Danh sách đầy đủ hàm/method

> Sinh tự động từ AST. Định dạng: `Tên (dòng)`; method ghi `Class.method`.
> Các hàm không có docstring vẫn được liệt kê để tra cứu nhanh.

### COCbot

**COCbot/app/army_presets.py** — 9 hàm/method

- attack_sides_for_label (37)
- _clean_counts (64)
- normalize_recipe (80)
- _normalize_data (93)
- _ensure_file (105)
- load_presets (111)
- save_presets (121)
- get_preset (132)
- get_active_preset (137)

**COCbot/app/bootstrap.py** — 10 hàm/method

- sync_state (71)
- _account_key_and_quota (94)
- _reset_attack_count (110)
- _switch_to_next_account (116)
- _maybe_switch_account (147)
- _wait_with_stop (185)
- _maybe_switch_full_storages (197)
- one_cycle (237)
- bot_loop (515)
- main (572)

**COCbot/app/controls.py** — 3 hàm/method

- pause_bot (5)
- resume_bot (10)
- _check_stop (15)

**COCbot/app/coords.py** — 1 hàm/method

- R (14)

**COCbot/app/stats.py** — 3 hàm/method

- _stats_file_path (9)
- _load_stats_from_disk (15)
- zero_all_stats_files (41)

**COCbot/app/troop_registry.py** — 15 hàm/method

- _norm (18)
- _pascal (196)
- train_template_file (200)
- canonical_troop (213)
- canonical_spell (218)
- canonical_siege (223)
- troop_icon_file (228)
- spell_icon_file (234)
- siege_icon_file (239)
- get_troop_space (245)
- get_spell_space (249)
- get_siege_space (253)
- get_troop_category (257)
- list_troops (261)
- list_spells (267)

**COCbot/app/updater.py** — 2 hàm/method

- Updater.__init__ (16)
- Updater.check_for_update (19)

**COCbot/attack/army.py** — 4 hàm/method

- _norm_template (27)
- _get_templates (35)
- _read_quantity (103)
- prepare_attack (160)

**COCbot/attack/cycle.py** — 3 hàm/method

- _capture_attack_image (27)
- _sort_troops (43)
- run_attack (81)

**COCbot/attack/device.py** — 7 hàm/method

- init_device (32)
- get_device (56)
- reset_device (63)
- tap (69)
- set_sleep (91)
- select_drop_troop (97)
- check_slot_has_troops (108)

**COCbot/attack/dropper.py** — 8 hàm/method

- get_spread_points_along_edge (14)
- drop_multipoint_concurrent (52)
- drop_on_edge (71)
- drop_on_active_edges (95)
- drop_on_edges (126)
- drop_heroes_v2 (146)
- drop_cc (179)
- drop_spells (192)

**COCbot/attack/planner.py** — 2 hàm/method

- legacy_edge_selection (23)
- build_attack_plan (38)

**COCbot/emulator/bluestacks.py** — 14 hàm/method

- run (31)
- find_bluestacks_tools (54)
- _read_conf (75)
- _write_conf (80)
- _detect_instance_prefix (106)
- _get (113)
- _set (124)
- is_running (130)
- stop_player (143)
- start_and_connect (154)
- _shot (191)
- wait_for_settings_icon (195)
- _first_diff (235)
- ensure_bluestacks (244)

**COCbot/emulator/ldplayer.py** — 44 hàm/method

- _popup_async (39)
- _popup_close (65)
- _from_env_pair (73)
- _from_path (81)
- _from_app_paths (96)
- _from_uninstall (152)
- _find_by_filename_scan (233)
- _load_cache (253)
- _save_cache (261)
- clear_ld_cache (269)
- _drive_order (276)
- _prime_ld_services (285)
- _iter_depth_limited (292)
- _has_console_player (302)
- _find_ldplayer_by_foldername (317)
- _main (358)
- _run (364)
- _has_value (395)
- _adb_start_server (415)
- _adb_connect_spin (427)
- _find_ld_cfg_path (457)
- _patch_ld_cfg_basic_flags (518)
- _patch_ld_cfg_file (562)
- _chosen_ld_name (643)
- _is_root_enabled (652)
- _enable_root_offline (687)
- _force_adb_tcp (699)
- find_ldplayer_tools (726)
- is_running (830)
- stop_player (843)
- _ldconsole (864)
- _enable_root (880)
- _ensure_adb_tcp (893)
- _get_adb_port (942)
- _connect_only (946)
- _adb_wm (972)
- _set_core (985)
- _shot (999)
- wait_for_home_icon (1003)
- _wait_for_boot_adb (1043)
- ensure_ldplayer (1055)
- list_ld_instances (1132)
- is_instance_started (1250)
- _wait_started (1261)

**COCbot/emulator/memu.py** — 13 hàm/method

- run (28)
- find_memu_tools (51)
- get_instance_index (87)
- apply_resolution (99)
- _find_instance_cfg (119)
- _current_render_mode_cfg (132)
- _set_render_mode_cfg (144)
- stop_memu (159)
- is_memu_running (171)
- start_and_connect (184)
- capture_for_matching (230)
- wait_for_settings_icon (234)
- ensure_memu (284)

**COCbot/emulator/setup.py** — 1 hàm/method

- setup_emulator (14)

**COCbot/game/account/boot_recovery.py** — 2 hàm/method

- _get_host (14)
- boot_recovery (34)

**COCbot/game/account/shared_prefs.py** — 32 hàm/method

- _safe_name (52)
- SharedPrefsManager.__init__ (60)
- SharedPrefsManager._get_host (67)
- SharedPrefsManager._adb_connect (101)
- SharedPrefsManager._host_alive (114)
- SharedPrefsManager._detect_host (128)
- SharedPrefsManager._adb (157)
- SharedPrefsManager._shell (167)
- SharedPrefsManager.root_mode (170)
- SharedPrefsManager.root_label (212)
- SharedPrefsManager._root_shell (220)
- SharedPrefsManager._require_ok (230)
- SharedPrefsManager.data_dir (237)
- SharedPrefsManager.prefs_dir (241)
- SharedPrefsManager.android_id (244)
- SharedPrefsManager.profile_dir (248)
- SharedPrefsManager.local_prefs (251)
- SharedPrefsManager.list_profiles (255)
- SharedPrefsManager.profile_names (281)
- SharedPrefsManager.has_profile (284)
- SharedPrefsManager.delete_profile (288)
- SharedPrefsManager._find_profile (293)
- SharedPrefsManager._migrate_archive (307)
- SharedPrefsManager.pull_profile (323)
- SharedPrefsManager.push_profile (377)
- SharedPrefsManager.switch_profile (413)
- SharedPrefsManager._pull_without_launch (420)
- SharedPrefsManager._pull_remote_to_local (449)
- SharedPrefsManager._push_local_to_remote (464)
- SharedPrefsManager._update_storage_new (486)
- SharedPrefsManager._stop (515)
- SharedPrefsManager._launch (518)

**COCbot/game/account/switch_config.py** — 4 hàm/method

- default_config (15)
- load_switch_config (36)
- save_switch_config (56)
- enabled_profiles (62)

**COCbot/game/battle/detect_home_base.py** — 2 hàm/method

- _log (16)
- detect_home_base (38)

**COCbot/game/battle/ensure_home_base.py** — 1 hàm/method

- ensure_home_base (10)

**COCbot/game/battle/helpers.py** — 11 hàm/method

- search_attack (50)
- find_next_button (63)
- search_next (95)
- connection_popup_visible (107)
- wait_for_scout_screen (136)
- battle_ended (190)
- wait_battle_end (203)
- is_next_button_present (224)
- treasure_event (251)
- get_stars_from_screen (278)
- gain_resources (306)

**COCbot/game/battle/target.py** — 3 hàm/method

- _save_debug_image (32)
- extract_loot_number (52)
- extract_resources (117)

**COCbot/game/clan/capital.py** — 17 hàm/method

- _sorted_box (75)
- _points_along (81)
- _abs_poly_from_rel (93)
- get_glow_drop_points_poly (98)
- get_glow_drop_points (137)
- _canon (167)
- popup_warning (183)
- _villages_for_ch_level (193)
- _scan_icons_in_panel (219)
- _load_last_cc_tpl (253)
- _save_last_cc_tpl (267)
- _scan_all_cc_templates (276)
- clan_capital (303)
- clan_capital_phase2 (415)
- clan_capital_phase3 (469)
- clan_capital_phase4 (571)
- _is_capital_peak_fresh (1038)

**COCbot/game/clan/games.py** — 4 hàm/method

- tap (39)
- match_template (47)
- choose_game (69)
- run_events_open (148)

**COCbot/game/clan/requests.py** — 10 hàm/method

- _get_host (34)
- _step_log (41)
- _grab (45)
- _tap (54)
- _key_back (71)
- _ocr_text (84)
- _has_text (103)
- _chat_open (110)
- _close_chat (114)
- auto_request (129)

**COCbot/game/training/quick_train.py** — 1 hàm/method

- quick_train (35)

**COCbot/game/training/smart_train.py** — 2 hàm/method

- smart_train (35)
- _ensure_close_army_window (78)

**COCbot/game/training/smart_train_ocr.py** — 3 hàm/method

- is_paddle_available (14)
- read_number_ocr (18)
- read_troop_count (24)

**COCbot/game/training/smart_train_trainers.py** — 6 hàm/method

- _get_host (25)
- tap (43)
- tap_icon_in_tab (60)
- train_troops (91)
- train_spells (119)
- train_siege (146)

**COCbot/game/training/smart_train_utils.py** — 4 hàm/method

- find_template_path (12)
- match (30)
- match_multiscale (44)
- roi (80)

**COCbot/game/training/smart_train_validators.py** — 4 hàm/method

- _validate_army_window (27)
- validate_troops (95)
- validate_spells (148)
- validate_siege (198)

**COCbot/game/village/collectors.py** — 3 hàm/method

- _get_host (27)
- run_adb (45)
- find_and_tap_collectors (67)

**COCbot/game/village/home_routine.py** — 11 hàm/method

- ocr_number (75)
- get_home_resources (80)
- _get_main (103)
- prepare_wall_search (108)
- _match_coords_single (135)
- _dedupe_coords (162)
- find_all_wall_coords (171)
- validate_wall_tap (223)
- validate_upgrade_window (310)
- upgrade_wall (323)
- handle_home_resources (429)

**COCbot/game/village/main_village.py** — 6 hàm/method

- _match_template (40)
- is_main_village (51)
- read_current_resources (75)
- _find_btn_close (92)
- close_btn_close_popups (108)
- prepare_main_village (140)

**COCbot/game/village/storage_full.py** — 2 hàm/method

- _count_matches (31)
- detect_full_storages (50)

**COCbot/game/village/ui_state.py** — 4 hàm/method

- _host (33)
- _key_back (38)
- _tap (47)
- close_open_panels (56)

**COCbot/game/village/zoom.py** — 3 hàm/method

- _get_host (18)
- _safe_pinch_in (36)
- multi_zoom_out (73)

**COCbot/gui/app.py** — 67 hàm/method

- EmulatorSelectionDialog.__init__ (139)
- EmulatorSelectionDialog._choose (199)
- EmulatorSelectionDialog.getSelection (203)
- handle_exception (207)
- TimestampStream.__init__ (228)
- TimestampStream.write (232)
- TimestampStream.flush (242)
- classify_level (254)
- load_settings (266)
- save_settings (302)
- load_attack_assets (310)
- LDInstancePickerDialog.__init__ (326)
- LDInstancePickerDialog._attach_bounce_icon (363)
- LDInstancePickerDialog._populate_table (392)
- LDInstancePickerDialog._add_row (408)
- LDInstancePickerDialog._adjust_button_icons (444)
- LDInstancePickerDialog._warn_busy (452)
- LDInstancePickerDialog._on_start_clicked (462)
- LDInstancePickerDialog._on_row_double_clicked (474)
- LDInstancePickerDialog._equalize_columns (486)
- LDInstancePickerDialog.resizeEvent (492)
- TitleBar.__init__ (501)
- TitleBar.mousePressEvent (506)
- TitleBar.mouseMoveEvent (513)
- TitleBar.mouseReleaseEvent (518)
- TitleBar.mouseDoubleClickEvent (522)
- MainWindow._on_toggle_pause_play (532)
- MainWindow._stats_file_path (555)
- MainWindow.load_village_stats (560)
- MainWindow._refresh_stats_from_json (582)
- MainWindow.on_update_available (591)
- MainWindow._account_manager (602)
- MainWindow._account_busy (605)
- MainWindow._build_accounts_tab (614)
- MainWindow._account_log (810)
- MainWindow._current_profile_text (815)
- MainWindow._set_current_profile (818)
- MainWindow._refresh_accounts (825)
- MainWindow._load_switch_ui (896)
- MainWindow._save_switch_ui (944)
- MainWindow._update_switch_rows (969)
- MainWindow._switch_page (985)
- MainWindow._selected_profile (991)
- MainWindow._acc_pull (997)
- MainWindow._acc_push (1016)
- MainWindow._acc_switch (1043)
- MainWindow._acc_delete (1077)
- MainWindow._toggle_maximized (1096)
- MainWindow._on_tab_changed (1102)
- MainWindow.choose_emulator (1105)
- MainWindow.__init__ (1160)
- MainWindow._build_about_tab (1971)
- MainWindow._on_army_recipe_changed (2021)
- MainWindow._toggle_wall_inputs (2025)
- MainWindow._append_log_row (2031)
- MainWindow._append_log (2074)
- MainWindow._on_log_filter_changed (2093)
- MainWindow._export_log (2100)
- MainWindow._reset_attack_table (2114)
- MainWindow._add_attack_row (2128)
- MainWindow._fmt_number (2167)
- MainWindow.on_start (2173)
- MainWindow.on_end (2263)
- MainWindow._set_inputs_enabled (2310)
- MainWindow._collect_cfg (2321)
- MainWindow.closeEvent (2408)
- main_gui (2456)

**COCbot/gui/services/qt_thread.py** — 4 hàm/method

- QtThreadCompat.__init__ (13)
- QtThreadCompat.run (20)
- QtThreadCompat.join (27)
- QtThreadCompat.is_alive (31)

**COCbot/gui/tabs/army_recipe.py** — 28 hàm/method

- TroopCell.__init__ (54)
- TroopCell.get_count (121)
- TroopCell.set_count (124)
- TroopCell.clear (129)
- RecipeGrid.__init__ (137)
- RecipeGrid.get_selected (160)
- RecipeGrid.set_selected (163)
- RecipeGrid.total_space (169)
- RecipeGrid.clear (172)
- ArmyRecipeTab.__init__ (181)
- ArmyRecipeTab._build_ui (187)
- ArmyRecipeTab._load_presets_to_combo (319)
- ArmyRecipeTab._on_preset_selected (330)
- ArmyRecipeTab._apply_recipe_to_ui (340)
- ArmyRecipeTab._collect_current (356)
- ArmyRecipeTab._on_save_preset (367)
- ArmyRecipeTab._on_new_preset (379)
- ArmyRecipeTab._on_delete_preset (402)
- ArmyRecipeTab._clear_grids (429)
- ArmyRecipeTab._on_side_changed (437)
- ArmyRecipeTab._on_grid_changed (440)
- ArmyRecipeTab._update_space_label (444)
- ArmyRecipeTab.get_current_recipe (460)
- ArmyRecipeTab.get_active_preset_name (463)
- ArmyRecipeTab.get_active_recipe (466)
- ArmyRecipeTab.get_active_name (469)
- ArmyRecipeTab.get_attack_side (472)
- ArmyRecipeTab.get_check_troops (475)

**COCbot/gui/tabs/debug.py** — 10 hàm/method

- EmittingStream.write (38)
- EmittingStream.flush (41)
- DebugTab.__init__ (45)
- DebugTab._build_ui (58)
- DebugTab.append_log (131)
- DebugTab._ensure_connection (136)
- DebugTab.run_test (169)
- DebugTab._execute_task (180)
- DebugTab.test_full_attack (212)
- DebugTab.__del__ (229)

**COCbot/gui/tabs/stats.py** — 11 hàm/method

- _ResourceRow.__init__ (20)
- _ResourceRow.set_value (39)
- StatsTab.__init__ (46)
- StatsTab.add_loot (311)
- StatsTab._refresh_time (333)
- StatsTab._refresh_overall_time (337)
- StatsTab._refresh_all (341)
- StatsTab.set_stats_dict (359)
- StatsTab._create_village_tab (375)
- StatsTab._refresh_village_tab (424)
- StatsTab._fmt_secs (442)

**COCbot/platform/adb_utils.py** — 4 hàm/method

- _get_target_device (11)
- run_adb (31)
- tap (45)
- return_home (69)

**COCbot/platform/ahk.py** — 1 hàm/method

- run_ahk (13)

**COCbot/platform/tap_guard.py** — 2 hàm/method

- in_shop_zone (17)
- blocked (27)

**COCbot/platform/unicode.py** — 1 hàm/method

- imread_unicode (14)

**COCbot/vision/capture.py** — 7 hàm/method

- ScreenshotArray.__new__ (27)
- ScreenshotArray.__array_finalize__ (33)
- ScreenshotArray.__bool__ (39)
- ScreenshotArray.__str__ (42)
- ScreenshotArray.__fspath__ (45)
- _get_host (50)
- take_screenshot (68)

**COCbot/vision/ocr.py** — 3 hàm/method

- _get_reader (6)
- _LazyReader.__getattr__ (20)
- read_text (27)

**COCbot/vision/read_text/dark_elixir.py** — 1 hàm/method

- get_dark_elixir (9)

**COCbot/vision/read_text/elixir.py** — 1 hàm/method

- get_elixir (9)

**COCbot/vision/read_text/gold.py** — 1 hàm/method

- get_gold_strict (9)

**COCbot/vision/read_text/numbers.py** — 9 hàm/method

- get_paddle_engine (31)
- paddle_available (53)
- _digits (57)
- _read_paddle (62)
- _prep_tesseract (89)
- _read_tesseract (100)
- read_digits (125)
- read_number (136)
- read_region (147)

**COCbot/vision/redline/dataset_capture.py** — 9 hàm/method

- _default_dir (41)
- _resolve_dir (45)
- _normalize_format (53)
- DatasetCapture.__init__ (63)
- DatasetCapture._run (105)
- DatasetCapture._encode (120)
- DatasetCapture._should_capture (139)
- DatasetCapture.maybe_capture (173)
- get_capture (227)

**COCbot/vision/redline/detector.py** — 4 hàm/method

- hex_to_bgr (27)
- get_redline_edges_cv (35)
- get_redline_edges_ex (104)
- get_redline_edges (124)

**COCbot/vision/redline/geometry.py** — 12 hàm/method

- parse_points (62)
- point_in_poly (78)
- clamp_point (95)
- nearest_on_segment (102)
- nearest_on_polygon (115)
- filter_edge (130)
- offset_edge_to_outer (149)
- offset_edges_to_outer (176)
- side_for_point (191)
- choose_edges (213)
- edge_midpoint (233)
- ensure_four_edges (239)

**COCbot/vision/redline/yolo.py** — 6 hàm/method

- _src_dir (29)
- resolve_model_path (36)
- polygon_to_edges (47)
- RedlineSegmenter.__init__ (76)
- RedlineSegmenter.predict_polygon (95)
- get_redline_from_yolo (142)

**COCbot/vision/templates.py** — 3 hàm/method

- _match_gray (8)
- _match_color (33)
- _match_template (66)

### tools

**tools/capture_redline_dataset.py** — 1 hàm/method

- main (27)

**tools/compress_dataset.py** — 4 hàm/method

- _imread (38)
- _encode (49)
- _convert_dir (63)
- main (144)

**tools/crop_tool.py** — 19 hàm/method

- CropTool.__init__ (9)
- CropTool.capture_screen (126)
- CropTool.update_canvas_image (181)
- CropTool.zoom_image (201)
- CropTool.on_mousewheel (206)
- CropTool.pick_color (209)
- CropTool.clear_polygon (234)
- CropTool.draw_polygon (239)
- CropTool.copy_polygon (266)
- CropTool.on_button_press (283)
- CropTool.execute_click_capture (314)
- CropTool.on_move_press (345)
- CropTool.on_button_release (351)
- CropTool.draw_selection_box (369)
- CropTool.update_coords_label (377)
- CropTool.update_preview (384)
- CropTool.copy_xyxy (395)
- CropTool.copy_xywh (404)
- CropTool.save_crop (415)

**tools/eval_redline_yolo.py** — 5 hàm/method

- load_gt_mask (34)
- mask_iou (55)
- sample_polyline (61)
- evaluate (77)
- main (157)

**tools/ocr_probe.py** — 52 hàm/method

- _find_dll_path (50)
- _get_memu_pid (62)
- _init_dll (83)
- _to_bgr (148)
- _create_dib32_from_bgr (169)
- _post_process (205)
- OcrEngine.__init__ (225)
- OcrEngine._ensure_dll (228)
- OcrEngine.available (233)
- OcrEngine.ocr (236)
- OcrEngine.gold_village (272)
- OcrEngine.elixir_village (275)
- OcrEngine.dark_elixir_village (278)
- OcrEngine.trophy_village (281)
- OcrEngine.trophy_main_screen (284)
- OcrEngine.resources_main_screen (295)
- OcrEngine.resources_loot (298)
- OcrEngine.resources_loot_de (301)
- OcrEngine.resources_loot_trophy (304)
- OcrEngine.resources_bonus (307)
- OcrEngine.yellow_level (310)
- OcrEngine.building_name (313)
- OcrEngine.builders (325)
- OcrEngine.overall_damage (331)
- OcrEngine.guard_shield (334)
- OcrEngine.remain_hero (337)
- OcrEngine.upgrade_cost (340)
- OcrEngine.upgrade_cost_red (343)
- OcrEngine.bldg_upgrade_time (346)
- OcrEngine.chat_string (350)
- OcrEngine.language_check (353)
- get_engine (361)
- get_gold_village_search (369)
- get_elixir_village_search (370)
- get_dark_elixir_village_search (371)
- get_trophy_village_search (372)
- get_trophy_main_screen (373)
- get_resources_main_screen (374)
- get_resources_loot (375)
- get_yellow_level (376)
- get_building_name (377)
- get_builders (378)
- get_overall_damage (379)
- get_remain_hero (380)
- get_upgrade_cost (381)
- get_upgrade_cost_red (382)
- get_bldg_upgrade_time (383)
- _parse_opts (389)
- _cli_stdin_batch (401)
- _setup_adb (456)
- _capture_adb (473)
- _cli_test (482)

**tools/png_to_ico.py** — 1 hàm/method

- png_to_ico (11)

**tools/redline_common.py** — 6 hàm/method

- dataset_yaml_path (26)
- ensure_dataset_yaml (31)
- model_candidates (47)
- find_trained_model (55)
- count_files (62)
- dataset_counts (69)

**tools/setup_redline_yolo.py** — 8 hàm/method

- _download_url (59)
- _line (87)
- _check_ultralytics (91)
- _check_torch (101)
- _download_base (112)
- _first_raw_image (150)
- _smoke (160)
- main (190)

**tools/split_redline_dataset.py** — 1 hàm/method

- main (32)

**tools/train_redline_yolo.py** — 4 hàm/method

- _resolve_base_model (51)
- _copy_to_models (61)
- _check_dataset (69)
- main (84)
