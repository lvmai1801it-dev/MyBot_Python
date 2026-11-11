"""Village / upgrade feature domain model (pure Python, no Qt)."""

from __future__ import annotations

from dataclasses import dataclass, replace

from COCbot.core.config.schema import (
    AppConfig,
    PriorityUpgradeConfig,
    UpgradeConfig,
    WallUpgradeConfig,
)
from COCbot.core.config.store import ConfigStore
from COCbot.core.ports import SettingsPort
from COCbot.models.enums import UpgradeCategory


@dataclass(frozen=True)
class VillageSnapshot:
    """The upgrade configuration shown in the Village tab."""

    upgrades: UpgradeConfig


class VillageModel:
    """Load and persist the upgrade groups."""

    def __init__(self, store: ConfigStore, settings: SettingsPort) -> None:
        """Share the live config and the settings persistence port."""
        self._store = store
        self._settings = settings

    def load(self) -> VillageSnapshot:
        """Return the current upgrade configuration."""
        return VillageSnapshot(upgrades=self._store.get().upgrades)

    def save(self, upgrades: UpgradeConfig) -> VillageSnapshot:
        """Persist *upgrades* and update the live config."""
        config = replace(self._store.get(), upgrades=upgrades)
        self._settings.save(config)
        self._store.set(config)
        return VillageSnapshot(upgrades=config.upgrades)

    def reset_defaults(self) -> UpgradeConfig:
        """Return the default upgrade configuration."""
        return AppConfig().upgrades

    @staticmethod
    def set_wall(
        upgrades: UpgradeConfig,
        enabled: bool,
        level: int,
        gold_threshold: int,
        elixir_threshold: int,
    ) -> UpgradeConfig:
        """Return an upgrade config with wall settings replaced."""
        wall = WallUpgradeConfig(
            enabled=bool(enabled),
            level=max(1, int(level)),
            gold_threshold=max(0, int(gold_threshold)),
            elixir_threshold=max(0, int(elixir_threshold)),
        )
        return replace(upgrades, wall=wall)

    @staticmethod
    def set_priority(
        upgrades: UpgradeConfig,
        category: UpgradeCategory,
        enabled: bool,
        priorities: list[str],
    ) -> UpgradeConfig:
        """Return an upgrade config with one priority group replaced."""
        field_name = {
            UpgradeCategory.HERO: "hero",
            UpgradeCategory.DEFENSE: "defense",
            UpgradeCategory.ARMY: "army",
            UpgradeCategory.RESOURCE: "resource",
            UpgradeCategory.OTHER: "other",
        }.get(category)
        if field_name is None:
            return upgrades
        group = PriorityUpgradeConfig(
            enabled=bool(enabled),
            priorities=[item.strip() for item in priorities if item.strip()],
        )
        return replace(upgrades, **{field_name: group})
