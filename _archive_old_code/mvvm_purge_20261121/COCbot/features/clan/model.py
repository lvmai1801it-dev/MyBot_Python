"""Clan feature domain model: Clan Games, Capital, and donations."""

from __future__ import annotations

from dataclasses import dataclass, replace

from COCbot.core.config.schema import AppConfig, ClanConfig
from COCbot.core.config.store import ConfigStore
from COCbot.core.ports import SettingsPort


@dataclass(frozen=True)
class ClanSnapshot:
    """Clan-related configuration shown in the Clan tab."""

    config: ClanConfig


class ClanModel:
    """Load and persist the Clan Games / Capital / donate settings."""

    def __init__(self, store: ConfigStore, settings: SettingsPort) -> None:
        """Share the live config and settings persistence."""
        self._store = store
        self._settings = settings

    def load(self) -> ClanSnapshot:
        """Return the current clan configuration."""
        return ClanSnapshot(config=self._store.get().clan)

    def save(self, config: ClanConfig) -> ClanSnapshot:
        """Persist *config* and update the live store."""
        app_config = replace(self._store.get(), clan=config)
        self._settings.save(app_config)
        self._store.set(app_config)
        return ClanSnapshot(config=app_config.clan)

    def reset_defaults(self) -> ClanConfig:
        """Return the default clan configuration."""
        return AppConfig().clan

    @staticmethod
    def build(
        games: bool,
        capital: bool,
        capital_level: int,
        request_troops: bool,
    ) -> ClanConfig:
        """Build a clan config from the form values."""
        return ClanConfig(
            enable_clan_games=bool(games),
            enable_clan_capital=bool(capital),
            capital_hall_level=max(1, int(capital_level)),
            request_troops=bool(request_troops),
        )
