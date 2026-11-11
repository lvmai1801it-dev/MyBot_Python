"""Attack feature view-model: runs scans/deploys on QThread workers."""

from __future__ import annotations

from functools import partial

from PyQt5.QtCore import pyqtSignal

from COCbot.core.errors import OperationCancelled
from COCbot.features.attack.model import AttackModel, AttackScan
from COCbot.viewmodels.base_viewmodel import BaseViewModel
from COCbot.workers.task_worker import TaskWorker


class AttackViewModel(BaseViewModel):
    """Coordinate attack scans without blocking the GUI thread."""

    plan_ready = pyqtSignal(object)
    deployed = pyqtSignal(int)
    progress = pyqtSignal(int, int, str)
    status_message = pyqtSignal(str, str)

    def __init__(self, model: AttackModel, parent=None) -> None:
        """Create the view-model around an attack model."""
        super().__init__(parent)
        self._model = model
        self._worker: TaskWorker | None = None

    @property
    def last_scan(self) -> AttackScan | None:
        """Return the most recent completed scan."""
        return self._model.last_scan

    @property
    def is_scanning(self) -> bool:
        """Return ``True`` while a scan/deploy worker is active."""
        return self._worker is not None and self._worker.isRunning()

    def _emit_progress(self, current: int, total: int, message: str) -> None:
        """Forward model progress from the worker thread as a signal."""
        self.progress.emit(current, total, message)

    def _start_worker(self, target, on_finished) -> None:
        """Start a TaskWorker with shared lifecycle handling."""
        if self.is_scanning:
            self._status("An attack task is already running", "warning")
            return
        worker = TaskWorker(target, parent=self, pass_cancel_event=True)
        worker.work_finished.connect(on_finished)
        worker.failed.connect(self._on_failed)
        worker.canceled.connect(self._on_canceled)
        worker.work_finished.connect(self._finish)
        self._worker = worker
        self._set_busy(True)
        worker.start()

    def scan(self) -> None:
        """Start a background scan."""
        target = partial(self._model.scan, progress=self._emit_progress)
        self._status("Scanning enemy base…", "info")
        self._start_worker(target, self._on_scan_finished)

    def deploy_current(self, dry_run: bool = True) -> None:
        """Deploy the last plan in a background worker (dry-run by default)."""
        scan = self._model.last_scan
        if scan is None:
            self._report_error("Scan a base before deploying")
            return

        def target(cancel_event) -> int:
            if cancel_event.is_set():
                raise OperationCancelled("Deployment cancelled")
            return self._model.deploy(scan.plan, scan.redline, dry_run=dry_run)

        self._status("Dry-run deployment started…" if dry_run else "Deploying…", "info")
        self._start_worker(target, self._on_deployed)

    def cancel(self) -> None:
        """Cancel the active worker."""
        if self._worker is not None:
            self._worker.cancel()

    def shutdown(self, wait_ms: int = 3000) -> None:
        """Cancel and wait for the active worker on app exit."""
        worker = self._worker
        if worker is None:
            return
        worker.cancel()
        if worker.isRunning() and not worker.wait(wait_ms):
            worker.terminate()
            worker.wait(1000)
        self._worker = None
        self._set_busy(False)

    def _finish(self, _result: object) -> None:
        """Reset busy state when a worker terminates."""
        self._set_busy(False)
        self._worker = None

    def _on_scan_finished(self, scan: object) -> None:
        """Publish a completed scan."""
        if not isinstance(scan, AttackScan):
            self._report_error("Scan returned an unexpected result")
            return
        self.plan_ready.emit(scan)
        target = scan.plan.target.label if scan.plan.target else "none"
        self._status(
            f"Plan ready: {target} · redline {scan.source} · {scan.duration:.2f}s",
            "success",
        )

    def _on_deployed(self, taps: object) -> None:
        """Publish the number of taps performed by a deployment."""
        count = int(taps) if isinstance(taps, int) else 0
        self.deployed.emit(count)
        if count:
            self._status(f"Deployed {count} taps", "success")
        else:
            self._status("Dry run complete — no taps sent", "info")

    def _on_failed(self, kind: str, message: str) -> None:
        """Report a worker failure, treating cancellation as a warning."""
        if self._worker is not None and self._worker.cancel_event.is_set():
            self._status("Attack task cancelled", "warning")
        else:
            self._report_error(f"{kind}: {message}")
            self._status(f"{kind}: {message}", "error")

    def _on_canceled(self) -> None:
        """Report a cooperative cancellation."""
        self._status("Attack task cancelled", "warning")

    def _status(self, message: str, kind: str = "info") -> None:
        """Publish a status line for the view."""
        self.status_message.emit(message, kind)
