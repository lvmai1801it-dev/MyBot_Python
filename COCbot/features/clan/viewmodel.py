"""Clan feature view-model."""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal

from COCbot.core.config.schema import ClanConfig
from COCbot.core.errors import StorageError
from COCbot.features.clan.model import ClanModel, ClanSnapshot
from COCbot.viewmodels.base_viewmodel import BaseViewModel


class ClanViewModel(BaseViewModel):
    """Own a clan-config draft and persist it explicitly."""

    loaded = pyqtSignal(object)
    saved = pyqtSignal(object)
    dirty_changed = pyqtSignal(bool)
    status_message = pyqtSignal(str, str)

    def __init__(self, model: ClanModel, parent=None) -> None:
        """Create the view-model around a clan model."""
        super().__init__(parent)
        self._model = model
        self._saved = ClanConfig()
        self._draft = ClanConfig()
        self._dirty = False

    @property
    def config(self) -> ClanConfig:
        """Return the current draft."""
        return self._draft

    @property
    def is_dirty(self) -> bool:
        """Return ``True`` when the draft differs from disk."""
        return self._dirty

    def _status(self, message: str, kind: str = "info") -> None:
        """Publish a status line."""
        self.status_message.emit(message, kind)

    def _set_draft(self, config: ClanConfig) -> None:
        """Replace the draft and emit a dirty transition."""
        self._draft = config
        dirty = config != self._saved
        if dirty != self._dirty:
            self._dirty = dirty
            self.dirty_changed.emit(dirty)

    def load(self) -> None:
        """Load clan configuration."""
        with self.busy():
            try:
                snapshot: ClanSnapshot = self._model.load()
            except Exception as exc:
                self._report_error(f"Could not load clan config: {exc}")
                return
        self._saved = snapshot.config
        self._draft = snapshot.config
        self._dirty = False
        self.loaded.emit(snapshot.config)
        self.dirty_changed.emit(False)
        self._status("Clan configuration loaded", "info")

    def save(self) -> bool:
        """Persist the current clan draft."""
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
        self._status("Clan configuration saved", "success")
        return True

    def reset_defaults(self) -> None:
        """Load default clan settings into the draft."""
        self._set_draft(self._model.reset_defaults())
        self._status("Defaults loaded — press Save to apply", "warning")

    def set_options(
        self,
        games: bool,
        capital: bool,
        capital_level: int,
        request_troops: bool,
    ) -> None:
        """Update all clan options from the form."""
        self._set_draft(
            self._model.build(games, capital, capital_level, request_troops)
        )
