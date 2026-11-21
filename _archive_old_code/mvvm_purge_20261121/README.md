# MVVM purge — 2026-11-21

Toàn bộ shell MVVM (`python run.py --mvvm`) đã được gỡ khỏi runtime và lưu
vào đây. Lý do: track song song legacy/MVVM gây vòng lặp bảo trì
("vẽ bánh xe"), shell không ổn định khi chạy thật, và engine gameplay vẫn
là legacy. Sau purge, `python run.py` (GUI legacy) là entry point duy nhất.

## Đã gỡ (150 file)

| Vị trí | Ghi chú |
|---|---|
| `COCbot/main.py`, `COCbot/qt_startup.py` | composition root + import guard của shell |
| `COCbot/views/`, `COCbot/viewmodels/`, `COCbot/workers/`, `COCbot/ui_components/` | UI shell + QThread + theme |
| `COCbot/features/{settings,attack,accounts,logs,statistics,clan,training}/` | 7 feature MVVM (GUI legacy đã có tab tương ứng) |
| `COCbot/features/village/{model,view,viewmodel}.py` | 3 file Qt của feature village |
| `COCbot/app/{session,orchestrator,legacy_engine}.py` | orchestrator + engine bridge |
| `COCbot/core/emulator/`, `COCbot/core/vision/{detector,redline}.py` | clean-port emulator + YOLO/redline detector |
| `tests/gui/`, 17 file `tests/unit/` | test của các module trên |
| `tools/smoke_mvvm_attack.py`, `tools/rehearse_mvvm_attack.py` | smoke tool của shell |

## Đợt 2 (audit cấu trúc, cùng ngày)

Các module còn lại mà không còn ai dùng sau purge (đối chiếu bằng
`tools/audit_structure.py` — 0 import gãy, 0 mồ côi sau đợt này):

| Vị trí | Ghi chú |
|---|---|
| `COCbot/features/village/wall.py` + `tests/unit/test_wall.py` | WallUpgrader quét map theo level — đã bị `HeroDefenseUpgrader.upgrade_walls_via_panel` thay thế |
| `COCbot/core/adb/mititouch.py` | adapter pinch u2 — chỉ shell cũ dùng |
| `COCbot/core/config/store.py` | ConfigStore — chỉ features MVVM dùng |
| `COCbot/core/logging/` | rotating logger — runtime legacy dùng stdout/GUI log |
| `COCbot/models/{account,bot_state,emulator,village}.py` | dataclass MVVM-era; `models/attack.py` thu về chỉ còn `Detection`; enums bỏ `BotPhase/LogLevel/AccountSwitchMode` |
| `COCbot/core/ports.py` | thu về 5 protocol còn dùng: Adb/Capture/Ocr/Clock/Logger |

## ĐÃ GIỮ (vì farm bot legacy đang dùng thật)

- `COCbot/features/village/`: `upgrades.py`, `runner.py`, `wall.py`,
  `planner.py`, `targets.py`, `resources.py` — hệ auto-upgrade
  (Builds & Heroes / Army / Equipment / Pets + wall qua Build panel +
  ResourceReader GLM-OCR). Hook chạy mỗi cycle được cài bởi
  `COCbot/app/upgrade_hook.py` từ `MainWindow.on_start` (port từ
  `LegacyEngine._run_upgrades`).
- `COCbot/core/` (trừ emulator/detector/redline) + `COCbot/models/`:
  thư viện pure-python cho features/village ở trên.
- Mọi thứ legacy: `gui/`, `app/bootstrap`, `attack/` (ONNX redline +
  sanitize + verify-redrop), `game/`, `vision/`, `platform/`, `emulator/`.

## Khôi phục

```
# từ src/, git checkout commit trước purge:
git log --oneline --follow -5 _archive_old_code/mvvm_purge_20261121
# hoặc copy ngược thư mục này về vị trí cũ rồi chạy lại tests.
```
