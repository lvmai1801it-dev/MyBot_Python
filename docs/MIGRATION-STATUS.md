# Migration status — MVVM + Feature-Driven

## Completed

### Purge batch 1 (dead code archived)

Moved to `_archive_old_code/` (see its `README.md`):

- `COCbot/platform/ahk.py`
- `COCbot/vision/read_text/gold.py`
- `COCbot/vision/read_text/elixir.py`
- `COCbot/vision/read_text/dark_elixir.py`

The active architecture (`run.py` → `COCbot.gui.app`) is unchanged and the GUI
smoke test still passes.

### Module 1 — Contracts, domain models, config, logging

```text
COCbot/core/ports.py              Protocol contracts (Adb, Emulator, Capture,
                                  Detector, OCR, Settings, Clock, EventSink, Bot)
COCbot/core/errors.py             Typed exception hierarchy
COCbot/core/config/               AppConfig schema, paths, coordinates, defaults
COCbot/core/logging/              BotFormatter, rotating logger, SUCCESS level
COCbot/models/                    Enums, geometry, frame, resources, village,
                                  account, attack, bot state, emulator
tests/unit/                       Model, config, ADB, vision, redline, emulator,
                                  session, orchestrator, worker, settings, attack,
                                  accounts, logs, statistics, village, clan,
                                  attack execution, main view-model tests
                                  (160 total)
tests/architecture/               Qt-free / layering / docstring contracts
pyproject.toml                     ruff, mypy, pytest, import-linter config
```

Key contracts:

- `AppConfig.from_legacy_dict()` / `to_dict()` preserve the existing
  `settings.json` shape, so old and new code can share the file.
- `core/` and `models/` are verified to have **zero PyQt5 imports** and no
  imports from `gui`, `app`, `game`, `attack`, `vision`, `workers`, `features`.
- `ProjectPaths` is the only path resolver; new code must not hard-code paths.
- `NavigationPoints` / `SCREEN` centralize tap targets and screen geometry.

### Module 2 — ADB, capture, YOLO, OCR, templates, emulators

```text
COCbot/core/adb/
├── client.py       AdbClient (AdbPort) with retries + injectable runner
├── commands.py     pure argument builders
└── tap_guard.py    Shop-zone protection

COCbot/core/vision/
├── image.py        Unicode-safe imread/imwrite, crop, blank detection
├── capture.py      ScreenCapture (CapturePort) with retries/blank check
├── detector.py     YoloDetector (DetectorPort), lazy Ultralytics load
├── ocr.py          NumberOcr (OcrPort), PaddleOCR → Tesseract fallback
└── templates.py    TemplateMatcher with cache + path-traversal guard

COCbot/core/emulator/
├── base.py         shared runner/tool discovery
├── memu.py         memuc listvms/start/isvmrunning
├── ldplayer.py     ldconsole list2/launch/isrunning
├── bluestacks.py   HD-Player instance
├── setup.py        start → ADB connect → launch CoC
└── registry.py     create_emulator(type)
```

Hardware verification (MEmu at `127.0.0.1:21503`):

- ADB connected.
- Captured a real 860x732 frame in 0.34 s (402,578 bytes PNG).
- `settings_logo.png` template score **1.00** on the live home screen.
- `MemuEmulator` discovered `F:\Microvirt\MEmu` and reported instance 0 running.

### Module 3 — Session, orchestrator, and QThread workers

```text
COCbot/app/session.py       thread-safe pause/stop/counters (no Qt)
COCbot/app/orchestrator.py  CycleStep protocol, CycleContext, BotOrchestrator
COCbot/workers/_bootstrap.py  torch-before-PyQt5 import guard
COCbot/workers/base_worker.py generic QThread + signals
COCbot/workers/task_worker.py one-shot heavy task worker
COCbot/workers/bot_worker.py  wraps BotEnginePort, forwards BotEvent
```

Live integration test (real MEmu, offscreen Qt):

```text
QCoreApplication + BotWorker + BotOrchestrator + ScreenCapture
→ thread_finished True
→ EVENT INFO "Bot started"
→ EVENT INFO "captured 860x732 in worker thread"
→ EVENT INFO "Bot stopped"
```

This proves the capture path runs off the GUI thread and events return through
`pyqtSignal`.

### Module 4 — Settings vertical slice (MVVM)

```text
COCbot/ui_components/
├── theme.py       palette + compact QSS + apply_theme()
├── cards.py       Card container
├── inputs.py      LabeledSpinBox/LineEdit/ComboBox/ToggleRow
├── buttons.py     Primary/Secondary/Danger buttons
└── status.py      inline StatusLabel

COCbot/viewmodels/base_viewmodel.py  QObject base, busy/error signals
COCbot/features/settings/
├── model.py       SettingsModel (pure Python, no Qt)
├── viewmodel.py   SettingsViewModel (QObject + signals only)
└── view.py        SettingsView (layout + signal binding only)
```

The view never touches the model or game logic. Every edit calls a
view-model command; `dirty_changed` enables Save; `loaded`/`saved`/`error_occurred`
flow back through signals. Verified with an offscreen GUI test and a rendered
screenshot (`artifacts/settings_view.png`).

### Module 5 — Attack vertical slice (complex feature)

```text
COCbot/core/vision/redline.py       YOLO-seg + OpenCV redline fallback, geometry
COCbot/features/attack/
├── model.py       AttackModel/AttackStep: capture → detect → redline → plan
├── viewmodel.py   AttackViewModel: TaskWorker scan/deploy + progress signals
└── view.py        AttackView: scan button, plan summary, live log
```

The model is pure Python and supports a safe dry-run deployment by default.
`AttackViewModel` runs scans in `TaskWorker`; progress and plan events return to
the GUI thread through `pyqtSignal`.

Live MEmu verification (no YOLO weights installed):

```text
source=cv  detections=0  redline_edges=4  valid=True
progress=Capturing → Detecting targets → Detecting redline → Building plan → Complete
QThread scan: plan_ready emitted, status "Plan ready: none · redline cv · 0.34s"
```

Rendered screenshot: `artifacts/attack_view.png`.

### Review / refactor pass

- `AppConfig` now preserves unknown `settings.json` keys through `extra`, so
  saving from the new UI cannot silently drop future/legacy fields.
- Settings side edit updates both `attack.side` and `recipe.side`; ADB host is
  validated before saving.
- `BaseWorker` always emits `work_finished` (with `None` on failure), so
  view-models always clear their busy state.
- Fixed card styling that hid primary button text, cleaned unused imports,
  and made emulator/worker tests share one `QApplication`.

### Module 6 — Composition root and MVVM shell

```text
COCbot/main.py                     composition root / new entry point
COCbot/core/config/store.py        live ConfigStore shared by features
COCbot/viewmodels/main_viewmodel.py start/stop/pause + BotWorker lifecycle
COCbot/views/main_window.py        frameless shell, Settings/Attack tabs, footer
COCbot/ui_components/title_bar.py  draggable header surface
```

Run the new shell:

```powershell
python -m COCbot.main
```

`run.py` still launches the legacy GUI until the remaining features reach
parity. The new entry point imports torch before PyQt5, builds the logger, ADB,
capture/detector/redline, both feature view-models/views, the orchestrator, and
the shell. A smoke hook (`MYBOT_SMOKE_TEST=1`) exits after 1.5 s for CI.

Settings saved from the new UI update the shared `ConfigStore`, so the attack
model picks up recipe changes without a restart.

### Module 7 — Accounts vertical slice

```text
COCbot/features/accounts/
├── model.py       AccountsModel: profiles + switch_accounts.json (no Qt)
├── viewmodel.py   AccountsViewModel: worker-backed pull/push/switch/delete
└── view.py        AccountsView: profile picker, actions, auto-switch card
```

`AccountStorePort` in `core/ports.py` isolates the feature from the legacy
`SharedPrefsManager`; `COCbot.main` injects the legacy manager as a transitional
adapter. Pull/Push/Switch/Delete run in `TaskWorker`, so the GUI never freezes
during ADB file copies. Profile list/root status refresh automatically after
each mutation.

Verified on the real MEmu device: profiles list, root status, ADB operations
are wired through the worker. Rendered screenshot: `artifacts/accounts_view.png`.

### Module 8 — Logs vertical slice

```text
COCbot/features/logs/
├── model.py       LogsModel: bounded buffer + level/search filter + export
├── viewmodel.py   LogsViewModel: BotEvent ingestion + signals
└── view.py        LogsView: filterable table, clear, export
```

The shell subscribes `MainViewModel.event_emitted` to `LogsViewModel.append_event`,
so every orchestrator event appears in the Logs tab. Rows are coloured by level,
filterable by exact level or text, and exportable to a UTF-8 text file. Startup
events (shell ready, ADB connected/offline) are logged before the view is shown.

Rendered screenshot: `artifacts/logs_view.png`.

### Module 9 — Statistics vertical slice

```text
COCbot/features/statistics/
├── model.py       StatisticsModel: read/aggregate/reset Stats_N.json
├── viewmodel.py   StatisticsViewModel: snapshot + reset signals
└── view.py        StatisticsView: totals, per-village table, reset
```

The model reads `profiles/Stats_1.json … Stats_5.json`, aggregates loot, attacks,
and star buckets, and resets all files atomically. The view shows overall totals
and a per-village table with the last update time. Rendered screenshot:
`artifacts/statistics_view.png`.

### Module 10 — Village/Upgrade and Clan config slices

```text
COCbot/features/village/   wall settings + Hero/Defense/Army/Resource/Other lists
COCbot/features/clan/      Clan Games, Clan Capital, donation toggle
```

Both features share the live `ConfigStore` and `SettingsPort`, so saving from
Settings/Village/Clan reloads the other config views without a restart. Wall is
editable; the other upgrade groups are config-only, matching the original
product requirement. Clan actions are also config-only in this build; the
legacy runtime still performs the actual gameplay.

### Launcher

`run.py` is now a single entry point:

```powershell
python run.py           # legacy GUI (full farming runtime)
python run.py --mvvm    # new MVVM shell
```

### Module 11 — Clean runtime port, stage 1 (village collectors)

```text
COCbot/features/village/model.py
├── VillageActions   return home + template-match collector taps
└── VillageStep      CycleStep adapter fed by the orchestrator
```

`VillageActions` uses the new `AdbPort`, `CapturePort`, `TemplateMatcher`, and
`ClockPort`; no legacy imports. It is dry-run by default (`execute=False`) and
is now the first step in the shell orchestrator:

```text
VillageStep (dry-run) → AttackStep (scan/dry-run)
```

Real-input stages still require device calibration before enabling:
attack search/drop/battle-end, wall/hero/defense upgrades, Clan actions.

### Module 12 — Clean runtime port, stage 2 (attack execution)

```text
COCbot/features/attack/army_bar.py   ArmyBarScanner + template normalization
COCbot/features/attack/executor.py   AttackExecutor + edge point spreading
COCbot/features/attack/battle.py     search/scout/end/stars/loot + FullAttackStep
```

`FullAttackStep` now runs the clean attack pipeline:

```text
return home → search → wait scout → capture/detect redline → scan army bar
→ deploy along edge → wait battle end → read stars/loot → return home
```

It remains **dry-run** in the shell (`execute=False`): it captures, scans the
army bar, plans deploy points, and reports them without tapping. Real input is
available by constructing `BattleService`, `AttackExecutor`, and `FullAttackStep`
with `execute=True` after device calibration.

## Verification commands

```powershell
.venv\Scripts\python.exe -m compileall -q COCbot
.venv\Scripts\python.exe -m unittest discover -s tests -t .
.venv\Scripts\python.exe -m COCbot.gui.app   # legacy GUI smoke
```

## Remaining work

1. Stage 3: wall/hero/defense upgrade execution, storage detection, zoom.
2. Stage 4: Clan Games / Clan Capital / Donate execution.
3. Calibrate attack/village stages on MEmu, then enable `execute=True`.
4. Purge batch 2 and switch the default launcher only after parity tests pass.
