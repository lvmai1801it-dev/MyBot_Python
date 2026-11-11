"""Settings feature view-model (QObject + signals only)."""

from __future__ import annotations

from dataclasses import replace

from PyQt5.QtCore import pyqtSignal

from COCbot.core.config.schema import (
    AppConfig,
    EmulatorConfig,
    LoggingConfig,
    ResourceThresholds,
    WallUpgradeConfig,
)
from COCbot.core.errors import StorageError
from COCbot.features.settings.model import SettingsModel
from COCbot.models.enums import EmulatorType
from COCbot.viewmodels.base_viewmodel import BaseViewModel


class SettingsViewModel(BaseViewModel):
    """Own a settings draft and publish load/save state to the view."""

    loaded = pyqtSignal(object)
    saved = pyqtSignal(object)
    dirty_changed = pyqtSignal(bool)
    status_message = pyqtSignal(str, str)

    def __init__(self, model: SettingsModel, parent=None) -> None:
        """Create the view-model around a settings model."""
        super().__init__(parent)
        self._model = model
        self._saved = AppConfig()
        self._draft = AppConfig()
        self._dirty = False

    @property
    def config(self) -> AppConfig:
        """Return the current draft configuration."""
        return self._draft

    @property
    def is_dirty(self) -> bool:
        """Return ``True`` when the draft differs from the saved config."""
        return self._dirty

    def _status(self, message: str, kind: str = "info") -> None:
        """Publish a status line for the view."""
        self.status_message.emit(message, kind)

    def _set_draft(self, config: AppConfig) -> None:
        """Replace the draft and emit ``dirty_changed`` only on transitions."""
        self._draft = config
        dirty = config != self._saved
        if dirty != self._dirty:
            self._dirty = dirty
            self.dirty_changed.emit(dirty)

    def load(self) -> None:
        """Load settings from disk and publish them."""
        with self.busy():
            try:
                config = self._model.load()
            except Exception as exc:
                self._report_error(f"Could not load settings: {exc}")
                return
        self._saved = config
        self._dirty = False
        self._draft = config
        self.loaded.emit(config)
        self.dirty_changed.emit(False)
        self._status("Settings loaded", "info")

    def reload(self) -> None:
        """Discard the draft and reload from disk."""
        self.load()

    def save(self) -> bool:
        """Persist the draft; return ``True`` on success."""
        if not self._draft.attack.name.strip():
            self._report_error("Attack name cannot be empty")
            return False
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
        self._status("Settings saved", "success")
        return True

    def reset_defaults(self) -> None:
        """Load defaults into the draft without writing them yet."""
        self._set_draft(self._model.reset())
        self._status("Defaults loaded — press Save to apply", "warning")

    def set_resources(self, gold: int, elixir: int, dark_elixir: int) -> None:
        """Update loot thresholds."""
        self._set_draft(
            replace(
                self._draft,
                resources=ResourceThresholds(
                    gold=max(0, int(gold)),
                    elixir=max(0, int(elixir)),
                    dark_elixir=max(0, int(dark_elixir)),
                ),
            )
        )

    def set_wall_upgrade(
        self,
        enabled: bool,
        level: int,
        gold_threshold: int,
        elixir_threshold: int,
    ) -> None:
        """Update wall upgrade settings."""
        wall = WallUpgradeConfig(
            enabled=bool(enabled),
            level=max(1, int(level)),
            gold_threshold=max(0, int(gold_threshold)),
            elixir_threshold=max(0, int(elixir_threshold)),
        )
        self._set_draft(
            replace(
                self._draft,
                upgrades=replace(self._draft.upgrades, wall=wall),
            )
        )

    def set_attack(self, name: str, side: str) -> None:
        """Update the default attack strategy and side."""
        self._set_draft(
            replace(
                self._draft,
                attack=replace(
                    self._draft.attack,
                    name=name.strip(),
                    side=side.strip() or "Ngẫu nhiên",
                ),
            )
        )

    def set_clan(
        self,
        clan_games: bool,
        clan_capital: bool,
        capital_level: int,
        request_troops: bool,
    ) -> None:
        """Update Clan Games / Capital / donation settings."""
        self._set_draft(
            replace(
                self._draft,
                clan=replace(
                    self._draft.clan,
                    enable_clan_games=bool(clan_games),
                    enable_clan_capital=bool(clan_capital),
                    capital_hall_level=max(1, int(capital_level)),
                    request_troops=bool(request_troops),
                ),
            )
        )

    def set_emulator(self, emulator_type: EmulatorType | str, host: str) -> None:
        """Update emulator selection and ADB host."""
        normalized = EmulatorType.from_value(emulator_type)
        emulator = EmulatorConfig(
            emulator_type=normalized,
            host=host.strip(),
        )
        self._set_draft(replace(self._draft, emulator=emulator))

    def set_logging(self, level: str, file_enabled: bool) -> None:
        """Update logging level and file output toggle."""
        logging = LoggingConfig(
            level=level.strip().upper() or "INFO",
            file_enabled=bool(file_enabled),
            file_path=self._draft.logging.file_path,
            max_bytes=self._draft.logging.max_bytes,
            backup_count=self._draft.logging.backup_count,
        )
        self._set_draft(replace(self._draft, logging=logging))

    def set_stats(self, enabled: bool) -> None:
        """Enable or disable statistics collection."""
        self._set_draft(replace(self._draft, enable_stats=bool(enabled)))
