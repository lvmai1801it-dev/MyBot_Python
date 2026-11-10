"""Bot status, progress, and event models."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Mapping

from COCbot.models.enums import BotPhase, LogLevel


@dataclass(frozen=True)
class BotEvent:
    """A structured event emitted by the bot engine."""

    level: LogLevel
    message: str
    phase: BotPhase = BotPhase.IDLE
    timestamp: float = field(default_factory=time.time)
    data: Mapping[str, Any] = field(default_factory=dict)

    def is_error(self) -> bool:
        """Return ``True`` for warning/error/critical events."""
        return self.level in (LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL)


@dataclass
class BotStatus:
    """Mutable status owned by the shell ViewModel."""

    phase: BotPhase = BotPhase.IDLE
    is_running: bool = False
    is_paused: bool = False
    current_account: str = ""
    attacks_done: int = 0
    last_error: str = ""

    def reset(self) -> None:
        """Return the status to its idle state."""
        self.phase = BotPhase.IDLE
        self.is_running = False
        self.is_paused = False
        self.current_account = ""
        self.attacks_done = 0
        self.last_error = ""


@dataclass(frozen=True)
class Progress:
    """A progress value suitable for a progress bar or status label."""

    current: int
    total: int
    message: str = ""

    def __post_init__(self) -> None:
        """Clamp counters to sane values."""
        object.__setattr__(self, "current", max(0, int(self.current)))
        object.__setattr__(self, "total", max(0, int(self.total)))

    @property
    def percent(self) -> int:
        """Return progress as an integer percentage in ``0..100``."""
        if self.total <= 0:
            return 0
        return min(100, max(0, round(self.current * 100 / self.total)))

    @property
    def is_complete(self) -> bool:
        """Return ``True`` when ``current`` has reached ``total``."""
        return self.total > 0 and self.current >= self.total
