"""Logs feature domain model (pure Python, no Qt)."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from COCbot.core.errors import StorageError
from COCbot.models.bot_state import BotEvent
from COCbot.models.enums import BotPhase, LogLevel


@dataclass(frozen=True)
class LogEntry:
    """One human-readable log row."""

    timestamp: float
    level: LogLevel
    message: str
    phase: BotPhase = BotPhase.IDLE
    data: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_event(cls, event: BotEvent) -> "LogEntry":
        """Build a row from a structured bot event."""
        return cls(
            timestamp=event.timestamp,
            level=event.level,
            message=event.message,
            phase=event.phase,
            data=dict(event.data),
        )

    @property
    def time_text(self) -> str:
        """Return ``HH:MM:SS`` for the table."""
        return time.strftime("%H:%M:%S", time.localtime(self.timestamp))

    def as_text(self) -> str:
        """Return a plain-text line for export."""
        return f"{self.time_text} • {self.level.value} {self.message}"


class LogsModel:
    """Bounded in-memory log buffer with level/search filtering."""

    def __init__(self, max_entries: int = 5000) -> None:
        """Create a buffer holding at most *max_entries* rows."""
        self._entries: deque[LogEntry] = deque(maxlen=max(100, int(max_entries)))
        self._level: LogLevel | None = None
        self._search = ""
        self._lock = threading.RLock()

    def add_event(self, event: BotEvent) -> LogEntry:
        """Append a structured event and return the stored row."""
        entry = LogEntry.from_event(event)
        self.add_entry(entry)
        return entry

    def add_entry(self, entry: LogEntry) -> None:
        """Append one row, dropping the oldest when full."""
        with self._lock:
            self._entries.append(entry)

    def set_filter(self, level: LogLevel | None, search: str = "") -> None:
        """Set the active level and text filter."""
        with self._lock:
            self._level = level
            self._search = search.strip().casefold()

    def matches(self, entry: LogEntry) -> bool:
        """Return ``True`` when *entry* passes the active filter."""
        with self._lock:
            if self._level is not None and entry.level != self._level:
                return False
            if not self._search:
                return True
            haystack = f"{entry.message} {entry.phase.value}".casefold()
            return self._search in haystack

    def entries(self) -> tuple[LogEntry, ...]:
        """Return the filtered rows in chronological order."""
        with self._lock:
            return tuple(entry for entry in self._entries if self.matches(entry))

    def all_entries(self) -> tuple[LogEntry, ...]:
        """Return every buffered row, ignoring filters."""
        with self._lock:
            return tuple(self._entries)

    def clear(self) -> None:
        """Drop every buffered row."""
        with self._lock:
            self._entries.clear()

    def export(self, path: Path | str) -> int:
        """Write filtered rows to *path* and return the row count."""
        target = Path(path)
        rows = self.entries()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                "\n".join(entry.as_text() for entry in rows) + ("\n" if rows else ""),
                encoding="utf-8",
            )
        except OSError as exc:
            raise StorageError(f"Could not export log: {exc}") from exc
        return len(rows)
