"""Base QObject view-model with busy state and error reporting."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from PyQt5.QtCore import QObject, pyqtSignal


class BaseViewModel(QObject):
    """Common signals and helpers for every feature view-model.

    View-models publish state through signals; they never call widget setters.
    """

    error_occurred = pyqtSignal(str)
    busy_changed = pyqtSignal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        """Create the base view-model."""
        super().__init__(parent)
        self._busy = False

    @property
    def is_busy(self) -> bool:
        """Return ``True`` while a blocking operation is in progress."""
        return self._busy

    def _set_busy(self, value: bool) -> None:
        """Update busy state and notify the view."""
        flag = bool(value)
        if flag == self._busy:
            return
        self._busy = flag
        self.busy_changed.emit(flag)

    def _report_error(self, message: str) -> None:
        """Publish a human-readable error."""
        self.error_occurred.emit(message)

    @contextmanager
    def busy(self) -> Iterator[None]:
        """Mark the view-model busy for the duration of a block."""
        self._set_busy(True)
        try:
            yield
        finally:
            self._set_busy(False)
