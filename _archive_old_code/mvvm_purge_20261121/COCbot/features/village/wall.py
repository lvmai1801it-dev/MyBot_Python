"""Wall scanning and guarded wall-upgrade execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from COCbot.core.config.coordinates import (
    HR_CLOSE_TAP,
    HR_CONFIRM_UPGRADE,
    HR_DISMISS_TAP,
    HR_ELIXIR_UPGRADE,
    HR_GOLD_UPGRADE,
    HR_HOME_TAP,
    HR_VALIDATION_ROI,
    HR_WALL_ROI,
)
from COCbot.core.config.paths import get_project_paths
from COCbot.core.ports import AdbPort, CapturePort, ClockPort, LoggerPort
from COCbot.core.vision.image import crop, frame_image
from COCbot.models.frame import Frame
from COCbot.models.geometry import Point


@dataclass(frozen=True)
class WallScanResult:
    """Wall coordinates and calibration metadata."""

    points: tuple[Point, ...] = ()
    templates: int = 0
    best_score: float = 0.0


@dataclass(frozen=True)
class WallUpgradePlan:
    """Planned (or executed) wall upgrade actions."""

    resource: str
    wall: Point
    upgrade: Point | None = None
    validation: float = 0.0
    executed: bool = False
    message: str = ""


class WallUpgrader:
    """Scan wall templates and optionally execute one upgrade."""

    def __init__(
        self,
        adb: AdbPort,
        capture: CapturePort,
        clock: ClockPort | None = None,
        logger: LoggerPort | None = None,
        execute: bool = False,
        threshold: float = 0.65,
        validation_threshold: float = 0.88,
        walls_dir: Path | str | None = None,
    ) -> None:
        """Create the upgrader; input is disabled unless *execute* is true."""
        from COCbot.core.clock import SystemClock

        self._adb = adb
        self._capture = capture
        self._clock = clock or SystemClock()
        self._logger = logger
        self._execute = execute
        self._threshold = threshold
        self._validation_threshold = validation_threshold
        self._walls_dir = Path(walls_dir) if walls_dir is not None else None

    def _log(self, level: str, message: str) -> None:
        """Emit a log line when a logger was supplied."""
        if self._logger is not None:
            getattr(self._logger, level)(message)

    def _templates_dir(self, level: int) -> Path:
        """Return ``walls/<level>``."""
        base = self._walls_dir or (get_project_paths().src_dir / "walls")
        return base / str(int(level))

    def load_templates(self, level: int) -> list[np.ndarray]:
        """Load top-level wall templates for *level*."""
        directory = self._templates_dir(level)
        templates: list[np.ndarray] = []
        if not directory.is_dir():
            return templates
        for path in sorted(directory.glob("*.png")):
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if image is not None:
                templates.append(image)
        return templates

    def scan(self, frame: Frame, level: int, threshold: float | None = None) -> WallScanResult:
        """Return deduplicated wall coordinates for *level*."""
        image = frame_image(frame)
        if image is None:
            return WallScanResult()
        roi = crop(image, HR_WALL_ROI)
        if roi.size == 0:
            return WallScanResult()
        minimum = self._threshold if threshold is None else float(threshold)
        templates = self.load_templates(level)
        points: list[Point] = []
        best = 0.0
        for template in templates:
            if (
                template.shape[0] > roi.shape[0]
                or template.shape[1] > roi.shape[1]
            ):
                continue
            result = cv2.matchTemplate(roi, template, cv2.TM_CCOEFF_NORMED)
            height, width = template.shape[:2]
            ys, xs = np.where(result >= minimum)
            for x, y in zip(xs, ys):
                score = float(result[y, x])
                best = max(best, score)
                point = Point(
                    HR_WALL_ROI.x + int(x) + width // 2,
                    HR_WALL_ROI.y + int(y) + height // 2,
                )
                if all(point.distance_to(existing) > 12 for existing in points):
                    points.append(point)
        points.sort(key=lambda item: (item.y, item.x))
        self._log(
            "info",
            f"Wall scan level={level}: {len(points)} points, best={best:.2f}",
        )
        return WallScanResult(tuple(points), len(templates), best)

    def _validation_template(self, level: int) -> np.ndarray | None:
        """Load the level validation template."""
        path = self._templates_dir(level) / "Validate_Upgrade" / "verify_wall_level.png"
        if not path.is_file():
            return None
        return cv2.imread(str(path), cv2.IMREAD_COLOR)

    def plan(self, wall: Point, resource: str, level: int) -> WallUpgradePlan:
        """Return a dry-run plan for one wall upgrade."""
        upgrade = HR_GOLD_UPGRADE if resource == "gold" else HR_ELIXIR_UPGRADE
        return WallUpgradePlan(
            resource=resource,
            wall=wall,
            upgrade=upgrade,
            message="Dry run: wall upgrade plan ready",
        )

    def execute(self, wall: Point, resource: str, level: int) -> WallUpgradePlan:
        """Execute one wall upgrade with validation; no-op in dry-run."""
        if not self._execute:
            return self.plan(wall, resource, level)

        self._adb.tap(wall.x, wall.y)
        self._clock.sleep(1.0)
        self._adb.tap(HR_HOME_TAP.x, HR_HOME_TAP.y)
        self._clock.sleep(1.0)

        frame = self._capture.capture()
        template = self._validation_template(level)
        image = frame_image(frame) if frame is not None else None
        if image is None or template is None:
            self._adb.tap(HR_DISMISS_TAP.x, HR_DISMISS_TAP.y)
            return WallUpgradePlan(resource, wall, message="Validation capture failed")

        roi = crop(image, HR_VALIDATION_ROI)
        if (
            template.shape[0] > roi.shape[0]
            or template.shape[1] > roi.shape[1]
        ):
            return WallUpgradePlan(resource, wall, message="Validation ROI too small")
        result = cv2.matchTemplate(roi, template, cv2.TM_CCOEFF_NORMED)
        _, score, _, location = cv2.minMaxLoc(result)
        if score < self._validation_threshold:
            self._adb.tap(HR_DISMISS_TAP.x, HR_DISMISS_TAP.y)
            return WallUpgradePlan(
                resource,
                wall,
                validation=float(score),
                message=f"Wall validation failed ({score:.2f})",
            )

        center_x = HR_VALIDATION_ROI.x + location[0] + template.shape[1] // 2
        offset = 175 if resource == "gold" else 350
        base = HR_GOLD_UPGRADE if resource == "gold" else HR_ELIXIR_UPGRADE
        upgrade = Point(center_x + offset, base.y)
        self._adb.tap(upgrade.x, upgrade.y)
        self._clock.sleep(1.0)
        self._adb.tap(HR_CONFIRM_UPGRADE.x, HR_CONFIRM_UPGRADE.y)
        self._clock.sleep(0.5)
        self._adb.tap(HR_CLOSE_TAP.x, HR_CLOSE_TAP.y)
        return WallUpgradePlan(
            resource,
            wall,
            upgrade=upgrade,
            validation=float(score),
            executed=True,
            message=f"Wall upgraded with {resource}",
        )
