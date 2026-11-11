"""Clean-port attack deployment using scanned army slots and redline edges."""

from __future__ import annotations

import math
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
        hero_ability_delay: float = 15.0,
    ) -> None:
        """Create the executor; input stays dry-run unless *execute* is true."""
        self._adb = adb
        self._clock = clock or SystemClock()
        self._logger = logger
        self._execute = execute
        self._jitter = max(0, int(jitter))
        self._hero_ability_delay = max(0.0, float(hero_ability_delay))

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
    def _edges_for(plan: AttackPlan, redline: RedlineResult) -> list[tuple[Point, ...]]:
        """Return one planned edge, or all four when the side is random."""
        if not redline.edges:
            return []
        if plan.side in _EDGE_INDEX:
            return [redline.edges[_EDGE_INDEX[plan.side] % len(redline.edges)]]
        return list(redline.edges)

    def deploy(
        self,
        plan: AttackPlan,
        redline: RedlineResult,
        slots: list[ArmySlot],
        execute: bool | None = None,
        cancel_event: Event | None = None,
        activate_heroes: bool = True,
    ) -> AttackExecutionResult:
        """Deploy scanned cards along the plan edge."""
        if not redline.is_valid():
            return AttackExecutionResult(False, message="Redline is not valid")
        if not slots:
            return AttackExecutionResult(False, message="No army cards detected")
        edges = self._edges_for(plan, redline)
        if not edges:
            return AttackExecutionResult(False, message="No deploy edge")

        should_tap = self._execute if execute is None else bool(execute)
        planned = 0
        taps = 0
        midpoint = edges[0][len(edges[0]) // 2]
        hero_slots: list[ArmySlot] = []

        for slot in slots:
            if cancel_event is not None and cancel_event.is_set():
                raise OperationCancelled("Attack deployment cancelled")
            if slot.kind is ArmySlotKind.TROOP:
                per_edge = max(1, math.ceil(max(1, slot.count) / len(edges)))
                points = [
                    point
                    for edge in edges
                    for point in spread_points(edge, per_edge)
                ][: max(1, slot.count)]
                for point in points:
                    if not redline.contains(point):
                        continue
                    planned += 1
                    if not should_tap:
                        continue
                    self._select(slot)
                    if self._tap(point):
                        taps += 1
                    self._clock.sleep(0.02)
            elif slot.kind in (ArmySlotKind.HERO, ArmySlotKind.SIEGE):
                if not redline.contains(midpoint):
                    continue
                planned += 1
                if slot.kind is ArmySlotKind.HERO:
                    hero_slots.append(slot)
                if should_tap:
                    self._select(slot)
                    if self._tap(midpoint):
                        taps += 1
                    self._clock.sleep(0.2)
            elif slot.kind is ArmySlotKind.SPELL:
                if not redline.contains(midpoint):
                    continue
                planned += max(1, slot.count)
                for _ in range(max(1, slot.count)):
                    if should_tap:
                        self._select(slot)
                        if self._tap(midpoint):
                            taps += 1
                        self._clock.sleep(0.25)

        if should_tap and activate_heroes and hero_slots:
            self._log(
                "info",
                f"Waiting {self._hero_ability_delay:.0f}s to activate hero abilities",
            )
            self._clock.sleep(self._hero_ability_delay)
            for slot in hero_slots:
                self._select(slot)
                taps += 1

        mode = "tapped" if should_tap else "planned (dry run)"
        message = f"{planned} deploy points {mode} on {len(slots)} cards"
        self._log("info", message)
        return AttackExecutionResult(True, planned=planned, taps=taps, message=message)
