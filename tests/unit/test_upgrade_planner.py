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
    buildings: PriorityUpgradeConfig | None = None,
    army: PriorityUpgradeConfig | None = None,
    equipment: PriorityUpgradeConfig | None = None,
    pets: PriorityUpgradeConfig | None = None,
    wall: WallUpgradeConfig | None = None,
    hero_priority: bool = False,
    money_priority: bool = False,
) -> UpgradeConfig:
    """Build an upgrade config for the planner tests."""
    return UpgradeConfig(
        wall=wall or WallUpgradeConfig(),
        buildings=buildings or PriorityUpgradeConfig(),
        army=army or PriorityUpgradeConfig(),
        equipment=equipment or PriorityUpgradeConfig(),
        pets=pets or PriorityUpgradeConfig(),
        hero=PriorityUpgradeConfig(priority=hero_priority),
        resource=PriorityUpgradeConfig(priority=money_priority),
    )


class PlannerTests(unittest.TestCase):
    """Verify priority ordering and the reserved wall builder."""

    def test_hero_priority_moves_heroes_first(self) -> None:
        cfg = config(
            buildings=PriorityUpgradeConfig(
                enabled=True,
                priorities=["Monolith", "Archer Queen", "Gold Mine"],
            ),
            hero_priority=True,
        )
        self.assertEqual(
            ordered_targets(cfg),
            ("Archer Queen", "Monolith", "Gold Mine"),
        )

    def test_money_priority_moves_resource_buildings_first(self) -> None:
        cfg = config(
            buildings=PriorityUpgradeConfig(
                enabled=True,
                priorities=["Monolith", "Gold Mine", "Archer Queen"],
            ),
            money_priority=True,
        )
        self.assertEqual(
            ordered_targets(cfg),
            ("Gold Mine", "Monolith", "Archer Queen"),
        )

    def test_without_flags_the_list_order_is_kept(self) -> None:
        cfg = config(
            buildings=PriorityUpgradeConfig(
                enabled=True,
                priorities=["Monolith", "Gold Mine", "Archer Queen"],
            )
        )
        self.assertEqual(
            ordered_targets(cfg),
            ("Monolith", "Gold Mine", "Archer Queen"),
        )

    def test_single_slot_tabs_are_capped(self) -> None:
        cfg = config(
            buildings=PriorityUpgradeConfig(enabled=True, priorities=["Monolith"]),
            pets=PriorityUpgradeConfig(
                enabled=True,
                priorities=["L.A.S.S.I", "Frosty"],
            ),
        )
        plan = plan_upgrades(cfg, builders_available=6)
        self.assertEqual(plan.order, ("Monolith", "L.A.S.S.I"))
        self.assertEqual(plan.single_slot, ("L.A.S.S.I",))
        self.assertEqual(plan.skipped, ("Frosty",))

    def test_ticked_targets_run_even_without_the_enable_flag(self) -> None:
        cfg = config(
            buildings=PriorityUpgradeConfig(enabled=False, priorities=["Cannon"]),
            equipment=PriorityUpgradeConfig(enabled=True, priorities=["Giant Gauntlet"]),
        )
        self.assertEqual(ordered_targets(cfg), ("Cannon", "Giant Gauntlet"))

    def test_wall_reserves_one_builder(self) -> None:
        cfg = config(
            wall=WallUpgradeConfig(enabled=True, level=12),
            buildings=PriorityUpgradeConfig(
                enabled=True,
                priorities=["Archer Queen", "Grand Warden", "Monolith"],
            ),
            hero_priority=True,
        )
        plan = plan_upgrades(cfg, builders_available=3)
        self.assertTrue(plan.wall_reserved)
        self.assertEqual(plan.reserved_for_walls, 1)
        self.assertEqual(plan.budget, 2)
        self.assertEqual(plan.order, ("Archer Queen", "Grand Warden"))
        self.assertEqual(plan.skipped, ("Monolith",))

    def test_without_walls_all_builders_are_usable(self) -> None:
        cfg = config(
            buildings=PriorityUpgradeConfig(
                enabled=True,
                priorities=["Archer Queen", "Grand Warden", "Monolith"],
            )
        )
        plan = plan_upgrades(cfg, builders_available=3)
        self.assertFalse(plan.wall_reserved)
        self.assertEqual(plan.reserved_for_walls, 0)
        self.assertEqual(plan.budget, 3)
        self.assertEqual(len(plan.order), 3)

    def test_zero_builders_plans_nothing(self) -> None:
        cfg = config(
            wall=WallUpgradeConfig(enabled=True),
            buildings=PriorityUpgradeConfig(enabled=True, priorities=["Archer Queen"]),
        )
        plan = plan_upgrades(cfg, builders_available=0)
        self.assertEqual(plan.budget, 0)
        self.assertEqual(plan.order, ())
        self.assertFalse(plan)

    def test_duplicate_names_are_removed(self) -> None:
        cfg = config(
            buildings=PriorityUpgradeConfig(
                enabled=True,
                priorities=["Archer Queen"],
            ),
            army=PriorityUpgradeConfig(enabled=True, priorities=["archer queen"]),
        )
        self.assertEqual(ordered_targets(cfg), ("Archer Queen",))

    def test_army_and_pets_allow_one_upgrade_each(self) -> None:
        cfg = config(
            buildings=PriorityUpgradeConfig(enabled=True, priorities=["Monolith"]),
            army=PriorityUpgradeConfig(
                enabled=True,
                priorities=["Lava Hound", "Bowler"],
            ),
            pets=PriorityUpgradeConfig(enabled=True, priorities=["Frosty", "Diggy"]),
        )
        plan = plan_upgrades(cfg, builders_available=6)
        self.assertEqual(plan.order, ("Monolith", "Lava Hound", "Frosty"))
        self.assertEqual(plan.single_slot, ("Lava Hound", "Frosty"))
        self.assertIn("Bowler", plan.skipped)
        self.assertIn("Diggy", plan.skipped)

    def test_buildings_use_every_free_builder(self) -> None:
        cfg = config(
            buildings=PriorityUpgradeConfig(
                enabled=True,
                priorities=["Cannon", "Archer Tower", "Mortar", "X-Bow", "Inferno Tower"],
            )
        )
        plan = plan_upgrades(cfg, builders_available=5)
        self.assertEqual(len(plan.order), 5)
        self.assertEqual(plan.budget, 5)
        self.assertFalse(plan.wall_reserved)

    def test_wall_keeps_one_builder_but_still_uses_the_rest(self) -> None:
        cfg = config(
            wall=WallUpgradeConfig(enabled=True),
            buildings=PriorityUpgradeConfig(
                enabled=True,
                priorities=["Cannon", "Archer Tower", "Mortar", "X-Bow", "Inferno Tower", "Monolith"],
            ),
        )
        plan = plan_upgrades(cfg, builders_available=6)
        self.assertEqual(plan.budget, 5)
        self.assertEqual(len(plan.order), 5)
        self.assertEqual(plan.skipped, ("Monolith",))


if __name__ == "__main__":
    unittest.main()
