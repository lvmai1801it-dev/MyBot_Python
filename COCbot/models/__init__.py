"""Pure domain models shared by core, features, and workers.

This package must never import PyQt5.
"""

from COCbot.models.account import AccountProfile, AccountSwitchState
from COCbot.models.attack import AttackPlan, AttackResult, Detection
from COCbot.models.bot_state import BotEvent, BotStatus, Progress
from COCbot.models.emulator import EmulatorInstance
from COCbot.models.enums import (
    AccountSwitchMode,
    AttackSide,
    BotPhase,
    EmulatorType,
    LogLevel,
    ResourceKind,
    UpgradeCategory,
)
from COCbot.models.frame import Frame
from COCbot.models.geometry import BoundingBox, Point, Rect, Size
from COCbot.models.resources import ResourceSnapshot
from COCbot.models.village import UpgradeTask, VillageState

__all__ = [
    "AccountProfile",
    "AccountSwitchMode",
    "AccountSwitchState",
    "AttackPlan",
    "AttackResult",
    "AttackSide",
    "BotEvent",
    "BotPhase",
    "BotStatus",
    "BoundingBox",
    "Detection",
    "EmulatorInstance",
    "EmulatorType",
    "Frame",
    "LogLevel",
    "Point",
    "Progress",
    "Rect",
    "ResourceKind",
    "ResourceSnapshot",
    "Size",
    "UpgradeCategory",
    "UpgradeTask",
    "VillageState",
]
