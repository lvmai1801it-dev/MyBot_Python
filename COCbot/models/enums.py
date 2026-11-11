"""Shared domain enumerations.

This module is part of the pure domain layer and must never import PyQt5.
"""

from __future__ import annotations

from enum import Enum


class EmulatorType(str, Enum):
    """Supported Android emulator families."""

    MEMU = "memu"
    LDPLAYER = "ldplayer"
    BLUESTACKS = "bluestacks"
    CUSTOM = "custom"

    @classmethod
    def from_value(cls, value: "str | EmulatorType | None") -> "EmulatorType":
        """Return a normalized emulator type from a loose config value."""
        if isinstance(value, cls):
            return value
        if not value:
            return cls.MEMU
        text = str(value).strip().lower().replace("-", "").replace("_", "").replace(" ", "")
        aliases = {
            "memu": cls.MEMU,
            "ld": cls.LDPLAYER,
            "ldplayer": cls.LDPLAYER,
            "ldplayermulti": cls.LDPLAYER,
            "bluestacks": cls.BLUESTACKS,
            "bs": cls.BLUESTACKS,
            "custom": cls.CUSTOM,
        }
        return aliases.get(text, cls.MEMU)


class BotPhase(str, Enum):
    """High-level phase of the bot state machine."""

    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    SEARCHING = "searching"
    ATTACKING = "attacking"
    RETURNING = "returning"
    UPGRADING = "upgrading"
    DONATING = "donating"
    SWITCHING_ACCOUNT = "switching_account"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class LogLevel(str, Enum):
    """Log severities understood by the UI and the logger."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ResourceKind(str, Enum):
    """Clash of Clans resource kinds."""

    GOLD = "gold"
    ELIXIR = "elixir"
    DARK_ELIXIR = "dark_elixir"


class UpgradeCategory(str, Enum):
    """Upgrade groups shown in the village upgrade tab."""

    WALL = "wall"
    HERO = "hero"
    DEFENSE = "defense"
    ARMY = "army"
    RESOURCE = "resource"
    OTHER = "other"


class AccountSwitchMode(str, Enum):
    """Account rotation strategies."""

    OFF = "off"
    ROTATE = "rotate"
    FULL_STORAGE = "full_storage"


class AttackSide(str, Enum):
    """Deployment side hint for an attack plan."""

    RANDOM = "RANDOM"
    TOP_LEFT = "TOP_LEFT"
    TOP_RIGHT = "TOP_RIGHT"
    BOTTOM_LEFT = "BOTTOM_LEFT"
    BOTTOM_RIGHT = "BOTTOM_RIGHT"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    TOP = "TOP"
    BOTTOM = "BOTTOM"

    @classmethod
    def from_value(cls, value: "str | AttackSide | None") -> "AttackSide":
        """Normalize a side label, accepting the legacy Vietnamese labels."""
        if isinstance(value, cls):
            return value
        if not value:
            return cls.RANDOM
        text = str(value).strip().upper().replace(" ", "_").replace("-", "_")
        aliases = {
            "NGẪU_NHIÊN": cls.RANDOM,
            "NGAU_NHIEN": cls.RANDOM,
            "RANDOM": cls.RANDOM,
            "TRÁI": cls.LEFT,
            "TRAI": cls.LEFT,
            "PHẢI": cls.RIGHT,
            "PHAI": cls.RIGHT,
            "TRÊN": cls.TOP,
            "TREN": cls.TOP,
            "DƯỚI": cls.BOTTOM,
            "DUOI": cls.BOTTOM,
            "TRÊN_TRÁI_(TL)": cls.TOP_LEFT,
            "TREN_TRAI_(TL)": cls.TOP_LEFT,
            "TRÊN_PHẢI_(TR)": cls.TOP_RIGHT,
            "TREN_PHAI_(TR)": cls.TOP_RIGHT,
            "DƯỚI_TRÁI_(BL)": cls.BOTTOM_LEFT,
            "DUOI_TRAI_(BL)": cls.BOTTOM_LEFT,
            "DƯỚI_PHẢI_(BR)": cls.BOTTOM_RIGHT,
            "DUOI_PHAI_(BR)": cls.BOTTOM_RIGHT,
            "NỬA_TRÊN_(TL_+_TR)": cls.TOP,
            "NUA_TREN_(TL_+_TR)": cls.TOP,
            "NỬA_DƯỚI_(BL_+_BR)": cls.BOTTOM,
            "NUA_DUOI_(BL_+_BR)": cls.BOTTOM,
        }
        if text in aliases:
            return aliases[text]
        try:
            return cls(text)
        except ValueError:
            return cls.RANDOM
