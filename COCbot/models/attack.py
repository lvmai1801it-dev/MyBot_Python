"""Detection model returned by template matchers.

Only :class:`Detection` remains: the legacy attack pipeline carries its own
plan/result structures (``COCbot.attack.planner`` / ``cycle``), so the
MVVM-era ``AttackPlan``/``AttackResult``/``RedlineResult`` dataclasses were
archived with the shell.
"""

from __future__ import annotations

from dataclasses import dataclass

from COCbot.models.geometry import BoundingBox, Point


@dataclass(frozen=True)
class Detection:
    """One object returned by a template or detector match."""

    label: str
    confidence: float
    bbox: BoundingBox
    polygon: tuple[Point, ...] = ()

    def center(self) -> Point:
        """Return the center of the detection box."""
        return self.bbox.center
