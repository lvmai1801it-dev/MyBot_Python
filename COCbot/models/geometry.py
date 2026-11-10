"""Geometry value objects used by vision and attack planners.

All values are expressed in screen pixels unless stated otherwise.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    """A 2D point in screen coordinates."""

    x: int
    y: int

    def as_tuple(self) -> tuple[int, int]:
        """Return the point as an ``(x, y)`` tuple."""
        return (self.x, self.y)

    def distance_to(self, other: "Point") -> float:
        """Return the Euclidean distance to *other*."""
        return math.hypot(self.x - other.x, self.y - other.y)


@dataclass(frozen=True)
class Size:
    """A width/height pair."""

    width: int
    height: int

    @property
    def area(self) -> int:
        """Return the area in square pixels."""
        return max(0, self.width) * max(0, self.height)


@dataclass(frozen=True)
class Rect:
    """An axis-aligned rectangle described by its top-left corner and size."""

    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        """Return the exclusive right edge."""
        return self.x + self.width

    @property
    def bottom(self) -> int:
        """Return the exclusive bottom edge."""
        return self.y + self.height

    @property
    def area(self) -> int:
        """Return the area in square pixels."""
        return max(0, self.width) * max(0, self.height)

    @property
    def center(self) -> Point:
        """Return the center point of the rectangle."""
        return Point(self.x + self.width // 2, self.y + self.height // 2)

    def contains(self, point: Point) -> bool:
        """Return ``True`` when *point* lies inside the rectangle."""
        return self.x <= point.x < self.right and self.y <= point.y < self.bottom

    def clamp(self, bounds: "Rect") -> "Rect":
        """Return a copy clipped to *bounds*."""
        left = max(self.x, bounds.x)
        top = max(self.y, bounds.y)
        right = min(self.right, bounds.right)
        bottom = min(self.bottom, bounds.bottom)
        return Rect(left, top, max(0, right - left), max(0, bottom - top))

    def as_xyxy(self) -> tuple[int, int, int, int]:
        """Return the rectangle as ``(x1, y1, x2, y2)``."""
        return (self.x, self.y, self.right, self.bottom)

    @classmethod
    def from_xyxy(cls, x1: int, y1: int, x2: int, y2: int) -> "Rect":
        """Build a rectangle from any two opposite corners."""
        left, right = sorted((int(x1), int(x2)))
        top, bottom = sorted((int(y1), int(y2)))
        return cls(left, top, right - left, bottom - top)


@dataclass(frozen=True)
class BoundingBox:
    """An inclusive-exclusive ``xyxy`` box returned by a detector."""

    x1: int
    y1: int
    x2: int
    y2: int

    def __post_init__(self) -> None:
        """Reject inverted boxes early so downstream math stays valid."""
        if self.x2 < self.x1 or self.y2 < self.y1:
            raise ValueError(f"invalid bounding box: {self}")

    @property
    def width(self) -> int:
        """Return the box width in pixels."""
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        """Return the box height in pixels."""
        return self.y2 - self.y1

    @property
    def area(self) -> int:
        """Return the box area in square pixels."""
        return self.width * self.height

    @property
    def center(self) -> Point:
        """Return the center point of the box."""
        return Point((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    def to_rect(self) -> Rect:
        """Convert the box to a :class:`Rect`."""
        return Rect(self.x1, self.y1, self.width, self.height)

    def iou(self, other: "BoundingBox") -> float:
        """Return the intersection-over-union ratio with *other*."""
        inter_x1 = max(self.x1, other.x1)
        inter_y1 = max(self.y1, other.y1)
        inter_x2 = min(self.x2, other.x2)
        inter_y2 = min(self.y2, other.y2)
        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        intersection = inter_w * inter_h
        union = self.area + other.area - intersection
        return intersection / union if union > 0 else 0.0
