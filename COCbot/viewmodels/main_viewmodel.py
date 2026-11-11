"""Shell view-model: owns the bot worker and exposes run controls."""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal

from COCbot.core.ports import BotEnginePort
from COCbot.models.bot_state import BotEvent
from COCbot.viewmodels.base_viewmodel import BaseViewModel
from COCbot.workers.bot_worker import BotWorker


class MainViewModel(BaseViewModel):
    """Start/stop/pause the orchestrator and relay its events to the shell."""

    event_emitted = pyqtSignal(object)
    running_changed = pyqtSignal(bool)
    status_message = pyqtSignal(str, str)

    def __init__(self, orchestrator: BotEnginePort, parent=None) -> None:
        """Wrap *orchestrator*; it is started only on user request."""
        super().__init__(parent)
        self._orchestrator = orchestrator
        self._worker: BotWorker | None = None

    @property
    def orchestrator(self) -> BotEnginePort:
        """Return the injected engine."""
        return self._orchestrator

    @property
    def is_running(self) -> bool:
        """Return ``True`` while the bot worker is active."""
        return self._worker is not None and self._worker.isRunning()

    def _status(self, message: str, kind: str = "info") -> None:
        """Publish a shell status line."""
        self.status_message.emit(message, kind)

    def start(self) -> bool:
        """Start the bot loop; return ``False`` when already running."""
        if self.is_running:
            return False
        worker = BotWorker(self._orchestrator, parent=self)
        worker.work_finished.connect(self._on_finished)
        worker.failed.connect(self._on_failed)
        worker.event_emitted.connect(self._on_event)
        self._worker = worker
        self._set_busy(True)
        self.running_changed.emit(True)
        self._status("Bot running", "success")
        worker.start()
        return True

    def stop(self) -> None:
        """Request a cooperative stop."""
        if self.is_running:
            self._status("Stopping bot…", "warning")
            self._worker.stop()

    def pause(self) -> None:
        """Pause the bot at the next safe point."""
        if self.is_running:
            self._worker.pause()
            self._status("Bot paused", "warning")

    def resume(self) -> None:
        """Resume a paused bot."""
        if self.is_running:
            self._worker.resume()
            self._status("Bot resumed", "success")

    def shutdown(self, wait_ms: int = 3000) -> None:
        """Stop the worker and wait briefly for the thread to exit."""
        worker = self._worker
        if worker is None:
            return
        worker.stop()
        if worker.isRunning() and not worker.wait(wait_ms):
            self._report_error("Bot worker did not stop in time; terminating it")
            worker.terminate()
            worker.wait(1000)
        self._worker = None
        self._set_busy(False)

    def _on_finished(self) -> None:
        """Publish that the loop has stopped."""
        self._worker = None
        self._set_busy(False)
        self.running_changed.emit(False)
        self._status("Bot stopped", "info")

    def _on_failed(self, kind: str, message: str) -> None:
        """Relay an engine failure to the shell."""
        self._report_error(f"{kind}: {message}")
        self._status(f"{kind}: {message}", "error")

    def _on_event(self, event: BotEvent) -> None:
        """Re-emit one engine event."""
        self.event_emitted.emit(event)
