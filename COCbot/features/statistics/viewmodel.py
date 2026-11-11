"""Statistics feature view-model."""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal

from COCbot.core.errors import StorageError
from COCbot.features.statistics.model import StatisticsModel, StatisticsSnapshot
from COCbot.viewmodels.base_viewmodel import BaseViewModel


class StatisticsViewModel(BaseViewModel):
    """Load and reset statistics, publishing snapshots to the view."""

    snapshot_loaded = pyqtSignal(object)
    status_message = pyqtSignal(str, str)

    def __init__(self, model: StatisticsModel, parent=None) -> None:
        """Create the view-model around a statistics model."""
        super().__init__(parent)
        self._model = model
        self._snapshot: StatisticsSnapshot | None = None

    @property
    def snapshot(self) -> StatisticsSnapshot | None:
        """Return the last loaded snapshot."""
        return self._snapshot

    def refresh(self) -> None:
        """Reload every stats file."""
        with self.busy():
            try:
                snapshot = self._model.load()
            except Exception as exc:
                self._report_error(f"Could not load statistics: {exc}")
                return
        self._snapshot = snapshot
        self.snapshot_loaded.emit(snapshot)
        self._status("Statistics refreshed", "info")

    def reset(self) -> None:
        """Reset every stats file to zero after the view confirms."""
        with self.busy():
            try:
                snapshot = self._model.zero_all()
            except StorageError as exc:
                self._report_error(str(exc))
                self._status(str(exc), "error")
                return
        self._snapshot = snapshot
        self.snapshot_loaded.emit(snapshot)
        self._status("Statistics reset", "warning")

    def _status(self, message: str, kind: str = "info") -> None:
        """Publish a status line for the view."""
        self.status_message.emit(message, kind)
