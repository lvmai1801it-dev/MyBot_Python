"""Village / upgrade feature view-model."""

from __future__ import annotations

from PyQt5.QtCore import QThread, pyqtSignal

from COCbot.core.config.schema import PriorityUpgradeConfig, UpgradeConfig
from COCbot.core.errors import StorageError
from COCbot.features.village.model import VillageModel, VillageSnapshot
from COCbot.features.village.planner import UpgradePlan, plan_upgrades
from COCbot.models.enums import UpgradeCategory
from COCbot.viewmodels.base_viewmodel import BaseViewModel

PRIORITY_CATEGORIES = (
    UpgradeCategory.BUILDINGS,
    UpgradeCategory.ARMY,
    UpgradeCategory.EQUIPMENT,
    UpgradeCategory.PETS,
)


class UpgradeScanWorker(QThread):
    """Read the in-game upgrade panel off the GUI thread."""

    scanned = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, model: VillageModel, parent=None) -> None:
        """Create the worker for *model*."""
        super().__init__(parent)
        self._model = model

    def run(self) -> None:
        """Open the panel, read all four tabs, close it."""
        try:
            scanned = self._model.scan_panel()
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")
            return
        self.scanned.emit(scanned)


class VillageViewModel(BaseViewModel):
    """Own a draft of the upgrade configuration and persist it explicitly."""

    loaded = pyqtSignal(object)
    saved = pyqtSignal(object)
    dirty_changed = pyqtSignal(bool)
    status_message = pyqtSignal(str, str)
    targets_scanned = pyqtSignal(object)
    scan_started = pyqtSignal()
    scan_finished = pyqtSignal()

    def __init__(self, model: VillageModel, parent=None) -> None:
        """Create the view-model around a village model."""
        super().__init__(parent)
        self._model = model
        self._saved = UpgradeConfig()
        self._draft = UpgradeConfig()
        self._dirty = False
        self._scan_worker: UpgradeScanWorker | None = None

    @property
    def is_scanning(self) -> bool:
        """Return ``True`` while the panel scan is running."""
        return self._scan_worker is not None and self._scan_worker.isRunning()

    def scan_targets(self) -> bool:
        """Start reading the in-game upgrade panel; return ``False`` if busy."""
        if self.is_scanning:
            return False
        worker = UpgradeScanWorker(self._model, parent=self)
        worker.scanned.connect(self._on_scanned)
        worker.failed.connect(self._on_scan_failed)
        worker.finished.connect(self._on_scan_done)
        self._scan_worker = worker
        self.scan_started.emit()
        self._status("Reading the in-game upgrade panel…", "info")
        worker.start()
        return True

    def _on_scanned(self, names: object) -> None:
        """Relay the scanned rows per Build tab."""
        if isinstance(names, dict):
            payload = {
                str(tab): tuple(str(name) for name in (values or ()))
                for tab, values in names.items()
            }
        else:
            payload = {}
        total = sum(len(values) for values in payload.values())
        if not total:
            self._status("No upgrade rows found — open the village first", "warning")
            return
        self.targets_scanned.emit(payload)
        self._status(f"{total} upgrade rows detected", "success")

    def _on_scan_failed(self, message: str) -> None:
        """Report a failed scan."""
        self._report_error(f"Upgrade scan failed: {message}")

    def _on_scan_done(self) -> None:
        """Clear the worker reference when the thread exits."""
        self._scan_worker = None
        self.scan_finished.emit()

    @property
    def config(self) -> UpgradeConfig:
        """Return the current draft."""
        return self._draft

    @property
    def is_dirty(self) -> bool:
        """Return ``True`` when the draft differs from disk."""
        return self._dirty

    def _status(self, message: str, kind: str = "info") -> None:
        """Publish a status line."""
        self.status_message.emit(message, kind)

    def _set_draft(self, upgrades: UpgradeConfig) -> None:
        """Replace the draft and emit a dirty transition."""
        self._draft = upgrades
        dirty = upgrades != self._saved
        if dirty != self._dirty:
            self._dirty = dirty
            self.dirty_changed.emit(dirty)

    def load(self) -> None:
        """Load the persisted upgrade configuration."""
        with self.busy():
            try:
                snapshot: VillageSnapshot = self._model.load()
            except Exception as exc:
                self._report_error(f"Could not load village config: {exc}")
                return
        self._saved = snapshot.upgrades
        self._draft = snapshot.upgrades
        self._dirty = False
        self.loaded.emit(snapshot.upgrades)
        self.dirty_changed.emit(False)
        self._status("Village configuration loaded", "info")

    def save(self) -> bool:
        """Persist the current upgrade draft."""
        with self.busy():
            try:
                self._model.save(self._draft)
            except StorageError as exc:
                self._report_error(str(exc))
                return False
            except Exception as exc:
                self._report_error(f"Unexpected save error: {exc}")
                return False
        self._saved = self._draft
        if self._dirty:
            self._dirty = False
            self.dirty_changed.emit(False)
        self.saved.emit(self._draft)
        self._status("Village configuration saved", "success")
        return True

    def reset_defaults(self) -> None:
        """Load default upgrade settings into the draft."""
        self._set_draft(self._model.reset_defaults())
        self._status("Defaults loaded — press Save to apply", "warning")

    def set_wall(
        self,
        enabled: bool,
        level: int,
        gold_threshold: int,
        elixir_threshold: int,
    ) -> None:
        """Update wall upgrade settings."""
        self._set_draft(
            self._model.set_wall(
                self._draft,
                enabled,
                level,
                gold_threshold,
                elixir_threshold,
            )
        )

    def set_priority(
        self,
        category: UpgradeCategory,
        enabled: bool,
        priorities: list[str],
        priority: bool | None = None,
    ) -> None:
        """Update one priority group."""
        self._set_draft(
            self._model.set_priority(
                self._draft, category, enabled, priorities, priority
            )
        )

    def set_priority_flag(self, category: UpgradeCategory, priority: bool) -> None:
        """Update only the priority flag of one group."""
        self._set_draft(
            self._model.set_priority_flag(self._draft, category, priority)
        )

    def priority_group(self, category: UpgradeCategory) -> PriorityUpgradeConfig:
        """Return the draft group for *category*."""
        mapping = {
            UpgradeCategory.BUILDINGS: self._draft.buildings,
            UpgradeCategory.ARMY: self._draft.army,
            UpgradeCategory.EQUIPMENT: self._draft.equipment,
            UpgradeCategory.PETS: self._draft.pets,
            UpgradeCategory.HERO: self._draft.hero,
            UpgradeCategory.DEFENSE: self._draft.defense,
            UpgradeCategory.RESOURCE: self._draft.resource,
            UpgradeCategory.OTHER: self._draft.other,
        }
        return mapping.get(category, PriorityUpgradeConfig())

    def upgrade_plan(self, builders_available: int) -> UpgradePlan:
        """Return the draft upgrade queue, walls reserving one builder."""
        return plan_upgrades(self._draft, builders_available)

    def shutdown(self, wait_ms: int = 3000) -> None:
        """Stop the panel scan thread on exit."""
        worker = self._scan_worker
        if worker is None:
            return
        if worker.isRunning() and not worker.wait(wait_ms):
            worker.terminate()
            worker.wait(1000)
        self._scan_worker = None
