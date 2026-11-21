"""Logs feature view-model: buffers BotEvent rows and exposes filters."""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import pyqtSignal

from COCbot.core.errors import StorageError
from COCbot.features.logs.model import LogEntry, LogsModel
from COCbot.models.bot_state import BotEvent
from COCbot.models.enums import LogLevel
from COCbot.viewmodels.base_viewmodel import BaseViewModel


class LogsViewModel(BaseViewModel):
    """Own the log buffer and publish rows/filters to the view."""

    entry_added = pyqtSignal(object)
    entries_loaded = pyqtSignal(object)
    entries_cleared = pyqtSignal()
    status_message = pyqtSignal(str, str)
    exported = pyqtSignal(str, int)

    def __init__(self, model: LogsModel | None = None, parent=None) -> None:
        """Create the view-model around a bounded log model."""
        super().__init__(parent)
        self._model = model or LogsModel()

    @property
    def entries(self) -> tuple[LogEntry, ...]:
        """Return the currently filtered rows."""
        return self._model.entries()

    def append_event(self, event: BotEvent) -> None:
        """Add one structured event and emit it when it passes the filter."""
        entry = self._model.add_event(event)
        if self._model.matches(entry):
            self.entry_added.emit(entry)

    def refresh(self) -> None:
        """Re-emit every row that matches the active filter."""
        self.entries_loaded.emit(self._model.entries())

    def set_filter(self, level: LogLevel | None, search: str = "") -> None:
        """Apply a level/text filter and reload the table."""
        self._model.set_filter(level, search)
        self.refresh()

    def clear(self) -> None:
        """Clear the buffer and the table."""
        self._model.clear()
        self.entries_cleared.emit()
        self._status("Log cleared", "info")

    def export(self, path: Path | str) -> bool:
        """Export the filtered rows to *path*."""
        try:
            count = self._model.export(path)
        except StorageError as exc:
            self._report_error(str(exc))
            self._status(str(exc), "error")
            return False
        self.exported.emit(str(path), count)
        self._status(f"Exported {count} log rows", "success")
        return True

    def _status(self, message: str, kind: str = "info") -> None:
        """Publish a status line for the view."""
        self.status_message.emit(message, kind)
