"""Training feature: quick-train through the saved recipe window."""

from __future__ import annotations

from dataclasses import dataclass

from COCbot.app.orchestrator import CycleContext, StepResult
from COCbot.core.config.coordinates import (
    ARMY_CLOSE_BUTTON,
    ARMY_CONFIRM_BUTTON,
    ARMY_EDIT_BUTTON,
    ARMY_EDIT_ROI,
    ARMY_RECIPE_PANE,
    ARMY_USE_BUTTONS,
    NAV,
)
from COCbot.core.ports import AdbPort, CapturePort, ClockPort, LoggerPort
from COCbot.core.vision.templates import TemplateMatcher
from COCbot.models.enums import BotPhase
from COCbot.models.frame import Frame


@dataclass(frozen=True)
class TrainingResult:
    """Outcome of one quick-train attempt."""

    ok: bool
    slot: int = 1
    taps: int = 0
    message: str = ""


class TrainingActions:
    """Open the army window and apply a saved recipe."""

    def __init__(
        self,
        adb: AdbPort,
        capture: CapturePort,
        matcher: TemplateMatcher,
        clock: ClockPort | None = None,
        logger: LoggerPort | None = None,
        execute: bool = False,
    ) -> None:
        """Create the training actions; dry-run by default."""
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

    def _tap(self, x: int, y: int) -> bool:
        """Tap only when real input is enabled."""
        if not self._execute:
            return False
        self._adb.tap(x, y)
        return True

    def _find_edit_button(self, frame: Frame):
        """Return the battle-menu Edit Army match, if visible."""
        return self._matcher.match(
            frame,
            "Smart_Auto_train/edit_army_btn.png",
            region=ARMY_EDIT_ROI,
            threshold=0.70,
        )

    def quick_train(self, slot: int = 1) -> TrainingResult:
        """Apply saved recipe *slot* to the army."""
        if not self._execute:
            self._log("info", f"Dry run: would quick-train recipe {slot}")
            return TrainingResult(True, slot, 0, f"Dry run: recipe {slot}")

        taps = 0
        self._adb.tap(NAV.battle_button.x, NAV.battle_button.y)
        taps += 1
        self._clock.sleep(2.0)

        frame = self._capture.capture()
        edit = self._find_edit_button(frame) if frame is not None else None
        if edit is not None:
            self._adb.tap(edit.center().x, edit.center().y)
        else:
            self._adb.tap(ARMY_EDIT_BUTTON.x, ARMY_EDIT_BUTTON.y)
        taps += 1
        self._clock.sleep(1.2)

        self._adb.tap(ARMY_RECIPE_PANE.x, ARMY_RECIPE_PANE.y)
        taps += 1
        self._clock.sleep(1.0)

        use = ARMY_USE_BUTTONS.get(slot, ARMY_USE_BUTTONS[1])
        self._adb.tap(use.x, use.y)
        taps += 1
        self._clock.sleep(1.0)

        self._adb.tap(ARMY_CONFIRM_BUTTON.x, ARMY_CONFIRM_BUTTON.y)
        taps += 1
        self._clock.sleep(0.8)

        self._adb.tap(ARMY_CLOSE_BUTTON.x, ARMY_CLOSE_BUTTON.y)
        taps += 1
        self._clock.sleep(0.5)
        keyevent = getattr(self._adb, "keyevent", None)
        if keyevent is not None:
            keyevent("KEYCODE_BACK")
            self._clock.sleep(0.5)
        self._log("info", f"Quick-train recipe {slot} applied")
        return TrainingResult(True, slot, taps, f"Quick-train recipe {slot} applied")


class TrainingStep:
    """CycleStep adapter for quick training."""

    def __init__(self, actions: TrainingActions, slot: int = 1) -> None:
        """Wrap training actions as an orchestrator step."""
        self._actions = actions
        self._slot = slot

    @property
    def name(self) -> str:
        """Return the stable step name."""
        return "training"

    def run(self, context: CycleContext) -> StepResult:
        """Run one quick-train attempt."""
        result = self._actions.quick_train(self._slot)
        return StepResult(
            result.ok,
            result.message,
            phase=BotPhase.RUNNING,
            data={"slot": result.slot, "taps": result.taps},
        )
