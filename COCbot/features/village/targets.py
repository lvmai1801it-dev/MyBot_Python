"""Known home-village upgrade targets grouped by Village-tab category.

The game lists upgrades in the *Buildings & Heroes* panel. The panel is read
with OCR, so names can come back with small slips (``Elixir Catlector``,
``MonolitH``). This module maps them onto a canonical name and a category so
the Village tab can offer a checkbox list instead of free text.
"""

from __future__ import annotations

import difflib
import re

from COCbot.models.enums import UpgradeCategory

HEROES: tuple[str, ...] = (
    "Barbarian King",
    "Archer Queen",
    "Grand Warden",
    "Royal Champion",
    "Dragon Duke",
    "Minion Prince",
)

DEFENSES: tuple[str, ...] = (
    "Cannon",
    "Archer Tower",
    "Mortar",
    "Air Defense",
    "Wizard Tower",
    "Super Wizard Tower",
    "Air Sweeper",
    "Hidden Tesla",
    "Bomb Tower",
    "X-Bow",
    "Inferno Tower",
    "Eagle Artillery",
    "Scattershot",
    "Monolith",
    "Revenge Tower",
    "Spell Tower",
    "Multi-Archer Tower",
    "Multi-Cannon",
    "Ricochet Cannon",
    "Firespitter",
    "Multi-Gear Tower",
    "Giga Inferno",
    "Giga Tesla",
    "Spring Trap",
    "Air Bomb",
    "Giant Bomb",
    "Seeking Air Mine",
    "Skeleton Trap",
    "Tornado Trap",
)

SPELLS: tuple[str, ...] = (
    "Lightning Spell",
    "Healing Spell",
    "Rage Spell",
    "Jump Spell",
    "Freeze Spell",
    "Clone Spell",
    "Poison Spell",
    "Earthquake Spell",
    "Haste Spell",
    "Skeleton Spell",
    "Bat Spell",
    "Invisibility Spell",
    "Recall Spell",
    "Revive Spell",
    "Overgrowth Spell",
    "Ice Block Spell",
    "Totem Spell",
    "Angry Spell",
)

RESOURCES: tuple[str, ...] = (
    "Gold Mine",
    "Elixir Collector",
    "Gold Storage",
    "Elixir Storage",
    "Dark Elixir Drill",
    "Dark Elixir Storage",
    "Gem Mine",
)

ARMY: tuple[str, ...] = (
    "Army Camp",
    "Barracks",
    "Dark Barracks",
    "Laboratory",
    "Spell Factory",
    "Dark Spell Factory",
    "Workshop",
    "Siege Workshop",
    "Blacksmith",
    "Pet House",
)

OTHER: tuple[str, ...] = (
    "Hero Hall",
    "Clan Castle",
    "Builder's Hut",
    "Crafting Station",
)

EQUIPMENT: tuple[str, ...] = (
    "Giant Gauntlet",
    "Rage Vial",
    "Earthquake Boots",
    "Vampstache",
    "Barbarian Puppet",
    "Archer Puppet",
    "Giant Arrow",
    "Invisibility Vial",
    "Healer Puppet",
    "Eternal Tome",
    "Life Gem",
    "Seeking Shield",
    "Royal Gem",
    "Hog Rider Puppet",
    "Haste Vial",
    "Rocket Spear",
)

PETS: tuple[str, ...] = (
    "L.A.S.S.I",
    "Electro Owl",
    "Mighty Yak",
    "Unicorn",
    "Frosty",
    "Diggy",
    "Poison Lizard",
    "Phoenix",
    "Spirit Fox",
    "Angry Jelly",
    "Sneezy",
    "Greedy Raven",
)

CATALOG: tuple[tuple[str, UpgradeCategory], ...] = (
    *((name, UpgradeCategory.HERO) for name in HEROES),
    *((name, UpgradeCategory.DEFENSE) for name in DEFENSES),
    *((name, UpgradeCategory.RESOURCE) for name in RESOURCES),
    *((name, UpgradeCategory.ARMY) for name in ARMY),
    *((name, UpgradeCategory.ARMY) for name in SPELLS),
    *((name, UpgradeCategory.OTHER) for name in OTHER),
    *((name, UpgradeCategory.EQUIPMENT) for name in EQUIPMENT),
    *((name, UpgradeCategory.PETS) for name in PETS),
)

FUZZY_THRESHOLD = 0.82

_HERO_KEYS = ("king", "queen", "warden", "champion", "prince", "duke")
_RESOURCE_KEYS = ("mine", "collector", "storage", "drill", "gem")
_ARMY_KEYS = (
    "camp",
    "barracks",
    "laboratory",
    "lab",
    "factory",
    "workshop",
    "smith",
    "pet",
)
_DEFENSE_KEYS = (
    "cannon",
    "tower",
    "mortar",
    "tesla",
    "xbow",
    "inferno",
    "eagle",
    "scattershot",
    "monolith",
    "sweeper",
    "artillery",
    "spitter",
    "defense",
)


def normalize(text: str) -> str:
    """Return lowercase alphanumerics only."""
    return "".join(ch for ch in str(text).lower() if ch.isalnum())


_BUNDLE_RE = re.compile(r"\s*x\s*\d+\s*$", re.IGNORECASE)


def strip_bundle(text: str) -> str:
    """Drop a trailing bundle count such as ``x 4`` from a row label."""
    return _BUNDLE_RE.sub("", str(text).strip())


def canonical_name(name: str) -> str | None:
    """Return the catalog name closest to *name* (``None`` when unknown)."""
    target = normalize(strip_bundle(name))
    if not target:
        return None
    best: str | None = None
    best_score = 0.0
    for catalog_name, _category in CATALOG:
        key = normalize(catalog_name)
        if target == key:
            return catalog_name
        if key in target or target in key:
            score = 0.95
        else:
            score = difflib.SequenceMatcher(None, target, key).ratio()
        if score > best_score:
            best, best_score = catalog_name, score
    return best if best_score >= FUZZY_THRESHOLD else None


def category_for(name: str) -> UpgradeCategory:
    """Classify *name* into one of the Village-tab upgrade groups."""
    canonical = canonical_name(name)
    if canonical is not None:
        for catalog_name, category in CATALOG:
            if catalog_name == canonical:
                return category
    lowered = normalize(name)
    if any(key in lowered for key in _HERO_KEYS):
        return UpgradeCategory.HERO
    if any(key in lowered for key in _RESOURCE_KEYS):
        return UpgradeCategory.RESOURCE
    if any(key in lowered for key in _ARMY_KEYS):
        return UpgradeCategory.ARMY
    if any(key in lowered for key in _DEFENSE_KEYS):
        return UpgradeCategory.DEFENSE
    return UpgradeCategory.OTHER


def group_targets(names: object) -> dict[UpgradeCategory, list[str]]:
    """Group OCR row names into the Village-tab categories, without duplicates."""
    groups: dict[UpgradeCategory, list[str]] = {
        UpgradeCategory.HERO: [],
        UpgradeCategory.DEFENSE: [],
        UpgradeCategory.ARMY: [],
        UpgradeCategory.RESOURCE: [],
        UpgradeCategory.OTHER: [],
    }
    seen: set[str] = set()
    for raw in names or ():
        text = str(raw).strip()
        if not text:
            continue
        name = canonical_name(text) or strip_bundle(text)
        key = normalize(name)
        if not key or key in seen:
            continue
        seen.add(key)
        groups[category_for(name)].append(name)
    for values in groups.values():
        values.sort(key=str.lower)
    return groups
