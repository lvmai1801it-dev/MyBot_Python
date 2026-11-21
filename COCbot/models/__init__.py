"""Pure domain models shared by core and the village/upgrade feature.

This package must never import PyQt5.
"""

from COCbot.models.attack import Detection
from COCbot.models.enums import AttackSide, EmulatorType, ResourceKind, UpgradeCategory
from COCbot.models.frame import Frame
from COCbot.models.geometry import BoundingBox, Point, Rect, Size
from COCbot.models.resources import ResourceSnapshot

__all__ = [
    "AttackSide",
    "BoundingBox",
    "Detection",
    "EmulatorType",
    "Frame",
    "Point",
    "Rect",
    "ResourceKind",
    "ResourceSnapshot",
    "Size",
    "UpgradeCategory",
]
