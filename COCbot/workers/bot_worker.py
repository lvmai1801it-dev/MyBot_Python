"""QThread wrapper for the long-running bot engine."""

from __future__ import annotations

import traceback
from typing import Any

from PyQt5.QtCore import QThread, pyqtSignal

from COCbot.core.ports import BotEnginePort
from COCbot.models.bot_state import BotEvent


class BotWorker(QThread):
    """Run a :class:`BotEnginePort` on a background thread."""

    work_started = pyqtSignal()
    work_finished = pyqtSignal()
    failed = pyqtSignal(str, str)
    event_emitted = pyqtSignal(object)

    def __init__(self, engine: BotEnginePort, parent: Any = None) -> None:
        """Store the engine; call :meth:`start` to launch it."""
        super().__init__(parent)
        self._engine = engine
        self._error_traceback = ""

    @property
    def engine(self) -> BotEnginePort:
        """Return the wrapped engine."""
        return self._engine

    @property
    def error_traceback(self) -> str:
        """Return the traceback of the last failure (empty on success)."""
        return self._error_traceback

    def emit(self, event: BotEvent) -> None:
        """Forward one engine event to the GUI thread (EventSinkPort)."""
        self.event_emitted.emit(event)

    def run(self) -> None:
        """Run the engine until it stops and emit terminal signals."""
        self.work_started.emit()
        try:
            self._engine.run_forever(self)
        except Exception as exc:
            self._error_traceback = traceback.format_exc()
            self.failed.emit(type(exc).__name__, str(exc))
        finally:
            self.work_finished.emit()

    def stop(self) -> None:
        """Request a cooperative stop."""
        self._engine.request_stop()

    def pause(self) -> None:
        """Request a cooperative pause."""
        self._engine.request_pause()

    def resume(self) -> None:
        """Resume the engine."""
        self._engine.request_resume()
