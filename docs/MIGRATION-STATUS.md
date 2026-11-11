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
                                  attack execution, wall calibration,
                                  hero/defense framework, training, legacy
                                  engine, resource bar, main view-model tests
                                  (223 total)
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

### Module 13 — Clean runtime port, stage 3 (village utilities)

```text
COCbot/core/adb/multitouch.py       uiautomator2 pinch/zoom adapter
COCbot/features/village/model.py    storage/resource/wall/close/zoom routines
```

`VillageActions` now provides:

- collector taps (existing)
- full-storage icon detection (gold/elixir/DE)
- home resource OCR (opt-in: `read_resources=True`)
- common popup close-template scan
- wall template scan (`wall.png` … `wall_4.png`)
- pinch-to-zoom through `MultiTouchPort`

Live MEmu test (home village, CoC launched):

```text
VillageActions.run(dry-run): 0.76 s
collectors found: 9
full storages: DE = 1
zoom_out(3): True (uiautomator2, ~4 s)
wall scan: 0 matches on the current wall level (templates need level calibration)
```

Resource OCR is deliberately off by default: PaddleOCR initialisation costs
~19 s on first use, which would break the sub-second scan loop.

### Module 14 — Clean runtime port, stage 3b (wall calibration + upgrade)

```text
COCbot/features/village/wall.py              WallUpgrader + WallUpgradePlan
tools/calibrate_wall_templates.py            score report for wall templates
```

`WallUpgrader` scans `walls/<level>/*.png` with a configurable threshold
(default 0.65 instead of the legacy 0.90), deduplicates points, validates a
tapped wall against `walls/<level>/Validate_Upgrade/verify_wall_level.png`, then
taps the gold/elixir upgrade button, confirm, and close. Real input is still
disabled in the shell (`execute=False`).

Live MEmu calibration on the zoomed home screenshot:

```text
level 8 : 5 wall points, best 0.686, 1.03 s
level 17: 2 wall points, best 0.727, 0.98 s
```

Hero/defense upgrades are implemented in stage 3c below: the legacy project only
ever implemented wall upgrades, so the clean port drives the in-game
"Buildings & Heroes" panel with OCR row selection and template-validated
confirmation.

### Live input switches (MVVM shell)

The shell is dry-run by default. Enable real input explicitly:

```powershell
$env:MYBOT_LIVE_VILLAGE=1   # tap home + collectors
$env:MYBOT_LIVE_ATTACK=1    # full search/scout/attack (calibration required)
$env:MYBOT_LIVE_WALL=1      # wall upgrade execution (guarded by validation)
python run.py --mvvm
```

Live MEmu check with `MYBOT_LIVE_VILLAGE=1`:

```text
VillageActions.run(): ok=True, found=9, tapped=9, 6.73 s
```

A dry orchestrator cycle also produced real `BotEvent`s:

```text
INFO    7 collectors found (dry run); storages={'de': 1}
WARNING No attack target detected
ERROR   No attack target detected
```

This confirms the MVVM chain is live; the bot logic is simply gated.

### Module 15 — Clean runtime port, stage 3c (hero/defense upgrades)

```text
COCbot/features/village/upgrades.py          HeroDefenseUpgrader
tools/calibrate_upgrade_templates.py         template score / row report
Templates/upgrade/hero/*.png                 hero portraits (6)
Templates/upgrade/upgrade_button.png         map info-panel Upgrade button
Templates/upgrade/confirm_button.png         green CONFIRM button
Templates/upgrade/close_button.png           red X of the upgrade dialog
```

The game exposes hero/building upgrades through the **Buildings & Heroes**
panel (bottom-right quick access), so the flow is validated at every step:

1. `open_panel()` taps the quick access and verifies the panel title by OCR.
2. `rows()` reads the panel name column. The crop skips the icon column and the
   cost/time column, and keeps white names plus green "new" labels, then
   Tesseract returns line boxes.
3. `execute(name)` taps the matching row (exact substring, then fuzzy match for
   OCR slips such as `Elixir Catlector`), requires the dialog title to mention
   the target, requires `confirm_button.png` before tapping, and dismisses the
   dialog with `close_button.png`.
4. Dry-run is the default; `execute=True` is required to spend resources, and
   a missing template or an unexpected dialog title aborts without tapping.

`VillageActions` wires this in as `upgrade_target()`, `scan_upgrade_rows()`
and `open_upgrade_panel()`.

Calibration on the captured panel screenshot:

```text
1.000  upgrade_button.png
1.000  confirm_button.png
1.000  close_button.png
rows=10
  (620,108)  Barbarian King
  (620,168)  Hero Hall
  (620,227)  Elixir Catlector
  (620,309)  MonolitH
  (620,405)  Spell Tower
  (620,501)  Crafting Station
```

Live rehearsal on MEmu (no confirm tap, so no resources spent):

```text
panel True
ROW Barbarian King (620,108)
  dialog_open True | title: upgrade barbarian king to level 48?
  confirm@ (612,548) | dismiss: True
ROW Elixir Collector (620,227)
  dialog_open True | title: upgrade elixir collector to level 6?
  confirm@ (612,548) | dismiss: True
```

The only gated step is the CONFIRM tap itself: it runs only when the caller
passes `execute=True`, which the shell keeps off while the legacy farm engine
handles gameplay.

### Village tab target picker

```text
COCbot/features/village/targets.py     catalog + OCR name normalization
COCbot/features/village/view.py        four Build-panel tabs with target lists
COCbot/features/village/viewmodel.py   UpgradeScanWorker (QThread)
```

The Village tab now mirrors the in-game Build panel exactly:

```text
Buildings & Heroes | Army Upgrades | Hero Equipment | Hero Pets
```

Pressing **Scan from game** opens the panel, switches through the four tabs
(bottom tab buttons, verified by their header text) and pages each list:

1. each tab is switched and its title is confirmed before reading;
2. the name column is read with a single fast OCR pass per page, merged with
   the `Templates/buildings` label templates;
3. the list is swiped upwards until a page adds nothing new (max 7 pages),
   then scrolled back so the next scan starts at the top;
4. OCR slips map to the catalog (`Monolitn` → `Monolith`), bundle suffixes such
   as `x 4` are stripped, and UI labels (`Unequipped`, `Favorite target`) are
   rejected;
5. the panel closes and each tab's rows become unchecked entries.

Walls live inside the **Buildings & Heroes** tab (enable, level, thresholds)
together with the *heroes first* and *money buildings first* priority flags;
the other three tabs carry a single priority flag each.

Scanning is disabled while the bot is running so it never interrupts a farm
cycle. Ticked rows are saved into `hero_priorities` / `defense_priorities` / …
like before, so the executor can consume them once auto-upgrade is wired in.

### Building label templates and upgrade planning

```text
Templates/buildings/Buildings&Heroes.png   panel title
Templates/buildings/grandwarden.png        "Grand Warden" row label
Templates/buildings/minionprince.png       "Minion Prince" row label
Templates/buildings/wall.png               "Wall" label
COCbot/features/village/planner.py         ordering + wall builder reserve
```

Panel labels are matched as images, not text: any `Templates/buildings/*.png`
whose name maps to a known target is matched inside the panel name column and
merged with the OCR rows, replacing mangled names at the same y. The
`Buildings&Heroes.png` title is also used as a pixel-exact "panel is open"
check, so a tab that reads *Army Upgrades* is never mistaken for it. Item
names are shared with the scan, so `grandwarden.png` yields `Grand Warden`.

The **Buildings & Heroes** tab carries two extra priority flags — *heroes first*
and *money buildings first* — which the planner applies by classifying each
name with the catalog. When wall upgrading is enabled, one builder is reserved,
so with `builders = 3` the queue gets `budget = 2` and any extra target is
reported as skipped:

```text
plan_upgrades(config, builders_available=3)
  wall_reserved=True  reserved_for_walls=1  budget=2
  order=("Archer Queen", "Grand Warden")  skipped=("Monolith",)
```

Without wall upgrading the budget equals the builders available. Zero builders
plans nothing. The plan is exposed through `VillageViewModel.upgrade_plan()`
and stays a dry-run until execution is wired into the cycle.

### Builder-limited ticking and the upgrade runner

```text
COCbot/features/village/runner.py          UpgradeRunner
COCbot/features/village/upgrades.py        find_in_panel / upgrade_listed
```

The **Buildings & Heroes** tab shows `Builders free: N — tick up to N target(s)`
after a scan. Ticking more than the free builders immediately unticks the extra
rows; enabling walls drops the allowance to `N-1` because one builder is kept
for walls. The Army Upgrades, Hero Equipment and Hero Pets tabs accept exactly
one target each (one upgrade at a time).

**Upgrade now** asks for confirmation, then the runner:

1. reads the free builder count from the village;
2. tunes the queue: every free builder (minus the wall reserve) for Buildings &
   Heroes, one slot each for Army/Equipment/Pets, walls last;
3. for each building target, opens the panel, pages to its row, verifies the
   dialog title and the CONFIRM template, confirms, and repeats until that
   target no longer appears in the panel (maxed) or builders run out;
4. army/equipment/pet targets run exactly once per run;
5. if the confirm dialog stays open after the tap (the usual "not enough loot"
   signal) the run stops with `needs_loot=True` and asks the operator to start
   the bot so it can attack and earn resources before upgrading again.

The same runner is wired into the farm loop: `LegacyEngine` installs
`state.upgrade_hook` for the duration of the run, and `one_cycle` calls it
right after the home check/zoom-out, **before** the wall step. Each cycle it:

```text
read builders -> 0 free: "No free builder — skipping upgrades"
              -> >0: run the ticked targets (buildings first, walls keep one)
```

A tab runs when it is enabled **or** has ticked targets, so ticking rows and
pressing Save is enough for Start to upgrade them. With no ticks at all the
cycle logs `No upgrade targets selected — tick targets in Village and Save`.

`UpgradeRunner.run()` stays a dry-run when `execute=False`; the button passes
`execute=True` only after the confirmation dialog, and both Scan and Upgrade
are disabled while the farm bot is running.


### Module 16 — Training quick-train (farm prerequisite)

```text
COCbot/features/training/model.py   TrainingActions + TrainingStep
```

The clean training flow now opens Battle → Edit Army → Saved Recipes, taps the
Use button for the configured quick slot, confirms, closes the army window, and
sends `KEYCODE_BACK` to return home.

Live MEmu result:

```text
quick_train(slot=1): ok=True, taps=6, ~9 s
after: back on the home village
```

The shell orchestrator order is now:

```text
TrainingStep → VillageStep → FullAttackStep
```

With live flags, training and village collection are real; attack remains
dry-run until its device calibration is approved.

### Attack correctness fixes (redline / all troops / hero abilities)

- OpenCV redline edges are now **inset 45 px inside** the red line, and the
  polygon is returned for point validation.
- `AttackExecutor` skips any deploy point outside the redline polygon.
- When the plan side is random, troops are distributed across **all four**
  inset edges instead of one side.
- After the first wave, `FullAttackStep` re-scans the army bar and sweeps any
  remaining troop cards (up to two extra passes).
- Hero cards are deployed, then re-tapped **15 s later** to trigger abilities.
- A debug frame is saved to `debug/attack_redline_<ts>.png` with the redline
  polygon and deploy-edge points, so out-of-line taps can be inspected.

### Gameplay runtime reverted to legacy farm engine

The clean-port attack path is retained for future work, but the shell **Start**
button now uses the proven pre-MVVM gameplay loop:

```text
COCbot/app/legacy_engine.py  LegacyEngine
  → COCbot.app.bootstrap.bot_loop(cfg)
      → setup_emulator / prepare_main_village
      → one_cycle: training, collectors, wall, clan, search, attack,
        battle result, stats, account switching
```

`LegacyEngine` snapshots `AppConfig.to_dict()` and bridges the new session
controls to the legacy `state.stop_event` / `state.pause_event`. This restores
the old attack logic exactly while keeping the MVVM shell, workers, logs,
settings, accounts, and statistics UI.

## Verification commands

```powershell
.venv\Scripts\python.exe -m compileall -q COCbot
.venv\Scripts\python.exe -m unittest discover -s tests -t .
.venv\Scripts\python.exe -m COCbot.gui.app   # legacy GUI smoke
```

### Resource bar (start-driven village readout)

```text
COCbot/features/village/resources.py        ResourceReader + VillageResources
COCbot/viewmodels/resource_bar.py           view-model fed by the farm engine
COCbot/views/resource_bar.py                ResourceBar widget
COCbot/app/state.py                         resource_hook
COCbot/app/bootstrap.py                     _notify_resources at home/zoom-out
```

The shell shows a bar under the header on every tab with gold, elixir, dark
elixir, gems, and the builder counter (`available/total`).

**The bar is empty until the bot starts.** Pressing Start clears every cell,
then the legacy loop checks the home village, zooms out, and calls
`state.resource_hook`, which is installed by `LegacyEngine.run_forever` while
the run is active. The same hook fires at the start of every cycle right after
`multi_zoom_out`, so the counters stay current without any background polling.

Currency values come from the farm loop's own readout
(`read_current_resources()`, `prepare_main_village()`), which is the proven
reader for the top bar; the shell reader adds gems and the builder/lab counters
that the legacy code never reads:

```text
HOME_GEMS_REGION     Rect(685, 110, 130, 42)
HOME_BUILDERS_REGION Rect(740, 596,  64, 40)   # "3/6" above the Build button
```

Live run on MEmu (bar after Start, matching the on-screen HUD):

```text
VillageResources(gold=10128117, elixir=7822777, dark_elixir=90168,
                 gems=991, builders_available=3, builders_total=6)
```

## Remaining work

1. Clean attack port calibration (retained for future; shell uses legacy engine).
2. Stage 3c is done: templates captured in `Templates/upgrade/`, rows read by
   OCR, and the confirm step gated on `execute=True`. Next step is wiring it
   into the farm cycle once hero/defense priorities are enabled in settings.
3. Stage 4 clean port: Clan Games / Clan Capital / Donate execution.
4. Purge batch 2 only after the clean engine reaches parity with the legacy one.
