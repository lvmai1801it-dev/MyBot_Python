"""Clean-port battle search, end detection, stars, and loot reading."""

from __future__ import annotations

from threading import Event

from COCbot.app.orchestrator import CycleContext, StepResult
from COCbot.core.clock import SystemClock
from COCbot.core.config.coordinates import (
    BATTLE_REGION,
    GAIN_DARK_LEFT,
    GAIN_DARK_RIGHT,
    GAIN_ELIXIR_LEFT,
    GAIN_ELIXIR_RIGHT,
    GAIN_GOLD_LEFT,
    GAIN_GOLD_RIGHT,
    NAV,
    NEXT_BUTTON_REGION,
    SCOUT_SCREEN_REGION,
    STAR_REGIONS,
)
from COCbot.core.errors import OperationCancelled
from COCbot.core.ports import AdbPort, CapturePort, ClockPort, LoggerPort, OcrPort
from COCbot.core.vision.templates import TemplateMatcher
from COCbot.features.attack.army_bar import ArmyBarScanner
from COCbot.features.attack.executor import AttackExecutionResult, AttackExecutor
from COCbot.features.attack.model import AttackModel, AttackScan
from COCbot.models.attack import AttackResult, Detection, RedlineResult
from COCbot.models.enums import BotPhase
from COCbot.models.frame import Frame
from COCbot.models.geometry import Point
from COCbot.models.resources import ResourceSnapshot


class BattleService:
    """Search, scout, wait for battle end, and read the result screen."""

    def __init__(
        self,
        adb: AdbPort,
        capture: CapturePort,
        matcher: TemplateMatcher,
        ocr: OcrPort | None = None,
        clock: ClockPort | None = None,
        logger: LoggerPort | None = None,
        execute: bool = False,
        max_battle_wait: float = 180.0,
        scout_timeout: float = 20.0,
    ) -> None:
        """Create the service; taps are gated by *execute*."""
        self._adb = adb
        self._capture = capture
        self._matcher = matcher
        self._ocr = ocr
        self._clock = clock or SystemClock()
        self._logger = logger
        self._execute = execute
        self._max_battle_wait = max_battle_wait
        self._scout_timeout = scout_timeout

    def _log(self, level: str, message: str) -> None:
        """Emit a log line when a logger was supplied."""
        if self._logger is not None:
            getattr(self._logger, level)(message)

    def _tap(self, point: Point) -> bool:
        """Tap only when real input is enabled."""
        if not self._execute:
            self._log("info", f"Dry run: would tap ({point.x},{point.y})")
            return False
        self._adb.tap(point.x, point.y)
        return True

    def return_home(self) -> None:
        """Return to the home village."""
        self._tap(NAV.return_home)
        if self._execute:
            self._clock.sleep(3.0)

    def search_attack(self) -> None:
        """Open the attack menu and start matchmaking."""
        self._tap(NAV.battle_button)
        self._clock.sleep(1.0)
        self._tap(NAV.find_match)
        self._clock.sleep(1.0)
        self._tap(NAV.attack_confirm)
        self._clock.sleep(1.0)

    def find_next_button(self) -> Detection | None:
        """Return the scout-screen Next button when visible."""
        frame = self._capture.capture()
        if frame is None:
            return None
        return self._matcher.match(
            frame,
            "next_button.png",
            region=NEXT_BUTTON_REGION,
            threshold=0.35,
        )

    def search_next(self) -> bool:
        """Tap Next on the scout screen."""
        button = self.find_next_button()
        if button is None:
            return False
        self._tap(button.center())
        if self._execute:
            self._clock.sleep(1.5)
        return True

    def wait_for_scout(self, cancel_event: Event | None = None) -> bool:
        """Wait for the scouting UI to appear."""
        deadline = self._clock.monotonic() + self._scout_timeout
        while self._clock.monotonic() < deadline:
            if cancel_event is not None and cancel_event.is_set():
                raise OperationCancelled("Scout wait cancelled")
            frame = self._capture.capture()
            if frame is not None and self._matcher.match(
                frame,
                "end_battle.png",
                region=SCOUT_SCREEN_REGION,
                threshold=0.70,
            ):
                return True
            self._clock.sleep(1.5)
        return False

    def wait_for_battle_end(self, cancel_event: Event | None = None) -> bool:
        """Wait for the battle-end panel."""
        deadline = self._clock.monotonic() + self._max_battle_wait
        while self._clock.monotonic() < deadline:
            if cancel_event is not None and cancel_event.is_set():
                raise OperationCancelled("Battle wait cancelled")
            frame = self._capture.capture()
            if frame is not None and self._matcher.match(
                frame,
                "end_battle.png",
                region=BATTLE_REGION,
                threshold=0.65,
            ):
                return True
            self._clock.sleep(1.0)
        return False

    def read_stars(self) -> int:
        """Read the star count from the battle-result screen."""
        frame = self._capture.capture()
        if frame is None:
            return 0

        def matched(name: str, index: int) -> bool:
            return (
                self._matcher.match(
                    frame,
                    name,
                    region=STAR_REGIONS[index],
                    threshold=0.40,
                )
                is not None
            )

        if not matched("one_star.png", 0):
            return 0
        if not matched("two_star.png", 1):
            return 1
        if matched("three_star.png", 2):
            return 3
        return 2

    def read_loot(self, stars: int) -> ResourceSnapshot:
        """Read the loot gained from the result screen."""
        frame = self._capture.capture()
        if frame is None or self._ocr is None:
            return ResourceSnapshot()

        def amount(region) -> int:
            value = self._ocr.read_number(frame, region)
            return int(value or 0)

        gold = amount(GAIN_GOLD_LEFT)
        elixir = amount(GAIN_ELIXIR_LEFT)
        dark = amount(GAIN_DARK_LEFT)
        if stars > 0:
            gold += amount(GAIN_GOLD_RIGHT)
            elixir += amount(GAIN_ELIXIR_RIGHT)
            dark += amount(GAIN_DARK_RIGHT)
        return ResourceSnapshot(gold=gold, elixir=elixir, dark_elixir=dark)

    def read_result(self) -> AttackResult:
        """Read stars and loot into an :class:`AttackResult`."""
        stars = self.read_stars()
        loot = self.read_loot(stars)
        return AttackResult(success=stars > 0, stars=stars, loot=loot)


class FullAttackStep:
    """CycleStep that runs search → scan → deploy → result → home."""

    def __init__(
        self,
        attack: AttackModel,
        battle: BattleService,
        scanner: ArmyBarScanner,
        executor: AttackExecutor,
        execute: bool = False,
    ) -> None:
        """Compose the attack pipeline; input is dry-run by default."""
        self._attack = attack
        self._battle = battle
        self._scanner = scanner
        self._executor = executor
        self._execute = execute

    @property
    def name(self) -> str:
        """Return the stable step name."""
        return "attack"

    def run(self, context: CycleContext) -> StepResult:
        """Execute one full attack or a dry-run scan."""
        cancel = context.session.stop_event
        if self._execute:
            self._battle.return_home()
            self._battle.search_attack()
            if not self._battle.wait_for_scout(cancel):
                return StepResult(False, "Scout screen not detected")

        scan: AttackScan = self._attack.scan(cancel_event=cancel)
        if scan.plan.target is None:
            return StepResult(
                False,
                "No attack target detected",
                phase=BotPhase.SEARCHING,
            )
        slots = self._scanner.scan(scan.frame)
        result: AttackExecutionResult = self._executor.deploy(
            scan.plan,
            scan.redline,
            slots,
            execute=self._execute,
            cancel_event=cancel,
        )
        if not result.ok:
            return StepResult(False, result.message, phase=BotPhase.ATTACKING)

        battle_result = AttackResult(success=True, stars=0)
        if self._execute:
            if not self._battle.wait_for_battle_end(cancel):
                self._battle.return_home()
                return StepResult(False, "Battle end not detected")
            battle_result = self._battle.read_result()
            self._battle.return_home()

        return StepResult(
            True,
            f"{result.message}; stars={battle_result.stars}",
            phase=BotPhase.ATTACKING,
            data={
                "planned": result.planned,
                "taps": result.taps,
                "stars": battle_result.stars,
                "loot": battle_result.loot.as_dict(),
            },
        )
