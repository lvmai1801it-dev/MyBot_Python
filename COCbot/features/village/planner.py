"""Upgrade ordering with hero/resource priority and a wall builder reserve.

Rules requested by the operator:

* hero and resource ("money") groups can be flagged as priority, so their
  upgrades are attempted before defense/army/other buildings;
* when wall upgrading is enabled, one builder must stay free for walls, so the
  building/hero queue may only consume ``builders - 1`` slots.
"""

from __future__ import annotations

from dataclasses import dataclass

from COCbot.core.config.schema import PriorityUpgradeConfig, UpgradeConfig
from COCbot.models.enums import UpgradeCategory

# Stable order used when two groups share the same priority flag.
CATEGORY_ORDER: tuple[UpgradeCategory, ...] = (
    UpgradeCategory.HERO,
    UpgradeCategory.RESOURCE,
    UpgradeCategory.DEFENSE,
    UpgradeCategory.ARMY,
    UpgradeCategory.OTHER,
)

_FIELD_BY_CATEGORY = {
    UpgradeCategory.HERO: "hero",
    UpgradeCategory.RESOURCE: "resource",
    UpgradeCategory.DEFENSE: "defense",
    UpgradeCategory.ARMY: "army",
    UpgradeCategory.OTHER: "other",
}


@dataclass(frozen=True)
class UpgradePlan:
    """Ordered upgrade queue plus the builder budget that produced it."""

    order: tuple[str, ...]
    skipped: tuple[str, ...]
    builders_available: int
    reserved_for_walls: int
    budget: int
    wall_reserved: bool

    def __bool__(self) -> bool:
        """Return ``True`` when the plan contains at least one upgrade."""
        return bool(self.order)


def _group(config: UpgradeConfig, category: UpgradeCategory) -> PriorityUpgradeConfig:
    """Return the config group for *category*."""
    return getattr(config, _FIELD_BY_CATEGORY[category])


def ordered_targets(config: UpgradeConfig) -> tuple[str, ...]:
    """Return enabled targets with priority groups first, in stable order."""
    enabled = [
        (category, _group(config, category))
        for category in CATEGORY_ORDER
        if _group(config, category).enabled
    ]
    ordered = sorted(
        enabled,
        key=lambda item: (
            0 if item[1].priority else 1,
            CATEGORY_ORDER.index(item[0]),
        ),
    )
    names: list[str] = []
    seen: set[str] = set()
    for _category, group in ordered:
        for name in group.priorities:
            key = name.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            names.append(name.strip())
    return tuple(names)


def plan_upgrades(config: UpgradeConfig, builders_available: int) -> UpgradePlan:
    """Build the upgrade queue, keeping one builder back for walls."""
    builders = max(0, int(builders_available))
    wall_reserved = bool(config.wall.enabled)
    reserved = 1 if wall_reserved and builders > 0 else 0
    budget = max(0, builders - reserved)
    targets = ordered_targets(config)
    return UpgradePlan(
        order=targets[:budget],
        skipped=targets[budget:],
        builders_available=builders,
        reserved_for_walls=reserved,
        budget=budget,
        wall_reserved=wall_reserved,
    )
