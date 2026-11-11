"""Village / upgrade feature domain model (pure Python, no Qt)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from threading import Event

from COCbot.app.orchestrator import CycleContext, StepResult
from COCbot.core.config.schema import (
    AppConfig,
    PriorityUpgradeConfig,
    UpgradeConfig,
    WallUpgradeConfig,
)
from COCbot.core.config.store import ConfigStore
from COCbot.core.ports import AdbPort, CapturePort, ClockPort, LoggerPort, SettingsPort
from COCbot.core.vision.templates import TemplateMatcher
from COCbot.models.enums import BotPhase, UpgradeCategory


@dataclass(frozen=True)
class VillageSnapshot:
    """The upgrade configuration shown in the Village tab."""

    upgrades: UpgradeConfig


class VillageModel:
    """Load and persist the upgrade groups."""

    def __init__(self, store: ConfigStore, settings: SettingsPort) -> None:
        """Share the live config and the settings persistence port."""
        self._store = store
        self._settings = settings

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
    def set_priority(
        upgrades: UpgradeConfig,
        category: UpgradeCategory,
        enabled: bool,
        priorities: list[str],
    ) -> UpgradeConfig:
        """Return an upgrade config with one priority group replaced."""
        field_name = {
            UpgradeCategory.HERO: "hero",
            UpgradeCategory.DEFENSE: "defense",
            UpgradeCategory.ARMY: "army",
            UpgradeCategory.RESOURCE: "resource",
            UpgradeCategory.OTHER: "other",
        }.get(category)
        if field_name is None:
            return upgrades
        group = PriorityUpgradeConfig(
            enabled=bool(enabled),
            priorities=[item.strip() for item in priorities if item.strip()],
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


class VillageActions:
    """Clean-port home routine: return home and collect resources."""

    def __init__(
        self,
        adb: AdbPort,
        capture: CapturePort,
        matcher: TemplateMatcher,
        clock: ClockPort | None = None,
        logger: LoggerPort | None = None,
        execute: bool = False,
    ) -> None:
        """Create the routine; input is dry-run unless *execute* is explicit."""
        from COCbot.core.clock import SystemClock

        self._adb = adb
        self._capture = capture
        self._matcher = matcher
        self._clock = clock or SystemClock()
        self._logger = logger
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

    def collect_resources(self) -> tuple[int, int]:
        """Return ``(found, tapped)`` collectors from one frame."""
        frame = self._capture.capture()
        if frame is None:
            return (0, 0)
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

    def run(self, cancel_event: Event | None = None) -> VillageActionResult:
        """Return home and collect available resources."""
        self._check_cancel(cancel_event)
        self._return_home()
        self._check_cancel(cancel_event)
        found, tapped = self.collect_resources()
        if found == 0:
            return VillageActionResult(
                ok=False,
                message="No collector templates found",
            )
        mode = "tapped" if self._execute else "found (dry run)"
        return VillageActionResult(
            ok=True,
            found=found,
            tapped=tapped,
            message=f"{found} collectors {mode}",
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
            data={"found": result.found, "tapped": result.tapped},
        )
