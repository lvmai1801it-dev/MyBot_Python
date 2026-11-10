"""Attack planning and result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from COCbot.models.geometry import BoundingBox, Point
from COCbot.models.resources import ResourceSnapshot


@dataclass(frozen=True)
class Detection:
    """One object returned by the YOLO/OpenCV detector."""

    label: str
    confidence: float
    bbox: BoundingBox
    polygon: tuple[Point, ...] = ()

    def center(self) -> Point:
        """Return the center of the detection box."""
        return self.bbox.center


@dataclass(frozen=True)
class AttackPlan:
    """A complete deployment plan for one battle."""

    target: Detection | None = None
    side: str = "RANDOM"
    troops: Mapping[str, int] = field(default_factory=dict)
    spells: Mapping[str, int] = field(default_factory=dict)
    siege: Mapping[str, int] = field(default_factory=dict)
    score: float = 0.0

    def total_units(self) -> int:
        """Return the total number of troop, spell, and siege units."""
        return sum(self.troops.values()) + sum(self.spells.values()) + sum(self.siege.values())

    def is_empty(self) -> bool:
        """Return ``True`` when the plan contains no units."""
        return self.total_units() == 0


@dataclass(frozen=True)
class AttackResult:
    """Outcome of a single battle."""

    success: bool
    stars: int = 0
    destruction: float = 0.0
    loot: ResourceSnapshot = field(default_factory=ResourceSnapshot)
    duration: float = 0.0
    reason: str = ""

    @property
    def is_victory(self) -> bool:
        """Return ``True`` when at least one star was earned."""
        return self.success and self.stars > 0
