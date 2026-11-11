"""Upgrade ordering with hero/money priority and a wall builder reserve.

Rules requested by the operator:

* the Village tab mirrors the in-game Build panel: Buildings & Heroes, Army
  Upgrades, Hero Equipment and Hero Pets;
* inside Buildings & Heroes, heroes and resource ("money") buildings can be
  flagged as priority, so they are attempted before defense/other buildings;
* when wall upgrading is enabled, one builder must stay free for walls, so the
  queue may only consume ``builders - 1`` slots.
"""

from __future__ import annotations

from dataclasses import dataclass

from COCbot.core.config.schema import PriorityUpgradeConfig, UpgradeConfig
from COCbot.features.village.targets import category_for
from COCbot.models.enums import UpgradeCategory

# Stable order of the four Build-panel tabs.
TAB_ORDER: tuple[str, ...] = ("buildings", "army", "equipment", "pets")

_FIELD_BY_TAB = {
    "buildings": "buildings",
    "army": "army",
    "equipment": "equipment",
    "pets": "pets",
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


def _group(config: UpgradeConfig, tab: str) -> PriorityUpgradeConfig:
    """Return the config group for *tab*."""
    return getattr(config, _FIELD_BY_TAB[tab])


def _building_items(config: UpgradeConfig) -> list[tuple[int, str, str]]:
    """Return ``(index, name, kind)`` for every Buildings & Heroes target."""
    items: list[tuple[int, str, str]] = []
    for index, name in enumerate(config.buildings.priorities):
        category = category_for(name)
        if category == UpgradeCategory.HERO:
            kind = "hero"
        elif category == UpgradeCategory.RESOURCE:
            kind = "money"
        else:
            kind = "other"
        items.append((index, name, kind))
    return items


def ordered_targets(config: UpgradeConfig) -> tuple[str, ...]:
    """Return enabled targets with priority items first, in stable order."""
    ranked: list[tuple[int, int, int, str]] = []
    for tab_index, tab in enumerate(TAB_ORDER):
        group = _group(config, tab)
        if not group.enabled:
            continue
        if tab == "buildings":
            for index, name, kind in _building_items(config):
                promoted = group.priority
                if kind == "hero":
                    promoted = promoted or config.hero.priority
                elif kind == "money":
                    promoted = promoted or config.resource.priority
                ranked.append((0 if promoted else 1, tab_index, index, name))
        else:
            flag = 0 if group.priority else 1
            for index, name in enumerate(group.priorities):
                ranked.append((flag, tab_index, index, name))

    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    names: list[str] = []
    seen: set[str] = set()
    for _flag, _tab, _index, name in ranked:
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
