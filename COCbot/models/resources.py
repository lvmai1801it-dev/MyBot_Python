"""Resource snapshots and capacity helpers."""

from __future__ import annotations

from dataclasses import dataclass

from COCbot.models.enums import ResourceKind


@dataclass(frozen=True)
class ResourceSnapshot:
    """Current loot and storage capacities for one village."""

    gold: int = 0
    elixir: int = 0
    dark_elixir: int = 0
    gold_capacity: int = 0
    elixir_capacity: int = 0
    dark_elixir_capacity: int = 0

    def amount(self, kind: ResourceKind) -> int:
        """Return the current amount for *kind*."""
        return {
            ResourceKind.GOLD: self.gold,
            ResourceKind.ELIXIR: self.elixir,
            ResourceKind.DARK_ELIXIR: self.dark_elixir,
        }[kind]

    def capacity(self, kind: ResourceKind) -> int:
        """Return the storage capacity for *kind* (0 means unknown)."""
        return {
            ResourceKind.GOLD: self.gold_capacity,
            ResourceKind.ELIXIR: self.elixir_capacity,
            ResourceKind.DARK_ELIXIR: self.dark_elixir_capacity,
        }[kind]

    def is_full(self, kind: ResourceKind, tolerance: float = 0.98) -> bool:
        """Return ``True`` when *kind* is at or above *tolerance* of capacity."""
        cap = self.capacity(kind)
        if cap <= 0:
            return False
        return (self.amount(kind) / cap) >= tolerance

    def fill_ratio(self, kind: ResourceKind) -> float:
        """Return the fill ratio in the ``0.0..1.0`` range (0 when unknown)."""
        cap = self.capacity(kind)
        if cap <= 0:
            return 0.0
        return min(1.0, max(0.0, self.amount(kind) / cap))

    def total(self) -> int:
        """Return the sum of all three resource amounts."""
        return self.gold + self.elixir + self.dark_elixir

    def as_dict(self) -> dict[str, int]:
        """Return a JSON-friendly representation."""
        return {
            "gold": self.gold,
            "elixir": self.elixir,
            "dark_elixir": self.dark_elixir,
            "gold_capacity": self.gold_capacity,
            "elixir_capacity": self.elixir_capacity,
            "dark_elixir_capacity": self.dark_elixir_capacity,
        }

    def loot_gain(self, before: "ResourceSnapshot") -> "ResourceSnapshot":
        """Return the non-negative loot difference between *before* and self."""
        return ResourceSnapshot(
            gold=max(0, self.gold - before.gold),
            elixir=max(0, self.elixir - before.elixir),
            dark_elixir=max(0, self.dark_elixir - before.dark_elixir),
        )
