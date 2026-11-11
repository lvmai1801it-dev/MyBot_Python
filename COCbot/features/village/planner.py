"""Upgrade ordering with per-tab capacity and a wall builder reserve.

Rules requested by the operator:

* the Village tab mirrors the in-game Build panel: Buildings & Heroes, Army
  Upgrades, Hero Equipment and Hero Pets;
* Buildings & Heroes may use every free builder, minus one kept back for walls
  when wall upgrading is enabled, and each chosen target is upgraded until it
  leaves the panel (maxed);
* Army Upgrades and Hero Pets may run exactly one upgrade at a time;
* hero and resource ("money") buildings can be flagged as priority.
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

# Army, equipment and pet upgrades run one at a time.
SINGLE_SLOT_TABS = ("army", "equipment", "pets")


@dataclass(frozen=True)
class UpgradePlan:
    """Ordered upgrade queue plus the capacities that produced it."""

    order: tuple[str, ...]
    skipped: tuple[str, ...]
    builders_available: int
    reserved_for_walls: int
    budget: int
    wall_reserved: bool
    single_slot: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        """Return ``True`` when the plan contains at least one upgrade."""
        return bool(self.order)


def _group(config: UpgradeConfig, tab: str) -> PriorityUpgradeConfig:
    """Return the config group for *tab*."""
    return getattr(config, _FIELD_BY_TAB[tab])


def _active(group: PriorityUpgradeConfig) -> bool:
    """A tab runs when it is enabled or has ticked targets."""
    return bool(group.enabled or group.priorities)


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


def _building_names(config: UpgradeConfig) -> list[str]:
    """Buildings & Heroes targets, hero/money priorities first."""
    group = config.buildings
    items: list[tuple[int, int, str]] = []
    for index, name, kind in _building_items(config):
        promoted = group.priority
        if kind == "hero":
            promoted = promoted or config.hero.priority
        elif kind == "money":
            promoted = promoted or config.resource.priority
        items.append((0 if promoted else 1, index, name))
    items.sort(key=lambda item: (item[0], item[1]))
    return [name for _flag, _index, name in items]


def ordered_targets(config: UpgradeConfig) -> tuple[str, ...]:
    """Return enabled targets tab by tab, priority items first."""
    names: list[str] = []
    for tab in TAB_ORDER:
        group = _group(config, tab)
        if not _active(group):
            continue
        if tab == "buildings":
            names.extend(_building_names(config))
        else:
            names.extend(name.strip() for name in group.priorities if name.strip())
    seen: set[str] = set()
    unique: list[str] = []
    for name in names:
        key = name.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(name.strip())
    return tuple(unique)


def plan_upgrades(config: UpgradeConfig, builders_available: int) -> UpgradePlan:
    """Build the upgrade queue, keeping one builder back for walls."""
    builders = max(0, int(builders_available))
    wall_reserved = bool(config.wall.enabled)
    reserved = 1 if wall_reserved and builders > 0 else 0
    building_budget = max(0, builders - reserved)

    selected: list[str] = []
    skipped: list[str] = []
    single_slot: list[str] = []
    for tab in TAB_ORDER:
        group = _group(config, tab)
        if not _active(group):
            continue
        if tab == "buildings":
            tab_names = _building_names(config)
        else:
            tab_names = [name.strip() for name in group.priorities if name.strip()]
        if not tab_names:
            continue
        limit = building_budget if tab == "buildings" else 1
        chosen = tab_names[:limit]
        selected.extend(chosen)
        skipped.extend(tab_names[limit:])
        if tab in SINGLE_SLOT_TABS:
            single_slot.extend(chosen)

    return UpgradePlan(
        order=tuple(selected),
        skipped=tuple(skipped),
        builders_available=builders,
        reserved_for_walls=reserved,
        budget=building_budget,
        wall_reserved=wall_reserved,
        single_slot=tuple(single_slot),
    )


def _tab_of(name: str) -> str:
    """Return the Build tab a target belongs to."""
    category = category_for(name)
    if category == UpgradeCategory.ARMY:
        return "army"
    if category == UpgradeCategory.EQUIPMENT:
        return "equipment"
    if category == UpgradeCategory.PETS:
        return "pets"
    return "buildings"
