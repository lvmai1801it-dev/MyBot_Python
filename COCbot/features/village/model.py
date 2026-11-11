"""Village / upgrade feature domain model (pure Python, no Qt)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from threading import Event
from typing import Mapping

from COCbot.app.orchestrator import CycleContext, StepResult
from COCbot.core.config.coordinates import (
    HR_DARK_REGION,
    HR_ELIXIR_REGION,
    HR_GOLD_REGION,
    HR_WALL_ROI,
)
from COCbot.core.config.schema import (
    AppConfig,
    PriorityUpgradeConfig,
    UpgradeConfig,
    WallUpgradeConfig,
)
from COCbot.core.config.store import ConfigStore
from COCbot.core.ports import (
    AdbPort,
    CapturePort,
    ClockPort,
    LoggerPort,
    MultiTouchPort,
    OcrPort,
    SettingsPort,
)
from COCbot.core.vision.templates import TemplateMatcher
from COCbot.features.village.planner import UpgradePlan, plan_upgrades
from COCbot.features.village.runner import UpgradeRunner, UpgradeRunResult
from COCbot.features.village.upgrades import (
    HeroDefenseUpgrader,
    UpgradeResult,
    UpgradeRow,
)
from COCbot.features.village.wall import WallUpgrader, WallUpgradePlan
from COCbot.models.enums import BotPhase, UpgradeCategory
from COCbot.models.geometry import Point
from COCbot.models.resources import ResourceSnapshot


@dataclass(frozen=True)
class VillageSnapshot:
    """The upgrade configuration shown in the Village tab."""

    upgrades: UpgradeConfig


@dataclass(frozen=True)
class PanelScan:
    """One Build-panel scan: rows per tab plus the builder count."""

    rows: dict[str, tuple[str, ...]]
    builders_available: int | None = None
    builders_total: int | None = None


class VillageModel:
    """Load and persist the upgrade groups."""

    def __init__(
        self,
        store: ConfigStore,
        settings: SettingsPort,
        scanner: HeroDefenseUpgrader | None = None,
        resource_reader: object | None = None,
    ) -> None:
        """Share the live config, the settings port and the panel scanner."""
        self._store = store
        self._settings = settings
        self._scanner = scanner
        self._resource_reader = resource_reader

    def load(self) -> VillageSnapshot:
        """Return the current upgrade configuration."""
        return VillageSnapshot(upgrades=self._store.get().upgrades)

    def save(self, upgrades: UpgradeConfig) -> VillageSnapshot:
        """Persist *upgrades* and update the live config."""
        config = replace(self._store.get(), upgrades=upgrades)
        self._settings.save(config)
        self._store.set(config)
        return VillageSnapshot(upgrades=config.upgrades)

    def reset_defaults(self) -> UpgradeConfig:
        """Return the default upgrade configuration."""
        return AppConfig().upgrades

    def scan_panel(self) -> PanelScan:
        """Open the in-game Build panel, scan all tabs, and read builders."""
        if self._scanner is None:
            return PanelScan(rows={})
        from COCbot.features.village.targets import canonical_name

        scanned = self._scanner.scan_panel(execute=True)
        result: dict[str, tuple[str, ...]] = {}
        for tab, rows in scanned.items():
            names: list[str] = []
            seen: set[str] = set()
            for row in rows:
                name = canonical_name(row.name) or row.name
                key = name.strip().lower()
                if not key or key in seen:
                    continue
                seen.add(key)
                names.append(name.strip())
            result[tab] = tuple(names)
        builders = builders_total = None
        if self._resource_reader is not None:
            try:
                snapshot = self._resource_reader.read()  # type: ignore[attr-defined]
            except Exception:
                snapshot = None
            builders = getattr(snapshot, "builders_available", None)
            builders_total = getattr(snapshot, "builders_total", None)
        return PanelScan(
            rows=result,
            builders_available=builders,
            builders_total=builders_total,
        )

    def scan_targets(self) -> tuple[str, ...]:
        """Return every scanned row across the Build panel tabs."""
        names: list[str] = []
        for values in self.scan_panel().rows.values():
            names.extend(values)
        return tuple(names)

    def upgrade_plan(self, builders_available: int) -> UpgradePlan:
        """Return the persisted upgrade queue for the current builder count."""
        return plan_upgrades(self._store.get().upgrades, builders_available)

    def run_upgrades(self, execute: bool = False) -> UpgradeRunResult:
        """Run the upgrade queue, reading the builder count from the village."""
        if self._scanner is None:
            return UpgradeRunResult(False, (), None, "No panel upgrader configured")
        builders: int | None = None
        if self._resource_reader is not None:
            try:
                snapshot = self._resource_reader.read()  # type: ignore[attr-defined]
            except Exception:
                snapshot = None
            builders = getattr(snapshot, "builders_available", None)
        if builders is None:
            return UpgradeRunResult(False, (), None, "Could not read the builder count")
        runner = UpgradeRunner(self._scanner)
        return runner.run(self._store.get().upgrades, builders, execute=execute)

    @staticmethod
    def set_wall(
        upgrades: UpgradeConfig,
        enabled: bool,
        level: int,
        gold_threshold: int,
        elixir_threshold: int,
    ) -> UpgradeConfig:
        """Return an upgrade config with wall settings replaced."""
        wall = WallUpgradeConfig(
            enabled=bool(enabled),
            level=max(1, int(level)),
            gold_threshold=max(0, int(gold_threshold)),
            elixir_threshold=max(0, int(elixir_threshold)),
        )
        return replace(upgrades, wall=wall)

    @staticmethod
    def set_priority_flag(
        upgrades: UpgradeConfig,
        category: UpgradeCategory,
        priority: bool,
    ) -> UpgradeConfig:
        """Flip the priority flag of one group without touching its list."""
        field_name = {
            UpgradeCategory.BUILDINGS: "buildings",
            UpgradeCategory.ARMY: "army",
            UpgradeCategory.EQUIPMENT: "equipment",
            UpgradeCategory.PETS: "pets",
            UpgradeCategory.HERO: "hero",
            UpgradeCategory.RESOURCE: "resource",
            UpgradeCategory.DEFENSE: "defense",
            UpgradeCategory.OTHER: "other",
        }.get(category)
        if field_name is None:
            return upgrades
        group = getattr(upgrades, field_name)
        return replace(
            upgrades,
            **{field_name: replace(group, priority=bool(priority))},
        )

    @staticmethod
    def set_priority(
        upgrades: UpgradeConfig,
        category: UpgradeCategory,
        enabled: bool,
        priorities: list[str],
        priority: bool | None = None,
    ) -> UpgradeConfig:
        """Return an upgrade config with one priority group replaced."""
        field_name = {
            UpgradeCategory.BUILDINGS: "buildings",
            UpgradeCategory.ARMY: "army",
            UpgradeCategory.EQUIPMENT: "equipment",
            UpgradeCategory.PETS: "pets",
            UpgradeCategory.HERO: "hero",
            UpgradeCategory.DEFENSE: "defense",
            UpgradeCategory.RESOURCE: "resource",
            UpgradeCategory.OTHER: "other",
        }.get(category)
        if field_name is None:
            return upgrades
        existing = getattr(upgrades, field_name)
        group = PriorityUpgradeConfig(
            enabled=bool(enabled),
            priorities=[item.strip() for item in priorities if item.strip()],
            priority=existing.priority if priority is None else bool(priority),
        )
        return replace(upgrades, **{field_name: group})


COLLECTOR_TEMPLATES = (
    "elixir_collector.png",
    "DE_collector.png",
    "gold_collector.png",
)


@dataclass(frozen=True)
class VillageActionResult:
    """Outcome of one village routine pass."""

    ok: bool
    found: int = 0
    tapped: int = 0
    message: str = ""
    full_storages: Mapping[str, int] = None  # type: ignore[assignment]
    resources: ResourceSnapshot = ResourceSnapshot()
    wall_points: int = 0

    def __post_init__(self) -> None:
        """Normalize the optional storage mapping."""
        if self.full_storages is None:
            object.__setattr__(self, "full_storages", {})


class VillageActions:
    """Clean-port home routine: resources, collectors, storages, walls."""

    FULL_STORAGE_TEMPLATES = {
        "gold": "gold_collector_full.png",
        "elixir": "elixir_collector_full.png",
        "de": "DE_collector_full.png",
    }
    WALL_TEMPLATES = ("wall.png", "wall_2.png", "wall_3.png", "wall_4.png")
    CLOSE_TEMPLATES = (
        "btn_close.png",
        "continue.png",
        "close_button_layout.png",
        "close_button_profile.png",
        "close_button_setting.png",
        "close_button_shield.png",
        "close_button_shop.png",
    )

    def __init__(
        self,
        adb: AdbPort,
        capture: CapturePort,
        matcher: TemplateMatcher,
        ocr: OcrPort | None = None,
        clock: ClockPort | None = None,
        logger: LoggerPort | None = None,
        multitouch: MultiTouchPort | None = None,
        wall_upgrader: WallUpgrader | None = None,
        upgrader: HeroDefenseUpgrader | None = None,
        read_resources: bool = False,
        execute: bool = False,
    ) -> None:
        """Create the routine; input is dry-run unless *execute* is explicit."""
        from COCbot.core.clock import SystemClock

        self._adb = adb
        self._capture = capture
        self._matcher = matcher
        self._ocr = ocr
        self._clock = clock or SystemClock()
        self._logger = logger
        self._multitouch = multitouch
        self._wall_upgrader = wall_upgrader
        self._upgrader = upgrader
        self._read_resources_flag = read_resources
        self._execute = execute

    def _log(self, level: str, message: str) -> None:
        """Emit a log line when a logger was supplied."""
        if self._logger is not None:
            getattr(self._logger, level)(message)

    @staticmethod
    def _check_cancel(cancel_event: Event | None) -> None:
        """Raise when the bot has been stopped."""
        from COCbot.core.errors import OperationCancelled

        if cancel_event is not None and cancel_event.is_set():
            raise OperationCancelled("Village routine cancelled")

    def _return_home(self) -> None:
        """Tap the home button and allow the camera to settle."""
        if not self._execute:
            self._log("info", "Dry run: would return home")
            return
        self._adb.tap(424, 625)
        self._clock.sleep(3.0)

    def _collect_from(self, frame) -> tuple[int, int]:
        """Return ``(found, tapped)`` collectors from *frame*."""
        found = 0
        tapped = 0
        for name in COLLECTOR_TEMPLATES:
            matches = self._matcher.match_all(
                frame,
                name,
                threshold=0.65,
                limit=3,
            )
            for match in matches:
                found += 1
                if self._execute:
                    center = match.center()
                    if self._adb.tap(center.x, center.y):
                        tapped += 1
        return (found, tapped)

    def collect_resources(self) -> tuple[int, int]:
        """Return ``(found, tapped)`` collectors from one frame."""
        frame = self._capture.capture()
        if frame is None:
            return (0, 0)
        return self._collect_from(frame)

    def _storages_from(self, frame) -> dict[str, int]:
        """Return full-storage icon counts for *frame*."""
        counts: dict[str, int] = {}
        for resource, name in self.FULL_STORAGE_TEMPLATES.items():
            matches = self._matcher.match_all(
                frame,
                name,
                threshold=0.85,
                limit=40,
            )
            counts[resource] = len(matches)
        return counts

    def detect_full_storages(self) -> dict[str, int]:
        """Return full-storage icon counts per resource."""
        frame = self._capture.capture()
        if frame is None:
            return {name: 0 for name in self.FULL_STORAGE_TEMPLATES}
        return self._storages_from(frame)

    def _resources_from(self, frame) -> ResourceSnapshot:
        """Read the home-village counters from *frame*."""
        if self._ocr is None:
            return ResourceSnapshot()
        gold = self._ocr.read_number(frame, HR_GOLD_REGION) or 0
        elixir = self._ocr.read_number(frame, HR_ELIXIR_REGION) or 0
        dark = self._ocr.read_number(frame, HR_DARK_REGION) or 0
        return ResourceSnapshot(gold=gold, elixir=elixir, dark_elixir=dark)

    def read_home_resources(self) -> ResourceSnapshot:
        """Read the home-village gold/elixir/dark counters."""
        frame = self._capture.capture()
        if frame is None:
            return ResourceSnapshot()
        return self._resources_from(frame)

    def close_panels(self) -> int:
        """Find and (optionally) dismiss common popups."""
        frame = self._capture.capture()
        if frame is None:
            return 0
        closed = 0
        for name in self.CLOSE_TEMPLATES:
            match = self._matcher.match(frame, name, threshold=0.75)
            if match is None:
                continue
            closed += 1
            if self._execute:
                center = match.center()
                if self._adb.tap(center.x, center.y):
                    self._clock.sleep(0.4)
        return closed

    def zoom_out(self, count: int = 3) -> bool:
        """Pinch out to see more of the village (real input only)."""
        if not self._execute or self._multitouch is None:
            self._log("info", "Dry run: would zoom out")
            return False
        any_ok = False
        for index in range(max(1, int(count))):
            if self._multitouch.pinch_in(percent=100, steps=20):
                any_ok = True
            if index < count - 1:
                self._clock.sleep(0.5)
        return any_ok

    def scan_walls(self, zoom_first: bool = False) -> tuple[Point, ...]:
        """Return deduplicated wall coordinates on the zoomed-out home village."""
        if zoom_first:
            self.zoom_out(3)
        frame = self._capture.capture()
        if frame is None:
            return ()
        points: list[Point] = []
        for name in self.WALL_TEMPLATES:
            matches = self._matcher.match_all(
                frame,
                name,
                region=HR_WALL_ROI,
                threshold=0.90,
                limit=40,
            )
            for match in matches:
                center = match.center()
                if all(center.distance_to(existing) > 10 for existing in points):
                    points.append(center)
        return tuple(points)

    def upgrade_wall(
        self,
        level: int,
        resource: str,
        wall: Point | None = None,
    ) -> WallUpgradePlan:
        """Scan and upgrade one wall through the guarded wall upgrader."""
        if self._wall_upgrader is None:
            return WallUpgradePlan(
                resource,
                wall or Point(0, 0),
                message="No wall upgrader configured",
            )
        frame = self._capture.capture()
        if frame is None:
            return WallUpgradePlan(resource, wall or Point(0, 0), message="Capture failed")
        scan = self._wall_upgrader.scan(frame, level)
        target = wall or (scan.points[0] if scan.points else None)
        if target is None:
            return WallUpgradePlan(
                resource,
                Point(0, 0),
                message=f"No walls matched level {level} (best={scan.best_score:.2f})",
            )
        return self._wall_upgrader.execute(target, resource, level)

    def scan_upgrade_rows(self) -> tuple[UpgradeRow, ...]:
        """Return the hero/defense rows of the Buildings & Heroes panel."""
        if self._upgrader is None:
            return ()
        frame = self._capture.capture()
        if frame is None:
            return ()
        return tuple(self._upgrader.rows(frame))

    def upgrade_target(
        self,
        name: str,
        execute: bool | None = None,
    ) -> UpgradeResult:
        """Run one guarded hero/defense upgrade from the upgrade panel."""
        if self._upgrader is None:
            return UpgradeResult(False, name, message="No upgrade helper configured")
        return self._upgrader.execute(name, execute=execute)

    def open_upgrade_panel(self, execute: bool | None = None) -> bool:
        """Open the Buildings & Heroes panel (dry-run aware)."""
        if self._upgrader is None:
            return False
        return self._upgrader.open_panel(
            execute=self._execute if execute is None else bool(execute)
        )

    def run(self, cancel_event: Event | None = None) -> VillageActionResult:
        """Return home, collect, and inspect storages/resources."""
        self._check_cancel(cancel_event)
        self._return_home()
        self._check_cancel(cancel_event)
        frame = self._capture.capture()
        if frame is None:
            return VillageActionResult(ok=False, message="Capture failed")
        found, tapped = self._collect_from(frame)
        storages = self._storages_from(frame)
        resources = (
            self._resources_from(frame)
            if self._read_resources_flag
            else ResourceSnapshot()
        )
        if found == 0:
            return VillageActionResult(
                ok=False,
                message="No collector templates found",
                full_storages=storages,
                resources=resources,
            )
        mode = "tapped" if self._execute else "found (dry run)"
        return VillageActionResult(
            ok=True,
            found=found,
            tapped=tapped,
            message=f"{found} collectors {mode}; storages={storages}",
            full_storages=storages,
            resources=resources,
        )


class VillageStep:
    """CycleStep adapter for the village routine."""

    def __init__(self, actions: VillageActions) -> None:
        """Wrap village actions as an orchestrator step."""
        self._actions = actions

    @property
    def name(self) -> str:
        """Return the stable step name."""
        return "village"

    def run(self, context: CycleContext) -> StepResult:
        """Run one village routine pass."""
        result = self._actions.run(context.session.stop_event)
        return StepResult(
            result.ok,
            result.message,
            phase=BotPhase.RUNNING,
            data={
                "found": result.found,
                "tapped": result.tapped,
                "full_storages": dict(result.full_storages),
                "resources": result.resources.as_dict(),
            },
        )
