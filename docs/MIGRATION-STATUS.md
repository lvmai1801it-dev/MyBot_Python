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
                                  session, orchestrator, worker, settings, attack
                                  tests (106 total)
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

## Verification commands

```powershell
.venv\Scripts\python.exe -m compileall -q COCbot
.venv\Scripts\python.exe -m unittest discover -s tests -t .
.venv\Scripts\python.exe -m COCbot.gui.app   # legacy GUI smoke
```

## Next modules

1. `COCbot/main.py` — composition root: wire config, logger, ADB, vision,
   settings/attack view-models, and workers; replace the legacy launcher.
2. Purge batch 2: archive the legacy packages once parity tests pass.
3. Optional: migrate remaining features (village/upgrade, accounts, clan,
   statistics, logs) using the same vertical-slice pattern.
