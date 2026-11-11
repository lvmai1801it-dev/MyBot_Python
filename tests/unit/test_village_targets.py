"""Unit tests for upgrade target classification and panel scanning."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from COCbot.core.config import AppConfig, ConfigStore
from COCbot.features.settings.model import SettingsModel
from COCbot.features.village.model import VillageModel
from COCbot.features.village.targets import (
    canonical_name,
    category_for,
    group_targets,
)
from COCbot.features.village.upgrades import UpgradeRow
from COCbot.models.enums import UpgradeCategory
from COCbot.models.geometry import Point


class TargetCatalogTests(unittest.TestCase):
    """Verify OCR names map to canonical names and categories."""

    def test_canonical_names_repair_ocr_slips(self) -> None:
        self.assertEqual(canonical_name("MonolitH"), "Monolith")
        self.assertEqual(canonical_name("Elixir Catlector"), "Elixir Collector")
        self.assertEqual(canonical_name("Barbarian King"), "Barbarian King")

    def test_unknown_names_are_kept(self) -> None:
        self.assertIsNone(canonical_name("Totally New Building"))

    def test_categories(self) -> None:
        self.assertEqual(category_for("Archer Queen"), UpgradeCategory.HERO)
        self.assertEqual(category_for("MonolitH"), UpgradeCategory.DEFENSE)
        self.assertEqual(category_for("Elixir Catlector"), UpgradeCategory.RESOURCE)
        self.assertEqual(category_for("Laboratory"), UpgradeCategory.ARMY)
        self.assertEqual(category_for("Crafting Station"), UpgradeCategory.OTHER)
        self.assertEqual(category_for("Mystery Shed"), UpgradeCategory.OTHER)

    def test_group_targets_deduplicates(self) -> None:
        groups = group_targets(
            ["Barbarian King", "barbarian king", "MonolitH", "Monolith", ""]
        )
        self.assertEqual(groups[UpgradeCategory.HERO], ["Barbarian King"])
        self.assertEqual(groups[UpgradeCategory.DEFENSE], ["Monolith"])


class FakeScanner:
    """Return canned rows without touching the game."""

    def __init__(self, names: list[str]) -> None:
        self.names = names
        self.calls = 0

    def scan_rows(self, execute: bool = True) -> list[UpgradeRow]:
        self.calls += 1
        return [UpgradeRow(name, Point(0, 0)) for name in self.names]


class VillageScanTests(unittest.TestCase):
    """Verify the model delegates the panel scan."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        path = Path(self._temp.name) / "settings.json"
        self.store = ConfigStore(AppConfig())
        self.settings = SettingsModel(path)

    def tearDown(self) -> None:
        self._temp.cleanup()

    def test_scan_returns_row_names(self) -> None:
        scanner = FakeScanner(["Barbarian King", "MonolitH"])
        model = VillageModel(self.store, self.settings, scanner=scanner)
        self.assertEqual(model.scan_targets(), ("Barbarian King", "MonolitH"))
        self.assertEqual(scanner.calls, 1)

    def test_scan_without_scanner_is_empty(self) -> None:
        model = VillageModel(self.store, self.settings)
        self.assertEqual(model.scan_targets(), ())


if __name__ == "__main__":
    unittest.main()
