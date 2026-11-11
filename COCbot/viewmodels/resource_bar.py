"""Resource bar view-model: poll the home-village counters off the GUI thread."""

from __future__ import annotations

from threading import Event

from PyQt5.QtCore import QThread, pyqtSignal

from COCbot.features.village.resources import ResourceReader, VillageResources
from COCbot.viewmodels.base_viewmodel import BaseViewModel

DEFAULT_REFRESH_SECONDS = 15.0


class ResourcePoller(QThread):
    """Background reader that refreshes on an interval or on demand."""

    updated = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        reader: ResourceReader,
        interval: float = DEFAULT_REFRESH_SECONDS,
        parent=None,
    ) -> None:
        """Create the poller around *reader*."""
        super().__init__(parent)
        self._reader = reader
        self._interval = max(2.0, float(interval))
        self._stop = Event()
        self._wake = Event()

    def request_refresh(self) -> None:
        """Read again as soon as possible."""
        self._wake.set()

    def stop(self) -> None:
        """Ask the loop to exit and wake it up."""
        self._stop.set()
        self._wake.set()

    def run(self) -> None:
        """Read one snapshot per interval until stopped."""
        while not self._stop.is_set():
            try:
                snapshot = self._reader.read()
            except Exception as exc:
                self.failed.emit(f"{type(exc).__name__}: {exc}")
            else:
                if snapshot.has_values():
                    self.updated.emit(snapshot)
            self._wake.wait(self._interval)
            self._wake.clear()


class ResourceBarViewModel(BaseViewModel):
    """Expose the latest village counters to the resource bar."""

    snapshot_updated = pyqtSignal(object)

    def __init__(
        self,
        reader: ResourceReader,
        interval: float = DEFAULT_REFRESH_SECONDS,
        parent=None,
    ) -> None:
        """Create the view-model around a resource reader."""
        super().__init__(parent)
        self._reader = reader
        self._interval = interval
        self._poller: ResourcePoller | None = None
        self._snapshot = VillageResources()

    @property
    def snapshot(self) -> VillageResources:
        """Return the last snapshot seen by the shell."""
        return self._snapshot

    def start(self) -> None:
        """Start polling when no poller is running."""
        if self._poller is not None and self._poller.isRunning():
            return
        poller = ResourcePoller(self._reader, interval=self._interval, parent=self)
        poller.updated.connect(self._on_updated)
        poller.failed.connect(self._on_failed)
        self._poller = poller
        poller.start()

    def stop(self, wait_ms: int = 3000) -> None:
        """Stop the poller and wait briefly for it to exit."""
        poller = self._poller
        if poller is None:
            return
        poller.stop()
        if poller.isRunning() and not poller.wait(wait_ms):
            poller.terminate()
            poller.wait(1000)
        self._poller = None

    def refresh_now(self) -> None:
        """Ask the poller for an immediate read."""
        if self._poller is not None and self._poller.isRunning():
            self._poller.request_refresh()
        else:
            self.start()

    def _on_updated(self, snapshot: object) -> None:
        """Store and relay one snapshot."""
        if not isinstance(snapshot, VillageResources):
            return
        self._snapshot = snapshot
        self.snapshot_updated.emit(snapshot)

    def _on_failed(self, message: str) -> None:
        """Keep the last values and report the failure quietly."""
        self._report_error(f"Resource readout: {message}")
