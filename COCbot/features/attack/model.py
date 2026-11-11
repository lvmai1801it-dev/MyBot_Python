"""Attack feature domain model (pure Python, no Qt)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Event
from typing import Callable, Sequence

from COCbot.app.orchestrator import CycleContext, StepResult
from COCbot.core.config.schema import AppConfig
from COCbot.core.config.store import ConfigStore
from COCbot.core.errors import AttackError, OperationCancelled
from COCbot.core.ports import AdbPort, CapturePort, DetectorPort, LoggerPort
from COCbot.core.vision.redline import RedlineDetector
from COCbot.models.attack import AttackPlan, Detection, RedlineResult
from COCbot.models.enums import AttackSide, BotPhase
from COCbot.models.frame import Frame

ProgressCallback = Callable[[int, int, str], None]

HIGH_VALUE_LABELS = (
    "town_hall",
    "eagle_artillery",
    "clan_castle",
    "inferno_tower",
    "monolith",
    "scattershot",
    "base_area",
)
_EDGE_SIDES = ("TR", "BR", "BL", "TL")


@dataclass(frozen=True)
class AttackScan:
    """Everything produced by one attack scan."""

    frame: Frame
    detections: tuple[Detection, ...]
    redline: RedlineResult
    plan: AttackPlan
    duration: float

    @property
    def source(self) -> str:
        """Return ``yolo``/``cv``/``none`` for the redline detector used."""
        return self.redline.source


class AttackModel:
    """Capture, detect, and build a deploy plan."""

    def __init__(
        self,
        capture: CapturePort,
        detector: DetectorPort,
        redline: RedlineDetector | None = None,
        adb: AdbPort | None = None,
        config: AppConfig | None = None,
        config_store: ConfigStore | None = None,
        logger: LoggerPort | None = None,
        allow_input: bool = False,
    ) -> None:
        """Create the model; input stays disabled unless explicitly allowed."""
        cfg = config or AppConfig()
        self._capture = capture
        self._detector = detector
        self._redline = redline or RedlineDetector(
            model_path=cfg.vision.redline_model,
            confidence=cfg.vision.confidence,
            offset_ratio=cfg.vision.redline_offset_ratio,
            logger=logger,
        )
        self._adb = adb
        self._config = cfg
        self._store = config_store
        self._logger = logger
        self._allow_input = allow_input
        self._last_scan: AttackScan | None = None

    @property
    def last_scan(self) -> AttackScan | None:
        """Return the most recent scan, if any."""
        return self._last_scan

    def _log(self, level: str, message: str) -> None:
        """Emit a log line when a logger was supplied."""
        if self._logger is not None:
            getattr(self._logger, level)(message)

    @staticmethod
    def _check_cancel(cancel_event: Event | None) -> None:
        """Raise when the worker has been cancelled."""
        if cancel_event is not None and cancel_event.is_set():
            raise OperationCancelled("Attack scan cancelled")

    def scan(
        self,
        cancel_event: Event | None = None,
        progress: ProgressCallback | None = None,
    ) -> AttackScan:
        """Capture the screen and return an attack plan."""
        started = time.monotonic()
        if progress is not None:
            progress(0, 4, "Capturing screen")
        self._check_cancel(cancel_event)
        frame = self._capture.capture()
        if frame is None or frame.is_empty():
            raise AttackError("Screen capture failed")

        if progress is not None:
            progress(1, 4, "Detecting targets")
        self._check_cancel(cancel_event)
        detections = tuple(self._detector.detect(frame))

        if progress is not None:
            progress(2, 4, "Detecting redline")
        self._check_cancel(cancel_event)
        redline = self._redline.detect(frame)

        if progress is not None:
            progress(3, 4, "Building deploy plan")
        self._check_cancel(cancel_event)
        plan = self.build_plan(detections, redline)

        if progress is not None:
            progress(4, 4, "Scan complete")
        scan = AttackScan(
            frame=frame,
            detections=detections,
            redline=redline,
            plan=plan,
            duration=time.monotonic() - started,
        )
        self._last_scan = scan
        return scan

    def build_plan(
        self,
        detections: Sequence[Detection],
        redline: RedlineResult,
    ) -> AttackPlan:
        """Choose the highest-value target and troops from the active recipe."""
        if not detections:
            config = self._store.get() if self._store is not None else self._config
            recipe = config.attack.recipe
            return AttackPlan(
                side=AttackSide.RANDOM.value,
                troops=dict(recipe.troops),
                spells=dict(recipe.spells),
                siege=dict(recipe.siege),
            )
        ranked = sorted(
            detections,
            key=lambda item: self._target_score(item),
            reverse=True,
        )
        target = ranked[0]
        side = self._side_for_target(target, redline)
        config = self._store.get() if self._store is not None else self._config
        recipe = config.attack.recipe
        return AttackPlan(
            target=target,
            side=side,
            troops=dict(recipe.troops),
            spells=dict(recipe.spells),
            siege=dict(recipe.siege),
            score=self._target_score(target),
        )

    @staticmethod
    def _target_score(detection: Detection) -> float:
        """Score a detection by confidence and label importance."""
        priority = 0.25 if detection.label in HIGH_VALUE_LABELS else 0.0
        return detection.confidence + priority

    @staticmethod
    def _side_for_target(target: Detection, redline: RedlineResult) -> str:
        """Pick the redline edge closest to the target center."""
        if not redline.is_valid():
            return AttackSide.RANDOM.value
        center = target.center()
        best_index = 0
        best_distance = float("inf")
        for index in range(4):
            midpoint = redline.edge_midpoint(index)
            distance = center.distance_to(midpoint)
            if distance < best_distance:
                best_distance = distance
                best_index = index
        return _EDGE_SIDES[best_index]

    def deploy(
        self,
        plan: AttackPlan,
        redline: RedlineResult,
        dry_run: bool = True,
    ) -> int:
        """Tap along the selected edge; returns the number of taps performed."""
        if not redline.is_valid():
            raise AttackError("Redline is not valid; refusing to deploy")
        edge_index = (
            _EDGE_SIDES.index(plan.side) if plan.side in _EDGE_SIDES else 0
        )
        points = list(redline.edges[edge_index])
        if dry_run or not self._allow_input:
            self._log(
                "info",
                f"Dry run: would deploy {len(points)} points on edge {_EDGE_SIDES[edge_index]}",
            )
            return 0
        if self._adb is None:
            raise AttackError("No ADB transport configured for deployment")
        taps = 0
        for point in points:
            if self._adb.tap(point.x, point.y):
                taps += 1
        return taps


class AttackStep:
    """CycleStep adapter that scans and optionally deploys one attack."""

    def __init__(self, model: AttackModel, execute: bool = False) -> None:
        """Wrap *model*; *execute* must be explicit for real input."""
        self._model = model
        self._execute = execute

    @property
    def name(self) -> str:
        """Return the stable step name."""
        return "attack"

    def run(self, context: CycleContext) -> StepResult:
        """Scan once and optionally deploy the resulting plan."""
        scan = self._model.scan(cancel_event=context.session.stop_event)
        if scan.plan.target is None:
            return StepResult(False, "No attack target detected", phase=BotPhase.SEARCHING)
        taps = 0
        if self._execute:
            taps = self._model.deploy(scan.plan, scan.redline, dry_run=False)
        label = scan.plan.target.label
        message = f"Target {label} ({scan.source}), side {scan.plan.side}"
        if self._execute:
            message += f", {taps} taps"
        return StepResult(
            True,
            message,
            phase=BotPhase.ATTACKING,
            data={"source": scan.source, "taps": taps},
        )
