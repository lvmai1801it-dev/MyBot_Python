"""Clean-port attack deployment using scanned army slots and redline edges."""

from __future__ import annotations

import random
from dataclasses import dataclass
from threading import Event

from COCbot.core.clock import SystemClock
from COCbot.core.errors import OperationCancelled
from COCbot.core.ports import AdbPort, ClockPort, LoggerPort
from COCbot.features.attack.army_bar import ArmySlot, ArmySlotKind
from COCbot.models.attack import AttackPlan, RedlineResult
from COCbot.models.geometry import Point

_EDGE_INDEX = {"TR": 0, "BR": 1, "BL": 2, "TL": 3}


@dataclass(frozen=True)
class AttackExecutionResult:
    """Outcome of one deployment."""

    ok: bool
    planned: int = 0
    taps: int = 0
    message: str = ""


def spread_points(edge: tuple[Point, ...], count: int) -> list[Point]:
    """Spread *count* points along an edge (5%..95% of its length)."""
    if not edge:
        return []
    if len(edge) == 1 or count <= 1:
        return [edge[len(edge) // 2]]
    start = edge[0]
    end = edge[-1]
    sx = start.x + (end.x - start.x) * 0.05
    sy = start.y + (end.y - start.y) * 0.05
    ex = start.x + (end.x - start.x) * 0.95
    ey = start.y + (end.y - start.y) * 0.95
    if len(edge) >= count:
        lo = max(0, int(len(edge) * 0.05))
        hi = min(len(edge) - 1, int(len(edge) * 0.95))
        step = (hi - lo) / max(1, count - 1)
        return [edge[int(round(lo + index * step))] for index in range(count)]
    return [
        Point(
            int(sx + (ex - sx) * index / (count - 1)),
            int(sy + (ey - sy) * index / (count - 1)),
        )
        for index in range(count)
    ]


class AttackExecutor:
    """Select army cards and tap them along the chosen redline edge."""

    def __init__(
        self,
        adb: AdbPort,
        clock: ClockPort | None = None,
        logger: LoggerPort | None = None,
        execute: bool = False,
        jitter: int = 3,
    ) -> None:
        """Create the executor; input stays dry-run unless *execute* is true."""
        self._adb = adb
        self._clock = clock or SystemClock()
        self._logger = logger
        self._execute = execute
        self._jitter = max(0, int(jitter))

    def _log(self, level: str, message: str) -> None:
        """Emit a log line when a logger was supplied."""
        if self._logger is not None:
            getattr(self._logger, level)(message)

    def _select(self, slot: ArmySlot) -> None:
        """Tap one army-bar card."""
        x, y = slot.tap_point()
        self._adb.tap(x, y)
        self._clock.sleep(0.15)

    def _tap(self, point: Point) -> bool:
        """Tap a deploy point with a small deterministic jitter."""
        x = point.x + random.randint(-self._jitter, self._jitter)
        y = point.y + random.randint(-self._jitter, self._jitter)
        return self._adb.tap(x, y)

    @staticmethod
    def _edge_for(plan: AttackPlan, redline: RedlineResult) -> tuple[Point, ...]:
        """Return the deploy edge selected by the plan."""
        if not redline.edges:
            return ()
        return redline.edges[_EDGE_INDEX.get(plan.side, 0) % len(redline.edges)]

    def deploy(
        self,
        plan: AttackPlan,
        redline: RedlineResult,
        slots: list[ArmySlot],
        execute: bool | None = None,
        cancel_event: Event | None = None,
    ) -> AttackExecutionResult:
        """Deploy scanned cards along the plan edge."""
        if not redline.is_valid():
            return AttackExecutionResult(False, message="Redline is not valid")
        if not slots:
            return AttackExecutionResult(False, message="No army cards detected")
        edge = self._edge_for(plan, redline)
        if not edge:
            return AttackExecutionResult(False, message="No deploy edge")

        should_tap = self._execute if execute is None else bool(execute)
        planned = 0
        taps = 0
        midpoint = edge[len(edge) // 2]

        for slot in slots:
            if cancel_event is not None and cancel_event.is_set():
                raise OperationCancelled("Attack deployment cancelled")
            if slot.kind is ArmySlotKind.TROOP:
                points = spread_points(edge, max(1, min(12, slot.count)))
                planned += len(points)
                for point in points:
                    if not should_tap:
                        continue
                    self._select(slot)
                    if self._tap(point):
                        taps += 1
                    self._clock.sleep(0.02)
            elif slot.kind in (ArmySlotKind.HERO, ArmySlotKind.SIEGE):
                planned += 1
                if should_tap:
                    self._select(slot)
                    if self._tap(midpoint):
                        taps += 1
                    self._clock.sleep(0.2)
            elif slot.kind is ArmySlotKind.SPELL:
                planned += max(1, slot.count)
                for _ in range(max(1, slot.count)):
                    if should_tap:
                        self._select(slot)
                        if self._tap(midpoint):
                            taps += 1
                        self._clock.sleep(0.25)

        mode = "tapped" if should_tap else "planned (dry run)"
        message = f"{planned} deploy points {mode} on {len(slots)} cards"
        self._log("info", message)
        return AttackExecutionResult(True, planned=planned, taps=taps, message=message)
