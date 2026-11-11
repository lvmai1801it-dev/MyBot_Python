"""Offscreen GUI test for scanning the four Build panel tabs."""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from COCbot.core.config import AppConfig, ConfigStore
from COCbot.features.settings.model import SettingsModel
from COCbot.features.village.model import VillageModel
from COCbot.features.village.upgrades import UpgradeRow
from COCbot.features.village.view import VillageView
from COCbot.features.village.viewmodel import VillageViewModel
from COCbot.models.enums import UpgradeCategory
from COCbot.models.geometry import Point
from COCbot.ui_components import apply_theme

_APP = QApplication.instance() or QApplication([])


class FakeScanner:
    """Return canned rows for all four Build tabs."""

    def scan_panel(self, execute: bool = True) -> dict[str, list[UpgradeRow]]:
        def rows(names: list[str]) -> list[UpgradeRow]:
            return [UpgradeRow(name, Point(0, 0)) for name in names]

        return {
            "buildings": rows(
                ["Barbarian King", "MonolitH", "Elixir Catlector", "Crafting Station"]
            ),
            "army": rows(["Laboratory"]),
            "equipment": rows(["Giant Gauntlet"]),
            "pets": rows(["L.A.S.S.I"]),
        }


class FakeReader:
    """Builder count reported by the village reader."""

    def __init__(self, available: int) -> None:
        self.available = available

    def read(self):
        from COCbot.features.village.resources import VillageResources

        return VillageResources(builders_available=self.available, builders_total=6)


def labels(widget) -> list[str]:
    """Return the item texts of a list widget."""
    return [widget.item(index).text() for index in range(widget.count())]


class VillageScanViewTests(unittest.TestCase):
    """Verify scanned rows land in the matching Build tab."""

    def setUp(self) -> None:
        apply_theme(_APP)
        self._temp = tempfile.TemporaryDirectory()
        path = Path(self._temp.name) / "settings.json"
        self.settings = SettingsModel(path)
        self.store = ConfigStore(AppConfig())
        model = VillageModel(
            self.store,
            self.settings,
            scanner=FakeScanner(),
            resource_reader=FakeReader(2),
        )
        self.vm = VillageViewModel(model)
        self.view = VillageView(self.vm)
        self.view.show()
        _APP.processEvents()
        self.scanned = []
        self.vm.targets_scanned.connect(self.scanned.append)

    def tearDown(self) -> None:
        self.vm.shutdown(1000)
        self.view.close()
        self.view.deleteLater()
        _APP.processEvents()
        self._temp.cleanup()

    def _scan(self) -> None:
        self.vm.scan_targets()
        for _ in range(300):
            _APP.processEvents()
            if self.scanned:
                break
            time.sleep(0.01)
        _APP.processEvents()

    def test_four_tabs(self) -> None:
        self.assertEqual(self.view.tabs.count(), 4)
        self.assertEqual(
            [
                self.view.tabs.tabText(index).replace("&&", "&")
                for index in range(4)
            ],
            [
                "Buildings & Heroes",
                "Army Upgrades",
                "Hero Equipment",
                "Hero Pets",
            ],
        )

    def test_scan_fills_every_tab(self) -> None:
        self._scan()
        self.assertTrue(self.scanned)
        buildings = labels(self.view.priority_lists[UpgradeCategory.BUILDINGS])
        army = labels(self.view.priority_lists[UpgradeCategory.ARMY])
        equipment = labels(self.view.priority_lists[UpgradeCategory.EQUIPMENT])
        pets = labels(self.view.priority_lists[UpgradeCategory.PETS])
        self.assertIn("Barbarian King", buildings)
        self.assertIn("Monolith", buildings)
        self.assertIn("Elixir Collector", buildings)
        self.assertIn("Crafting Station", buildings)
        self.assertEqual(army, ["Laboratory"])
        self.assertEqual(equipment, ["Giant Gauntlet"])
        self.assertEqual(pets, ["L.A.S.S.I"])

    def test_checked_targets_are_saved(self) -> None:
        self._scan()
        widget = self.view.priority_lists[UpgradeCategory.ARMY]
        self.view.priority_checks[UpgradeCategory.ARMY].setChecked(True)
        for index in range(widget.count()):
            widget.item(index).setCheckState(Qt.Checked)
        _APP.processEvents()
        self.assertTrue(self.view.save_btn.isEnabled())
        self.view.save_btn.click()
        _APP.processEvents()
        self.assertIn("Laboratory", self.vm.config.army.priorities)
        self.assertTrue(self.vm.config.army.enabled)

    def test_scan_disabled_while_bot_runs(self) -> None:
        self.view.set_bot_running(True)
        self.assertFalse(self.view.scan_btn.isEnabled())
        self.view.set_bot_running(False)
        self.assertTrue(self.view.scan_btn.isEnabled())

    def test_priority_flags_are_saved(self) -> None:
        self._scan()
        self.view.hero_priority.setChecked(True)
        self.view.money_priority.setChecked(True)
        self.view.wall_enabled.setChecked(True)
        _APP.processEvents()
        self.view.save_btn.click()
        _APP.processEvents()
        saved = self.vm.config
        self.assertTrue(saved.hero.priority)
        self.assertTrue(saved.resource.priority)
        self.assertTrue(saved.wall.enabled)
        plan = self.vm.upgrade_plan(3)
        self.assertTrue(plan.wall_reserved)
        self.assertEqual(plan.budget, 2)

    def test_builder_limit_caps_ticked_targets(self) -> None:
        self._scan()
        widget = self.view.priority_lists[UpgradeCategory.BUILDINGS]
        for index in range(3):
            widget.item(index).setCheckState(Qt.Checked)
        _APP.processEvents()
        checked = [
            widget.item(index).text()
            for index in range(widget.count())
            if widget.item(index).checkState() == Qt.Checked
        ]
        self.assertEqual(len(checked), 2)

    def test_wall_tick_reduces_the_limit(self) -> None:
        self._scan()
        widget = self.view.priority_lists[UpgradeCategory.BUILDINGS]
        for index in range(2):
            widget.item(index).setCheckState(Qt.Checked)
        _APP.processEvents()
        self.assertEqual(len(self.view._checked_items(UpgradeCategory.BUILDINGS)), 2)
        self.view.wall_enabled.setChecked(True)
        _APP.processEvents()
        self.assertEqual(len(self.view._checked_items(UpgradeCategory.BUILDINGS)), 1)


if __name__ == "__main__":
    unittest.main()
