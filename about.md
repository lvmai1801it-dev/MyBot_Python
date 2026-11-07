```markdown
# 📘 SIMPLICITY BOT v3.50 — Project Documentation

> Tài liệu mô tả kiến trúc, luồng hoạt động và logic của bot Clash of Clans (Simplicity v3.50.0). Dựa trên toàn bộ bytecode đã decompile.

---

## Mục lục

1. [Tổng quan](#1-tổng-quan)
2. [Cấu trúc file](#2-cấu-trúc-file)
3. [Luồng khởi động](#3-luồng-khởi-động-startup-flow)
4. [Các tab trong GUI](#4-các-tab-trong-gui)
5. [Luồng Start → Stop](#5-luồng-start--stop)
6. [Bot loop — Luồng chính](#6-bot-loop--luồng-chính)
7. [`one_cycle` — Một chu kỳ farm](#7-one_cycle--một-chu-kỳ-farm)
8. [Các module con](#8-các-module-con)
9. [Quản lý emulator](#9-quản-lý-emulator)
10. [Multi-village flow](#10-multi-village-flow)
11. [Threading model](#11-threading-model)
12. [Xử lý lỗi & recovery](#12-xử-lý-lỗi--recovery)
13. [Lưu settings](#13-lưu-settings)
14. [Attack dispatch](#14-attack-dispatch)
15. [Utilities nhanh](#15-utilities-nhanh)
16. [Điểm cần lưu ý khi port](#16-điểm-cần-lưu-ý-khi-port)
17. [Sơ đồ tổng quát](#17-sơ-đồ-tổng-quát)
18. [Changelog / TODO](#18-changelog--todo-suy-luận-từ-code)

---

## 1. TỔNG QUAN

**Simplicity** là bot tự động chơi **Clash of Clans** trên emulator Android (MEmu / BlueStacks / LDPlayer) thông qua ADB. Bot có GUI PyQt5, hỗ trợ nhiều làng (multi-village), nhiều loại lính (Dragon / Electro Dragon), và các tính năng: tự động farm, nâng wall, xin quân, Clan Games, Clan Capital.

### Stack công nghệ

| Thành phần | Công nghệ |
|---|---|
| GUI | PyQt5 |
| Điều khiển emulator | ADB (`adb.exe` bundle) |
| Nhận diện hình ảnh | OpenCV (`cv2`) template matching |
| OCR | EasyOCR (lazy-loaded) |
| Multi-gesture (zoom) | UIAutomator2 |
| Tương tác phụ | AutoHotkey v2 (cho MEmu) |
| Đóng gói | PyInstaller (`sys.frozen`) |

---

## 2. CẤU TRÚC FILE

```
project_pyc/
├── bot_gui.py             ← Entry point (GUI)
├── main.py                ← Bot engine chính (bot_loop, one_cycle)
├── version.py             ← __version__ = "3.50.0"
├── updater.py             ← Auto-update checker
├── qt_thread_compat.py    ← QThread ↔ threading.Thread wrapper
│
├── [EMULATOR MANAGERS]
├── memu_manager.py
├── bluestacks_manager.py
├── ldplayer_manager.py
├── adb_config.py          ← ADB_BIN path
│
├── [CORE GAME LOGIC]
├── ensure_home_base.py    ← Chờ/khôi phục home screen
├── detect_home_base.py    ← Nhận diện home screen
├── boot_recovery.py       ← Restart Clash of Clans
├── home_routine.py        ← Nâng wall tự động
├── request_troops.py      ← Xin quân
├── IsTarget.py            ← Đọc loot địch (OCR)
├── Tap_Collectors.py      ← Tap collectors trên home
├── clan_games.py          ← Chơi Clan Games
├── smart_train.py         ← Train quân thông minh (theo recipe)
├── quick_train.py         ← Quick train slot
│
├── [MULTI-VILLAGE]
├── ready_villages.py      ← Switch, crop, save configs
├── village_wiz.py         ← Wizard cấu hình nhiều làng
├── wizard_bridge.py       ← Signal bridge GUI ↔ worker
│
├── [UTILITIES]
├── screenshot_utils.py    ← ADB screencap
├── ocr_reader.py          ← EasyOCR lazy loader
├── unicode.py             ← imread_unicode (đọc ảnh path Unicode)
├── ahk_utils.py           ← run_ahk (AutoHotkey)
├── zoom_out.py            ← Pinch-out gesture
├── stats_tab.py           ← Tab thống kê
│
├── [DIRECTORIES]
├── Templates/             ← Ảnh template
│   ├── Clan Games/
│   ├── Clan Capital/
│   │   ├── Scenery/       ← Ảnh scenery làng capital
│   │   ├── Spells/
│   │   └── Troops/
│   ├── Smart_Auto_train/
│   │   ├── Army Troops/
│   │   ├── s_troops/
│   │   ├── Spells/
│   │   ├── Siege Machines/
│   │   └── to_train/
│   ├── attacks/           ← Ảnh + mô tả chiến thuật
│   └── *.png              ← Icon, template lẻ
├── adb/adb.exe
├── AutoHotkey/v2/AutoHotkey64.exe
├── profiles/              ← Config từng làng
│   ├── Village_1.json
│   ├── account_1.png
│   ├── Stats_1.json
│   └── accounts.txt
└── settings.json
```

---

## 3. LUỒNG KHỞI ĐỘNG (Startup Flow)

```
[user double-click bot_gui.exe]
        │
        ▼
┌─────────────────────────────────────┐
│ bot_gui.py — module-level init       │
│  • ctypes SetProcessDpiAwareness(1)  │
│  • import certifi → set SSL env     │
│  • QApplication(sys.argv)            │
│  • OS check, warnings.filter         │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│ main_gui()                           │
│  • zero_all_stats_files()            │
│  • app.setWindowIcon()               │
│  • win = MainWindow()                │
│  • win.show()                        │
│  • pyi_splash.close() nếu frozen     │
│  • app.exec_()                       │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│ MainWindow.__init__()                │
│  1. load_settings() → settings dict  │
│  2. load_attack_assets() (ảnh attack)│
│  3. Build 7 tab GUI                  │
│  4. TimestampStream → sys.stdout     │
│  5. Start/Stop buttons               │
│  6. QTimer 5s → refresh stats        │
│  7. Updater → check_for_update()     │
└─────────────────────────────────────┘
```

---

## 4. CÁC TAB TRONG GUI

| Tab | Chức năng | Widget chính |
|---|---|---|
| **General** | Threshold gold/elixir/DE, wall upgrade, request troops | `QLineEdit`, `QCheckBox`, `QSpinBox` |
| **Army** | Chọn attack type, smart/quick train | `QComboBox`, `QRadioButton` |
| **Multi-Village** | Bật multi-làng, chọn số làng, load/save config từng làng | `QCheckBox`, `QSpinBox`, danh sách widget |
| **Clan Games** | Bật/tắt auto Clan Games | `QCheckBox`, ảnh minh hoạ |
| **Clan Capital** | Bật/tắt auto Clan Capital, chọn CH level | `QCheckBox`, `QSpinBox` |
| **Statistics** | Bảng thống kê loot, stars, attacks | `StatsTab` |
| **Logs** | Log realtime từ bot (colored) | `QTextEdit` |

---

## 5. LUỒNG START → STOP

### 5.1 Khi nhấn **START**

```
MainWindow.on_start()
     │
     ├─ Nếu worker đang chạy → return
     │
     ├─ choose_emulator()
     │    └─ Mở EmulatorSelectionDialog
     │         ├─ MEmu    → host=MEMU(127.0.0.1:21503), port=6200
     │         ├─ BlueStacks → host=BLUESTACKS(127.0.0.1:5556), port=6201
     │         ├─ LDPlayer → LDInstancePickerDialog → port=6202+idx
     │         └─ Bind port để chống chạy 2 instance bot
     │
     ├─ cfg = _collect_cfg()   ← đọc toàn bộ UI
     │
     ├─ main.stop_event.clear()
     │
     ├─ worker = QtThreadCompat(target=main.bot_loop, args=(cfg,))
     │
     ├─ worker.start()         ← Qt thread chạy bot_loop
     │
     ├─ Disable toàn bộ input
     └─ start_btn.disable, stop_btn.enable
```

### 5.2 Khi nhấn **STOP**

```
MainWindow.on_end()
     ├─ main.stop_event.set()      ← signal dừng
     ├─ worker.join(0.1)
     ├─ Enable lại input
     ├─ start_btn.enable, stop_btn.disable
     └─ _emu_socket.close()        ← nhả port lock
```

### 5.3 Nút PAUSE / RESUME (side nav)

```
_on_toggle_pause_play()
     ├─ Nếu chưa paused → main.pause_bot()  (pause_event.clear())
     │                    đổi icon thành Play
     └─ Nếu đang paused → main.resume_bot() (pause_event.set())
                          đổi icon thành Stop
```

---

## 6. BOT LOOP — LUỒNG CHÍNH

```
main.bot_loop(cfg)
     │
     ├─ setup_emulator()               # Khởi động emulator + ADB
     │    ├─ emulator_key = 'memu' | 'bluestacks' | 'ldplayer'
     │    ├─ ensure_memu/ensure_bluestacks/ensure_ldplayer()
     │    ├─ Check CoC installed (pm list packages)
     │    ├─ Restart CoC nếu đang chạy (am force-stop + monkey)
     │    └─ Đợi home screen
     │
     ├─ ensure_home_base()
     ├─ tap(140, 606)                  # Tap vào vị trí home an toàn
     │
     ├─ Check multi-village:
     │    ├─ Nếu có làng → prepare_accounts(start=1, count=None)
     │    │              → Save ảnh account_i.png
     │    │              → Boot recovery
     │    │
     │    └─ Nếu không → single mode
     │
     ├─ accounts_count = đọc profiles/accounts.txt
     ├─ Nếu enable_multi_account & accounts_count==1
     │     → force single mode
     │
     ├─ Nếu single mode:
     │    loop:  one_cycle(cfg)   cho đến khi stop_event
     │
     └─ Nếu multi mode:
          for idx in selected_villages:
               ├─ switch_to_village(idx)
               ├─ Load village_cfg từ Village_{idx}.json
               ├─ merge cfg + village_cfg
               └─ while time < interval_secs:
                       one_cycle(merged_cfg)
```

---

## 7. `one_cycle` — MỘT CHU KỲ FARM

Đây là **trái tim** của bot. Mỗi cycle = 1 lần farm + 1 lần nâng wall + xin quân.

```
one_cycle(cfg)
    │
    ├─ pause_event.wait()                # block nếu đang pause
    ├─ if stop_event: abort
    │
    ├─ treasure_event()                  # Check event kho báu (nếu có → tap)
    │
    ├─ ensure_home_base()                # Đảm bảo ở home
    ├─ tap(140, 606)
    │
    ├─ if connection_popup_visible():    # Mất kết nối?
    │      boot_recovery(); return
    │
    ├─ multi_zoom_out(host)              # Zoom out 3 lần (pinch in)
    │
    ├─ [CLAN CAPITAL LOOP]  nếu cfg.enable_clan_capital:
    │    while True:
    │       started = clan_capital(cfg)
    │       if not started: break
    │       boot_recovery()
    │       ensure_home_base()
    │       multi_zoom_out()
    │       if connection lost: break
    │
    ├─ [TRAIN ARMY]
    │    ├─ if train_mode == 'quick':
    │    │     if cycle_count % 5 == 0:
    │    │         quick_train(cfg['quick_slot'])
    │    └─ else:
    │          if cycle_count % 3 == 0:
    │              smart_train(cfg)
    │
    ├─ [UPGRADE WALL] nếu cfg.upgrade_wall:
    │    handle_home_resources(
    │         wall_level, wall_gold_thresh, wall_elixir_thresh)
    │
    ├─ [CLAN GAMES] nếu cfg.enable_clan_games:
    │    run_events_open(host)
    │
    ├─ [REQUEST TROOPS] nếu cfg.request_troops:
    │    auto_request()
    │
    ├─ find_and_tap_collectors()          # Tap collectors
    │
    ├─ search_attack()                    # Mở attack menu
    │
    ├─ [SEARCH LOOP]
    │    while not stop_event:
    │       ├─ if connection_lost: boot_recovery
    │       ├─ if not wait_for_scout_screen():
    │       │      boot_recovery
    │       ├─ for attempt in 1..3:
    │       │      if is_next_button_present(): break
    │       │      sleep(2)
    │       ├─ e_gold, e_elixir, e_de = extract_resources()
    │       │
    │       ├─ if loot >= thresholds:
    │       │      ATTACK_FUNCS[cfg.attack](cfg)
    │       │      wait_battle_end()
    │       │      if cfg.enable_stats:
    │       │           stars = get_stars_from_screen()
    │       │           loot = gain_resources(stars)
    │       │           save to Stats_{village}.json
    │       │      return_home()
    │       │      break
    │       └─ else:
    │              search_next()
    │
    ├─ final connection check
    └─ cycle_count += 1
```

---

## 8. CÁC MODULE CON

### 8.1 `ensure_home_base.py`

```python
def ensure_home_base(max_wait=50):
    print("🧠 Checking if we're on the home base screen...")
    start_time = time.time()

    while time.time() - start_time < max_wait:
        if detect_home_base():
            print('✅ Home base confirmed.')
            return True
        print('⏳ Still not on home base. Retrying in 5s...')
        time.sleep(5)

    print('❌ Failed to detect home base. Initiating reboot sequence...')
    boot_recovery()
    return ensure_home_base(max_wait=20)
```

### 8.2 `detect_home_base.py`

Kiểm tra 3 dấu hiệu:
1. Template `game_setting.png` khớp tại ROI `(1445,499,1599,708)` score ≥ 0.7
2. Template `shop.png` khớp toàn ảnh score ≥ 0.7
3. OCR crop `(1408,826,1582,886)` chứa chữ "shop"

### 8.3 `boot_recovery.py`

```python
def boot_recovery():
    host = main.host
    if not host:
        raise RuntimeError('No emulator selected for boot_recovery()')

    print('🔁 Restarting Clash of Clans...')

    # Force-stop
    subprocess.run(
        [ADB_BIN, '-s', host, 'shell', 'am', 'force-stop',
         'com.supercell.clashofclans'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )

    # Launch via monkey
    subprocess.run(
        [ADB_BIN, '-s', host, 'shell', 'monkey',
         '-p', 'com.supercell.clashofclans',
         '-c', 'android.intent.category.LAUNCHER', '1'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )

    print('⏳ Waiting 10 seconds for game to load...')
    time.sleep(10)

    print('👆 Dismissing pop-ups…')
    subprocess.run(
        [ADB_BIN, '-s', host, 'shell', 'input', 'tap', '146', '487'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )
```

### 8.4 `home_routine.py` — Auto Upgrade Wall

```
handle_home_resources(wall_level, gold_thr, elixir_thr)
    gold, elixir = get_home_resources()   # OCR từ home screen
    if gold >= gold_thr:   upgrade_wall('gold', wall_level)
    if elixir >= elixir_thr: upgrade_wall('elixir', wall_level)

upgrade_wall(resource, wall_level):
    while attempts < 3:
        coords = find_all_wall_coords()   # scan template wall.png
        # Loại bỏ những tọa độ đã thử
        # Tap wall → tap home để về vị trí
        if validate_wall_tap(wall_level):
            # Tap GOLD_UPGRADE hoặc ELIXIR_UPGRADE
            # validate_upgrade_window() → tap CONFIRM
            return True
        attempts += 1
```

### 8.5 `request_troops.py`

```
auto_request()
    if not ensure_home_base(): return False
    tap(ARMY_BUTTON)              # (63, 653)
    img = adb_screenshot('request_troops')
    header = OCR(vùng 199,64,929,121)
    if không match keyword ARMY/RECIPES/MY/SAVED:
        tap(CLOSE_BUTTON); return False
    if not is_request_button_present(img):
        tap(CLOSE_BUTTON); return False
    if is_castle_cake_avail(img):
        return True                 # Đã tự đăng ký từ trước
    tap(REQUEST_BUTTON_TAP)         # (1491, 712)
    sleep(0.7)
    tap(SEND_BUTTON)                # (970, 627)
    tap(CLOSE_BUTTON)
```

### 8.6 `clan_capital.py` (trong `main.py`)

4 phase:

```
clan_capital(cfg, threshold=0.65) → bool
    phase1: tap vào scenery làng → zoom → tap làng
    phase2: match template để vào CC screen
    phase3: quét 9 làng → tìm làng còn attack
    phase4: chọn army + drop troop + spell
```

### 8.7 `smart_train.py`

```
smart_train(cfg)
    if not _validate_army_window(): return
    army_ok  = _validate_troops(cfg)
    spell_ok = _validate_spells()
    siege_ok = _validate_siege()
    if all: return
    if not army_ok:  train_troops(cfg)
    if not spell_ok: train_spells(cfg)
    if not siege_ok: train_slammer()
    tap(CLOSE_ARMY_WINDOW)
```

Logic train:
- Dragon: **9 dragon + balloon** (space 20/dragon, 5/balloon)
- Electro Dragon: **7 ED + balloon** (space 30/ED)
- Rage + Freeze: chia theo spell space (max 11 slot)
- Slammer: 3×slammer

### 8.8 `quick_train.py`

```
quick_train(use_army)
    if not _validate_army_window(): return
    tap(ARMY_RECIPE_PANE)   # (777, 90)
    if match use_button.png tại ROI slot_roi score ≥ 0.9:
        tap(center of use_button)
        if match use_army_recipe_window.png score ≥ 0.9:
            tap(972, 584)   # Confirm
    tap(CLOSE_ARMY_WINDOW)
```

### 8.9 `clan_games.py`

```
run_events_open(host)
    tap(354, 830)         # Events button
    screenshot → match EVENTS_TPL tại (605,8,1038,125)
    if không có → return
    Scroll tìm Clan Games card
    tap OPEN button
    if is_finished → tap X
    if is_busy → tap X
    choose_game(host)     # Chọn task và tap START
```

---

## 9. QUẢN LÝ EMULATOR

### 9.1 Ma trận lựa chọn

| Emulator | Host | Port lock | Manager |
|---|---|---|---|
| MEmu | `127.0.0.1:21503` | 6200 | `memu_manager.py` |
| BlueStacks | `127.0.0.1:5556` | 6201 | `bluestacks_manager.py` |
| LDPlayer | `127.0.0.1:5555` | 6202 | `ldplayer_manager.py` |
| LDPlayer Multi | `127.0.0.1:{5555+idx}` | 6202+idx | `ldplayer_manager.py` |

### 9.2 `ensure_memu()` / `ensure_bluestacks()` / `ensure_ldplayer()`

```
1. find_tools() → tìm MEmu.exe / HD-Player.exe / LDPlayer.exe
2. Check config (resolution, ADB, render mode)
3. Nếu sai → setconfigex + restart
4. start_and_connect() → ADB connect loop (timeout)
5. wait_for_home_icon() → xác nhận app Clash đã load
```

---

## 10. MULTI-VILLAGE FLOW

```
Multi-Village tab → user chọn làng → save_village_config(idx, cfg)
                                          │
                                          ▼
                                  profiles/Village_{idx}.json
                                  profiles/account_{idx}.png

bot_loop:
    if enable_multi_account:
        for idx in selected_villages:
             switch_to_village(idx)
                 ├─ tap Settings (1534, 649)
                 ├─ tap Switch-Account button
                 ├─ run_ahk('bypass_screen.ahk')  # MEmu only
                 ├─ get_latest_memu_screenshot()
                 ├─ match is_account_loaded.png
                 │    score ≥ 0.85 → list đã load
                 ├─ tap VILLAGE_COORDS[idx]
                 └─ tap home

             # Merge cfg
             merged = cfg + village_cfg
             while time < interval_secs:
                 one_cycle(merged)
```

**Wizard** (`village_wiz.py`):
- Khi bật multi-làng lần đầu, `bridge.requestWizard.emit(indices)`
- GUI mở `QWizard` gồm: Intro → ConfigPage cho từng làng → Conclusion
- Khi click **Finish**: `save_all()` ghi `Village_i.json` + emit `wizardDone`

---

## 11. THREADING MODEL

```
┌──────────────────────────────────────────────────────┐
│ MAIN THREAD (Qt)                                     │
│   • MainWindow + toàn bộ widget                       │
│   • Nhận log qua TimestampStream.new_line signal     │
│   • QTimer 5s → refresh stats                        │
│   • Nhận bridge.requestWizard / wizardDone           │
└──────────────────────────────────────────────────────┘
              ▲                               │
              │ Qt signal                     │ QtThreadCompat.start()
              │                               ▼
┌──────────────────────────────────────────────────────┐
│ WORKER THREAD (QThread)                              │
│   • main.bot_loop(cfg)                               │
│   • one_cycle() → điều khiển ADB + OCR + CV          │
│   • pause_event.wait() tại mọi bước nguy hiểm        │
│   • stop_event.set() để dừng                         │
└──────────────────────────────────────────────────────┘
```

- `pause_event` (threading.Event) — **set** = đang chạy, **clear** = paused
- `stop_event` (threading.Event) — **set** = dừng khẩn
- `QtThreadCompat` bọc `QThread` nhưng giả lập API `threading.Thread` (`join`, `is_alive`, `daemon`)

---

## 12. XỬ LÝ LỖI & RECOVERY

| Tình huống | Xử lý |
|---|---|
| **Mất home screen** | `ensure_home_base()` → `boot_recovery()` → retry |
| **Connection lost** | Detect qua 4 template (`Another_device.png`, `Connection_lost.png`, `Client_error!.png`, `rate_coc.png`) → `boot_recovery()` |
| **Screenshot lỗi** | `take_screenshot()` retry 4 lần, sau đó `boot_recovery()` |
| **Blank screen** (stddev < 1.0) | Retry, sau đó `boot_recovery()` |
| **Wall upgrade fail 3 lần** | Skip (không upgrade wall đó) |
| **Clan Capital fail** | Skip CC, tiếp tục cycle |
| **Emulator busy** | Warning dialog, abort start |
| **Template missing** | Log warning, skip bước đó |

---

## 13. LƯU SETTINGS

```json
// settings.json — Lưu toàn bộ state GUI
{
    "gold_threshold": 650000,
    "elixir_threshold": 650000,
    "dark_elixir_threshold": 5000,
    "upgrade_wall": false,
    "wall_level": 5,
    "wall_gold_threshold": 5000000,
    "wall_elixir_threshold": 5000000,
    "enable_clan_games": false,
    "enable_multi_account": false,
    "request_troops": true,
    "attack": "Dragon_Attack",
    "train_mode": "smart",
    "quick_slot": 1,
    "enable_stats": false,
    "enable_clan_capital": false,
    "capital_hall_level": 9
}
```

```
profiles/
├── Village_{idx}.json   ← Config riêng cho từng làng
├── account_{idx}.png    ← Ảnh chụp tài khoản Supercell
├── Stats_{idx}.json     ← Thống kê loot/attack/stars
├── accounts.txt         ← Số account đã detect
└── clan_capital_tpl.txt ← Cache tên template CC cuối cùng
```

**Load**: `load_settings()` khi mở GUI
**Save**: `closeEvent()` khi đóng GUI + nút Save trong Multi-Village tab

---

## 14. ATTACK DISPATCH

```python
ATTACK_FUNCS = {
    'Dragon_Attack':        run_attack,
    'ElectroDragon_Attack': run_attack,
}

# Trong one_cycle:
attack_fn = ATTACK_FUNCS.get(cfg['attack'])
attack_fn(cfg)
```

Hàm `run_attack` (trong `attacks/attacks.py` — **chưa decompile**) có nhiệm vụ:
1. Chọn điểm drop lính (dùng `get_glow_drop_points_poly`)
2. Drop lính theo thứ tự
3. Drop spell
4. Đợi battle end

---

## 15. UTILITIES NHANH

| Hàm | Chức năng |
|---|---|
| `take_screenshot()` | ADB `screencap -p`, retry 4 lần, kiểm tra PNG signature + blank screen |
| `imread_unicode()` | Đọc ảnh bằng `cv2.imdecode` (hỗ trợ path Unicode), retry 3 lần |
| `ocr_reader.reader` | EasyOCR lazy-load, GPU off, thread-safe singleton |
| `run_ahk(script, wait)` | Chạy AutoHotkey v2 script |
| `run_adb(cmd_list)` | Wrapper `subprocess.run` với `-s host` |

---

## 16. ĐIỂM CẦN LƯU Ý KHI PORT

1. **ADB bundle** phải ở `BASE_DIR/adb/adb.exe` + các DLL WinApi
2. **Resolution**: Chuẩn hóa `860×732 @ 160dpi` (hoặc `1600×900 @ 300dpi` cho bản gốc)
3. **Resolution mismatch** → bot sẽ fail template matching
4. **EasyOCR** cần model (~100MB) tải lần đầu
5. **Multi-village** cần Supercell ID đã add sẵn trong game
6. **LDPlayer Multi** cần `ldconsole.exe` trong PATH hoặc cache
7. **Clan Capital** cần scenery mặc định để detect boat
8. **Wall upgrade** cần ảnh `walls/{level}/Validate_Upgrade/verify_wall_level.png`

---

## 17. SƠ ĐỒ TỔNG QUÁT

```
┌─────────────┐    emit signal    ┌──────────────┐
│  MainWindow │◄─────────────────►│    bridge    │
│  (PyQt5)    │                   │  (QObject)   │
└──────┬──────┘                   └──────┬───────┘
       │                                  │
       │ QtThreadCompat.start()           │
       ▼                                  │
┌──────────────────────────────────────────┴──────┐
│           main.bot_loop(cfg)                    │
│  ┌────────────────────────────────────────────┐ │
│  │  setup_emulator() → ensure_*               │ │
│  └────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────┐ │
│  │  loop one_cycle():                         │ │
│  │   • ensure_home_base                       │ │
│  │   • multi_zoom_out                         │ │
│  │   • smart_train / quick_train              │ │
│  │   • handle_home_resources (wall)           │ │
│  │   • run_events_open (Clan Games)           │ │
│  │   • auto_request (troops)                  │ │
│  │   • find_and_tap_collectors                │ │
│  │   • search_attack → extract_resources      │ │
│  │   • ATTACK_FUNCS[type](cfg)                │ │
│  │   • gain_resources → save Stats_{i}.json   │ │
│  └────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
       │
       │ ADB commands
       ▼
┌─────────────┐
│  Emulator   │  ← MEmu / BlueStacks / LDPlayer
│  (Android)  │
└─────────────┘
```

---

## 18. CHANGELOG / TODO (suy luận từ code)

### Bugs tiềm ẩn trong bản decompile
- `village_wiz.py`: `run_village_wizard()` không nhận được `indices` khi gọi từ bot_loop (emit `object` nhưng trong bridge handler dùng `run_village_wizard(indices, 0)` với `start` là list → OK)
- `main.py`: `_collect_cfg()` có 2 key trùng `enable_stats` (giữ nguyên)
- `main.py`: `if cfg['attack'] == 'Dragon attack':` (lowercase) sẽ không match `'Dragon_Attack'` → nhánh này thực tế không chạy
- `stats_tab.py`: `self.tab_vill` được add widget vào `session_layout` nhưng không set parent chuẩn → có thể memory leak

### Điểm cần verify khi rebuild
- Đường dẫn `Templates/` có đúng cấu trúc không
- File `adb/adb.exe` + DLL có tồn tại không
- Python version phải ≥ 3.8 (do dùng `X | None` type hints)
- PyQt5 phải cài `PyQt5==5.15.x`

---

📌 **Tóm lại**: Simplicity v3.50 là bot farm Clash of Clans với kiến trúc **GUI thread + Worker thread**, sử dụng **template matching + OCR** để điều khiển game qua ADB, hỗ trợ 3 emulator, multi-village, multi-train mode, auto wall upgrade, Clan Games và Clan Capital. Toàn bộ logic điều khiển nằm trong `main.py::one_cycle()`, được gọi lặp đi lặp lại cho đến khi user nhấn **Stop**.
```

---

Lưu file này thành **`SIMPLICITY_v3.50_DOCS.md`** nhé. Bạn có thể mở bằng VS Code / Obsidian / Typora để xem đúng format Markdown (mục lục, code block, bảng, sơ đồ ASCII đều render đẹp).

Nếu cần mình có thể thêm:
- **Danh sách đầy đủ hằng số tọa độ** (tất cả ROI, tap coord) thành bảng riêng
- **Sequence diagram** dạng Mermaid
- **FAQ / Troubleshooting** dựa trên các lỗi thường gặp
- **Bản tiếng Anh** nếu muốn chia sẻ cho team nước ngoài

Cứ nói nhé!