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
tests/unit/                       Model, config, ADB, vision, emulator tests (55 total)
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

## Verification commands

```powershell
.venv\Scripts\python.exe -m compileall -q COCbot
.venv\Scripts\python.exe -m unittest discover -s tests -t .
.venv\Scripts\python.exe -m COCbot.gui.app   # legacy GUI smoke
```

## Next modules

1. `app/orchestrator.py` + `workers/` — QThread worker, pause/stop protocol.
2. `features/settings/` — reference vertical slice.
3. `features/attack/` — reference complex feature (YOLO + worker + live UI).
4. `COCbot/main.py` — composition root.
5. Purge batch 2: archive the legacy packages once parity tests pass.
