"""Unit tests for upgrade ordering, priority flags, and the wall reserve."""

from __future__ import annotations

import unittest

from COCbot.core.config.schema import (
    PriorityUpgradeConfig,
    UpgradeConfig,
    WallUpgradeConfig,
)
from COCbot.features.village.planner import ordered_targets, plan_upgrades


def config(
    *,
    hero: PriorityUpgradeConfig | None = None,
    resource: PriorityUpgradeConfig | None = None,
    defense: PriorityUpgradeConfig | None = None,
    army: PriorityUpgradeConfig | None = None,
    wall: WallUpgradeConfig | None = None,
) -> UpgradeConfig:
    """Build an upgrade config for the planner tests."""
    return UpgradeConfig(
        wall=wall or WallUpgradeConfig(),
        hero=hero or PriorityUpgradeConfig(),
        resource=resource or PriorityUpgradeConfig(),
        defense=defense or PriorityUpgradeConfig(),
        army=army or PriorityUpgradeConfig(),
    )


class PlannerTests(unittest.TestCase):
    """Verify priority ordering and the reserved wall builder."""

    def test_priority_groups_come_first(self) -> None:
        cfg = config(
            hero=PriorityUpgradeConfig(
                enabled=True,
                priorities=["Archer Queen"],
                priority=True,
            ),
            resource=PriorityUpgradeConfig(
                enabled=True,
                priorities=["Gold Mine"],
                priority=True,
            ),
            defense=PriorityUpgradeConfig(enabled=True, priorities=["Monolith"]),
        )
        self.assertEqual(
            ordered_targets(cfg),
            ("Archer Queen", "Gold Mine", "Monolith"),
        )

    def test_non_priority_keeps_stable_order(self) -> None:
        cfg = config(
            hero=PriorityUpgradeConfig(enabled=True, priorities=["Archer Queen"]),
            resource=PriorityUpgradeConfig(enabled=True, priorities=["Gold Mine"]),
        )
        self.assertEqual(ordered_targets(cfg), ("Archer Queen", "Gold Mine"))

    def test_disabled_groups_are_ignored(self) -> None:
        cfg = config(
            hero=PriorityUpgradeConfig(enabled=False, priorities=["Archer Queen"]),
            defense=PriorityUpgradeConfig(enabled=True, priorities=["Cannon"]),
        )
        self.assertEqual(ordered_targets(cfg), ("Cannon",))

    def test_wall_reserves_one_builder(self) -> None:
        cfg = config(
            wall=WallUpgradeConfig(enabled=True, level=12),
            hero=PriorityUpgradeConfig(
                enabled=True,
                priorities=["Archer Queen", "Grand Warden"],
                priority=True,
            ),
            defense=PriorityUpgradeConfig(enabled=True, priorities=["Monolith"]),
        )
        plan = plan_upgrades(cfg, builders_available=3)
        self.assertTrue(plan.wall_reserved)
        self.assertEqual(plan.reserved_for_walls, 1)
        self.assertEqual(plan.budget, 2)
        self.assertEqual(plan.order, ("Archer Queen", "Grand Warden"))
        self.assertEqual(plan.skipped, ("Monolith",))

    def test_without_walls_all_builders_are_usable(self) -> None:
        cfg = config(
            hero=PriorityUpgradeConfig(
                enabled=True,
                priorities=["Archer Queen", "Grand Warden"],
            ),
            defense=PriorityUpgradeConfig(enabled=True, priorities=["Monolith"]),
        )
        plan = plan_upgrades(cfg, builders_available=3)
        self.assertFalse(plan.wall_reserved)
        self.assertEqual(plan.reserved_for_walls, 0)
        self.assertEqual(plan.budget, 3)
        self.assertEqual(len(plan.order), 3)

    def test_zero_builders_plans_nothing(self) -> None:
        cfg = config(
            wall=WallUpgradeConfig(enabled=True),
            hero=PriorityUpgradeConfig(enabled=True, priorities=["Archer Queen"]),
        )
        plan = plan_upgrades(cfg, builders_available=0)
        self.assertEqual(plan.budget, 0)
        self.assertEqual(plan.order, ())
        self.assertFalse(plan)

    def test_duplicate_names_are_removed(self) -> None:
        cfg = config(
            hero=PriorityUpgradeConfig(enabled=True, priorities=["Archer Queen"]),
            resource=PriorityUpgradeConfig(enabled=True, priorities=["archer queen"]),
        )
        self.assertEqual(ordered_targets(cfg), ("Archer Queen",))


if __name__ == "__main__":
    unittest.main()
