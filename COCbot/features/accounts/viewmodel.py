"""Accounts feature view-model: profile actions on background workers."""

from __future__ import annotations

from typing import Callable

from PyQt5.QtCore import pyqtSignal

from COCbot.features.accounts.model import AccountsModel
from COCbot.models.account import AccountsSnapshot
from COCbot.viewmodels.base_viewmodel import BaseViewModel
from COCbot.workers.task_worker import TaskWorker


class AccountsViewModel(BaseViewModel):
    """Load profiles and run pull/push/switch/delete off the GUI thread."""

    snapshot_loaded = pyqtSignal(object)
    action_finished = pyqtSignal(str)
    config_saved = pyqtSignal(object)
    status_message = pyqtSignal(str, str)

    def __init__(self, model: AccountsModel, parent=None) -> None:
        """Create the view-model around an accounts model."""
        super().__init__(parent)
        self._model = model
        self._worker: TaskWorker | None = None

    def _status(self, message: str, kind: str = "info") -> None:
        """Publish a status line for the view."""
        self.status_message.emit(message, kind)

    def refresh(self) -> None:
        """Reload profiles and switch configuration in a worker."""
        self._start("Refresh", self._model.snapshot)

    def pull(self, name: str) -> None:
        """Save the current account under *name*."""
        self._start("Pull", lambda: self._model.pull(name))

    def push(self, name: str, current_profile: str = "") -> None:
        """Restore *name* into the game."""
        self._start("Push", lambda: self._model.push(name, current_profile))

    def switch(self, target: str, current_profile: str = "") -> None:
        """Switch to *target*."""
        self._start("Switch", lambda: self._model.switch(target, current_profile))

    def delete(self, name: str) -> None:
        """Delete profile *name*."""
        self._start("Delete", lambda: self._model.delete(name))

    def save_auto_switch(self, enabled: bool, attacks: int) -> None:
        """Persist the auto-switch options (fast file write)."""
        try:
            config = self._model.update_auto_switch(enabled, attacks)
        except Exception as exc:
            self._report_error(f"Could not save switch config: {exc}")
            return
        self.config_saved.emit(config)
        self._status("Auto-switch settings saved", "success")

    def shutdown(self, wait_ms: int = 3000) -> None:
        """Cancel and wait for the active profile worker on app exit."""
        worker = self._worker
        if worker is None:
            return
        worker.cancel()
        if worker.isRunning() and not worker.wait(wait_ms):
            worker.terminate()
            worker.wait(1000)
        self._worker = None
        self._set_busy(False)

    def _start(self, action: str, target: Callable[[], object]) -> None:
        """Start a one-shot action worker."""
        if self.is_busy:
            self._status("An account operation is already running", "warning")
            return
        worker = TaskWorker(target, parent=self)
        worker.work_finished.connect(self._clear_worker)
        worker.work_finished.connect(lambda result: self._on_finished(action, result))
        worker.failed.connect(self._on_failed)
        self._worker = worker
        self._set_busy(True)
        self._status(f"{action}…", "info")
        worker.start()

    def _clear_worker(self, _result: object) -> None:
        """Reset busy state before downstream slots run."""
        self._worker = None
        self._set_busy(False)

    def _on_finished(self, action: str, result: object) -> None:
        """Publish the action result."""
        if action == "Refresh" and isinstance(result, AccountsSnapshot):
            self.snapshot_loaded.emit(result)
            self._status("Profiles refreshed", "info")
        else:
            self._status(f"{action} complete", "success")
        self.action_finished.emit(action)

    def _on_failed(self, kind: str, message: str) -> None:
        """Report a failed profile action."""
        self._report_error(f"{kind}: {message}")
        self._status(f"{kind}: {message}", "error")
