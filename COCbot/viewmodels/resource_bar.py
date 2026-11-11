"""Resource bar view-model: show what the farm loop read at home.

The bar is fed by the legacy engine: the bot checks the home village, zooms
out, and only then publishes the resource/builder readout. Nothing is polled
while the bot is stopped, so the bar stays empty until Start.
"""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal

from COCbot.features.village.resources import VillageResources
from COCbot.viewmodels.base_viewmodel import BaseViewModel


class ResourceBarViewModel(BaseViewModel):
    """Expose the latest village counters to the resource bar."""

    snapshot_updated = pyqtSignal(object)

    def __init__(self, parent=None) -> None:
        """Create an empty view-model."""
        super().__init__(parent)
        self._snapshot = VillageResources()

    @property
    def snapshot(self) -> VillageResources:
        """Return the last snapshot seen by the shell."""
        return self._snapshot

    def publish(self, snapshot: object) -> None:
        """Store and relay one snapshot.

        Called from the bot worker thread; the signal is delivered to the
        GUI thread by Qt's queued connections.
        """
        if not isinstance(snapshot, VillageResources):
            return
        self._snapshot = snapshot
        self.snapshot_updated.emit(snapshot)

    def clear(self) -> None:
        """Reset every cell to the empty placeholder."""
        self.publish(VillageResources())

    def on_running_changed(self, running: bool) -> None:
        """Clear stale counters when a new run starts."""
        if running:
            self.clear()
