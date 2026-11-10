"""Village state and upgrade task models."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from COCbot.models.enums import ResourceKind, UpgradeCategory
from COCbot.models.resources import ResourceSnapshot


@dataclass(frozen=True)
class VillageState:
    """A snapshot of the player's current village."""

    resources: ResourceSnapshot = field(default_factory=ResourceSnapshot)
    town_hall_level: int = 0
    builder_count: int = 0
    available_builders: int = 0
    laboratory_available: bool = False
    army_ready: bool = False
    shield_active: bool = False
    is_home_village: bool = True
    updated_at: float = field(default_factory=time.time)

    def has_free_builder(self) -> bool:
        """Return ``True`` when at least one builder is idle."""
        return self.available_builders > 0

    def with_resources(self, resources: ResourceSnapshot) -> "VillageState":
        """Return a copy with a refreshed resource snapshot."""
        return VillageState(
            resources=resources,
            town_hall_level=self.town_hall_level,
            builder_count=self.builder_count,
            available_builders=self.available_builders,
            laboratory_available=self.laboratory_available,
            army_ready=self.army_ready,
            shield_active=self.shield_active,
            is_home_village=self.is_home_village,
        )


@dataclass(frozen=True)
class UpgradeTask:
    """A single upgrade candidate selected by the upgrade feature."""

    name: str
    category: UpgradeCategory
    target_level: int = 0
    cost: int = 0
    resource: ResourceKind = ResourceKind.GOLD
    priority: int = 0

    def is_affordable(self, resources: ResourceSnapshot) -> bool:
        """Return ``True`` when the village can pay for this upgrade."""
        if self.cost <= 0:
            return True
        return resources.amount(self.resource) >= self.cost
