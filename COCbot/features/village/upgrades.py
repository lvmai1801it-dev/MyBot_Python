"""Hero/defense upgrade flow with template-driven validation.

The legacy project never implemented this flow, so it is intentionally
template-driven: provide target portraits and upgrade/confirm buttons under
``Templates/Upgrades`` and the flow will not guess blindly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import cv2
import numpy as np

from COCbot.core.config.paths import get_project_paths
from COCbot.core.ports import AdbPort, CapturePort, ClockPort, LoggerPort
from COCbot.core.vision.image import frame_image, imread
from COCbot.models.frame import Frame
from COCbot.models.geometry import Point


@dataclass(frozen=True)
class UpgradeTarget:
    """One hero or defense candidate."""

    name: str
    kind: str
    template: str


DEFAULT_TARGETS: tuple[UpgradeTarget, ...] = (
    UpgradeTarget("King", "hero", "hero_king.png"),
    UpgradeTarget("Queen", "hero", "hero_queen.png"),
    UpgradeTarget("Warden", "hero", "hero_warden.png"),
    UpgradeTarget("Champion", "hero", "hero_champion.png"),
    UpgradeTarget("Prince", "hero", "hero_prince.png"),
)

DEFAULT_BUTTONS: Mapping[str, str] = {
    "upgrade": "upgrade_button.png",
    "confirm": "confirm_button.png",
    "close": "close_button.png",
}


@dataclass(frozen=True)
class UpgradeResult:
    """Outcome of a hero/defense upgrade attempt."""

    ok: bool
    target: str = ""
    executed: bool = False
    message: str = ""
    taps: int = 0


class HeroDefenseUpgrader:
    """Find a target portrait and execute a template-validated upgrade."""

    def __init__(
        self,
        adb: AdbPort,
        capture: CapturePort,
        clock: ClockPort | None = None,
        logger: LoggerPort | None = None,
        template_dir: Path | str | None = None,
        targets: Sequence[UpgradeTarget] = DEFAULT_TARGETS,
        buttons: Mapping[str, str] = DEFAULT_BUTTONS,
        threshold: float = 0.75,
        execute: bool = False,
    ) -> None:
        """Create the upgrader; missing templates simply disable targets."""
        from COCbot.core.clock import SystemClock

        self._adb = adb
        self._capture = capture
        self._clock = clock or SystemClock()
        self._logger = logger
        self._dir = (
            Path(template_dir)
            if template_dir is not None
            else get_project_paths().templates_dir / "Upgrades"
        )
        self._targets = tuple(targets)
        self._buttons = dict(buttons)
        self._threshold = threshold
        self._execute = execute

    def _log(self, level: str, message: str) -> None:
        """Emit a log line when a logger was supplied."""
        if self._logger is not None:
            getattr(self._logger, level)(message)

    def _load(self, filename: str) -> np.ndarray | None:
        """Load one template from the upgrade template directory."""
        path = self._dir / filename
        return imread(path) if path.is_file() else None

    def available_targets(self) -> list[str]:
        """Return targets whose portrait template exists."""
        return [target.name for target in self._targets if (self._dir / target.template).is_file()]

    @staticmethod
    def _match(image: np.ndarray, template: np.ndarray, threshold: float) -> Point | None:
        """Return the best match center above *threshold*."""
        if (
            template.shape[0] > image.shape[0]
            or template.shape[1] > image.shape[1]
        ):
            return None
        result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        _, score, _, location = cv2.minMaxLoc(result)
        if not np.isfinite(score) or score < threshold:
            return None
        return Point(
            location[0] + template.shape[1] // 2,
            location[1] + template.shape[0] // 2,
        )

    def find(self, frame: Frame, template_name: str) -> Point | None:
        """Find a template in *frame*."""
        image = frame_image(frame)
        template = self._load(template_name)
        if image is None or template is None:
            return None
        return self._match(image, template, self._threshold)

    def _find_target(self, frame: Frame) -> tuple[UpgradeTarget, Point] | None:
        """Return the first available target found in *frame*."""
        image = frame_image(frame)
        if image is None:
            return None
        for target in self._targets:
            template = self._load(target.template)
            if template is None:
                continue
            point = self._match(image, template, self._threshold)
            if point is not None:
                return target, point
        return None

    def execute(self, target_name: str | None = None, execute: bool | None = None) -> UpgradeResult:
        """Run one upgrade flow; dry-run returns the plan only."""
        should_tap = self._execute if execute is None else bool(execute)
        frame = self._capture.capture()
        if frame is None:
            return UpgradeResult(False, message="Capture failed")
        found = self._find_target(frame)
        if found is None:
            return UpgradeResult(
                False,
                target_name or "",
                message="No configured hero/defense template found",
            )
        target, point = found
        if target_name and target.name.lower() != target_name.lower():
            return UpgradeResult(
                False,
                target_name,
                message=f"Found {target.name}, not {target_name}",
            )
        if not should_tap:
            return UpgradeResult(
                True,
                target.name,
                executed=False,
                message=f"Dry run: would upgrade {target.name} at ({point.x},{point.y})",
            )

        taps = 0
        self._adb.tap(point.x, point.y)
        taps += 1
        self._clock.sleep(1.0)

        frame = self._capture.capture()
        upgrade = self.find(frame, self._buttons["upgrade"]) if frame is not None else None
        if upgrade is None:
            return UpgradeResult(
                False,
                target.name,
                executed=False,
                taps=taps,
                message="Upgrade button template not found",
            )
        self._adb.tap(upgrade.x, upgrade.y)
        taps += 1
        self._clock.sleep(1.0)

        frame = self._capture.capture()
        confirm = self.find(frame, self._buttons["confirm"]) if frame is not None else None
        if confirm is None:
            return UpgradeResult(
                False,
                target.name,
                executed=False,
                taps=taps,
                message="Confirm button template not found",
            )
        self._adb.tap(confirm.x, confirm.y)
        taps += 1
        self._clock.sleep(0.5)

        frame = self._capture.capture()
        close = self.find(frame, self._buttons["close"]) if frame is not None else None
        if close is not None:
            self._adb.tap(close.x, close.y)
            taps += 1
        return UpgradeResult(
            True,
            target.name,
            executed=True,
            taps=taps,
            message=f"Upgraded {target.name}",
        )
