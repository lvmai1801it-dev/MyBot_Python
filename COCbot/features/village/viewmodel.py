"""Village / upgrade feature view-model."""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal

from COCbot.core.config.schema import PriorityUpgradeConfig, UpgradeConfig
from COCbot.core.errors import StorageError
from COCbot.features.village.model import VillageModel, VillageSnapshot
from COCbot.models.enums import UpgradeCategory
from COCbot.viewmodels.base_viewmodel import BaseViewModel

PRIORITY_CATEGORIES = (
    UpgradeCategory.HERO,
    UpgradeCategory.DEFENSE,
    UpgradeCategory.ARMY,
    UpgradeCategory.RESOURCE,
    UpgradeCategory.OTHER,
)


class VillageViewModel(BaseViewModel):
    """Own a draft of the upgrade configuration and persist it explicitly."""

    loaded = pyqtSignal(object)
    saved = pyqtSignal(object)
    dirty_changed = pyqtSignal(bool)
    status_message = pyqtSignal(str, str)

    def __init__(self, model: VillageModel, parent=None) -> None:
        """Create the view-model around a village model."""
        super().__init__(parent)
        self._model = model
        self._saved = UpgradeConfig()
        self._draft = UpgradeConfig()
        self._dirty = False

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
    ) -> None:
        """Update one priority group."""
        self._set_draft(
            self._model.set_priority(self._draft, category, enabled, priorities)
        )

    def priority_group(self, category: UpgradeCategory) -> PriorityUpgradeConfig:
        """Return the draft group for *category*."""
        mapping = {
            UpgradeCategory.HERO: self._draft.hero,
            UpgradeCategory.DEFENSE: self._draft.defense,
            UpgradeCategory.ARMY: self._draft.army,
            UpgradeCategory.RESOURCE: self._draft.resource,
            UpgradeCategory.OTHER: self._draft.other,
        }
        return mapping.get(category, PriorityUpgradeConfig())
