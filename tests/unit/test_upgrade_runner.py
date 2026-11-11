"""Unit tests for the upgrade runner (builder budget and stop conditions)."""

from __future__ import annotations

import unittest

from COCbot.core.config.schema import (
    PriorityUpgradeConfig,
    UpgradeConfig,
    WallUpgradeConfig,
)
from COCbot.features.village.runner import UpgradeRunner
from COCbot.features.village.upgrades import UpgradeResult


def config(*, wall_enabled: bool = False) -> UpgradeConfig:
    """Two ticked buildings, walls optional."""
    return UpgradeConfig(
        wall=WallUpgradeConfig(enabled=wall_enabled),
        buildings=PriorityUpgradeConfig(
            enabled=True,
            priorities=["Archer Queen", "Monolith", "X-Bow"],
        ),
    )


class ScriptedUpgrader:
    """Return scripted results and record calls."""

    def __init__(self, results: list[UpgradeResult]) -> None:
        self.results = results
        self.calls: list[str] = []
        self.dismissed = 0

    def upgrade_listed(self, name: str, execute: bool = True) -> UpgradeResult:
        self.calls.append(name)
        return self.results.pop(0)

    def dismiss(self, execute: bool = True) -> bool:
        self.dismissed += 1
        return True


class UpgradeRunnerTests(unittest.TestCase):
    """Verify the runner respects the builder budget and stops when maxed."""

    def test_dry_run_returns_the_plan(self) -> None:
        runner = UpgradeRunner(ScriptedUpgrader([]))  # type: ignore[arg-type]
        result = runner.run(config(), builders_available=2, execute=False)
        self.assertTrue(result.ok)
        self.assertEqual(result.upgraded, ("Archer Queen", "Monolith"))
        self.assertEqual(result.builders_left, 2)

    def test_upgrades_until_target_leaves_the_panel(self) -> None:
        upgrader = ScriptedUpgrader(
            [
                UpgradeResult(True, "Archer Queen", executed=True, message="Upgraded"),
                UpgradeResult(True, "Archer Queen", executed=True, message="Upgraded"),
                UpgradeResult(
                    True,
                    "Archer Queen",
                    executed=False,
                    message="Archer Queen is no longer listed",
                ),
            ]
        )
        runner = UpgradeRunner(upgrader)  # type: ignore[arg-type]
        result = runner.run(config(), builders_available=2, execute=True)
        self.assertTrue(result.ok)
        self.assertEqual(result.upgraded, ("Archer Queen", "Archer Queen"))
        self.assertEqual(result.builders_left, 0)
        self.assertEqual(len(upgrader.calls), 2)
        self.assertGreaterEqual(upgrader.dismissed, 1)

    def test_wall_reserves_one_builder(self) -> None:
        upgrader = ScriptedUpgrader(
            [
                UpgradeResult(True, "Archer Queen", executed=True, message="Upgraded"),
                UpgradeResult(
                    True,
                    "Archer Queen",
                    executed=False,
                    message="Archer Queen is no longer listed",
                ),
                UpgradeResult(True, "Monolith", executed=True, message="Upgraded"),
                UpgradeResult(
                    True,
                    "Monolith",
                    executed=False,
                    message="Monolith is no longer listed",
                ),
            ]
        )
        runner = UpgradeRunner(upgrader)  # type: ignore[arg-type]
        result = runner.run(config(wall_enabled=True), builders_available=3, execute=True)
        self.assertTrue(result.ok)
        self.assertEqual(result.upgraded, ("Archer Queen", "Monolith"))
        self.assertEqual(result.builders_left, 0)

    def test_failure_stops_the_run(self) -> None:
        upgrader = ScriptedUpgrader(
            [
                UpgradeResult(
                    False,
                    "Archer Queen",
                    executed=False,
                    message="Confirm button template not found",
                )
            ]
        )
        runner = UpgradeRunner(upgrader)  # type: ignore[arg-type]
        result = runner.run(config(), builders_available=2, execute=True)
        self.assertFalse(result.ok)
        self.assertEqual(result.message, "Confirm button template not found")

    def test_no_enabled_targets(self) -> None:
        runner = UpgradeRunner(ScriptedUpgrader([]))  # type: ignore[arg-type]
        result = runner.run(
            UpgradeConfig(),
            builders_available=2,
            execute=True,
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.upgraded, ())

    def test_army_upgrade_runs_once_and_keeps_builders(self) -> None:
        cfg = UpgradeConfig(
            army=PriorityUpgradeConfig(enabled=True, priorities=["Lava Hound"]),
        )
        upgrader = ScriptedUpgrader(
            [UpgradeResult(True, "Lava Hound", executed=True, message="Upgraded")]
        )
        runner = UpgradeRunner(upgrader)  # type: ignore[arg-type]
        result = runner.run(cfg, builders_available=3, execute=True)
        self.assertTrue(result.ok)
        self.assertEqual(result.upgraded, ("Lava Hound",))
        self.assertEqual(len(upgrader.calls), 1)
        self.assertEqual(result.builders_left, 3)

    def test_missing_loot_stops_the_run(self) -> None:
        upgrader = ScriptedUpgrader(
            [
                UpgradeResult(
                    True,
                    "Archer Queen",
                    executed=False,
                    needs_loot=True,
                    message="not enough loot; attack first",
                )
            ]
        )
        runner = UpgradeRunner(upgrader)  # type: ignore[arg-type]
        result = runner.run(config(), builders_available=2, execute=True)
        self.assertTrue(result.ok)
        self.assertTrue(result.needs_loot)
        self.assertEqual(result.upgraded, ())
        self.assertIn("attack", result.message)


if __name__ == "__main__":
    unittest.main()
