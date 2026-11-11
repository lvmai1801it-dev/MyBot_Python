"""Generic QThread worker with structured signals."""

from __future__ import annotations

import threading
import traceback
from typing import Any, Callable

from PyQt5.QtCore import QThread, pyqtSignal


class BaseWorker(QThread):
    """Run one callable off the GUI thread and report progress via signals."""

    work_started = pyqtSignal()
    work_finished = pyqtSignal(object)
    failed = pyqtSignal(str, str)
    canceled = pyqtSignal()
    progress = pyqtSignal(int, int, str)
    log = pyqtSignal(str, str)

    def __init__(
        self,
        target: Callable[..., Any],
        *args: object,
        parent: Any = None,
        pass_cancel_event: bool = False,
        **kwargs: object,
    ) -> None:
        """Store the callable and arguments; call :meth:`start` to run it."""
        super().__init__(parent)
        self._target = target
        self._args = args
        self._kwargs = kwargs
        self._pass_cancel_event = pass_cancel_event
        self._cancel_event = threading.Event()
        self._error_traceback = ""

    @property
    def cancel_event(self) -> threading.Event:
        """Return the cooperative cancellation flag."""
        return self._cancel_event

    @property
    def error_traceback(self) -> str:
        """Return the traceback of the last failure (empty on success)."""
        return self._error_traceback

    def cancel(self) -> None:
        """Ask the callable to stop and request Qt interruption."""
        self._cancel_event.set()
        self.requestInterruption()

    def run(self) -> None:
        """Execute the callable and emit the appropriate terminal signal."""
        self.work_started.emit()
        try:
            if self._pass_cancel_event:
                result = self._target(self._cancel_event, *self._args, **self._kwargs)
            else:
                result = self._target(*self._args, **self._kwargs)
        except Exception as exc:  # pragma: no cover - exercised via tests
            self._error_traceback = traceback.format_exc()
            self.log.emit("ERROR", self._error_traceback)
            self.failed.emit(type(exc).__name__, str(exc))
            return
        if self._cancel_event.is_set():
            self.canceled.emit()
            return
        self.work_finished.emit(result)
