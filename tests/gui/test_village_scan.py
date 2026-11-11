"""Offscreen GUI test for scanning upgrade targets into the Village tab."""

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
    """Return canned panel rows."""

    def __init__(self) -> None:
        self.names = [
            "Barbarian King",
            "MonolitH",
            "Elixir Catlector",
            "Laboratory",
            "Crafting Station",
        ]

    def scan_rows(self, execute: bool = True) -> list[UpgradeRow]:
        return [UpgradeRow(name, Point(0, 0)) for name in self.names]


def labels(widget) -> list[str]:
    """Return the item texts of a list widget."""
    return [widget.item(index).text() for index in range(widget.count())]


class VillageScanViewTests(unittest.TestCase):
    """Verify scanned rows land in the right category lists."""

    def setUp(self) -> None:
        apply_theme(_APP)
        self._temp = tempfile.TemporaryDirectory()
        path = Path(self._temp.name) / "settings.json"
        self.settings = SettingsModel(path)
        self.store = ConfigStore(AppConfig())
        model = VillageModel(self.store, self.settings, scanner=FakeScanner())
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

    def test_scan_groups_targets(self) -> None:
        self._scan()
        self.assertTrue(self.scanned)
        hero = labels(self.view.priority_lists[UpgradeCategory.HERO])
        defense = labels(self.view.priority_lists[UpgradeCategory.DEFENSE])
        resource = labels(self.view.priority_lists[UpgradeCategory.RESOURCE])
        army = labels(self.view.priority_lists[UpgradeCategory.ARMY])
        other = labels(self.view.priority_lists[UpgradeCategory.OTHER])
        self.assertIn("Barbarian King", hero)
        self.assertIn("Monolith", defense)
        self.assertIn("Elixir Collector", resource)
        self.assertIn("Laboratory", army)
        self.assertIn("Crafting Station", other)

    def test_checked_targets_are_saved(self) -> None:
        self._scan()
        widget = self.view.priority_lists[UpgradeCategory.DEFENSE]
        self.view.priority_checks[UpgradeCategory.DEFENSE].setChecked(True)
        for index in range(widget.count()):
            item = widget.item(index)
            item.setCheckState(Qt.Checked)
        _APP.processEvents()
        self.assertTrue(self.view.save_btn.isEnabled())
        self.view.save_btn.click()
        _APP.processEvents()
        self.assertIn("Monolith", self.vm.config.defense.priorities)
        self.assertTrue(self.vm.config.defense.enabled)

    def test_scan_disabled_while_bot_runs(self) -> None:
        self.view.set_bot_running(True)
        self.assertFalse(self.view.scan_btn.isEnabled())
        self.view.set_bot_running(False)
        self.assertTrue(self.view.scan_btn.isEnabled())

    def test_priority_checkbox_only_for_hero_and_resource(self) -> None:
        self.assertIn(UpgradeCategory.HERO, self.view.priority_flags)
        self.assertIn(UpgradeCategory.RESOURCE, self.view.priority_flags)
        self.assertNotIn(UpgradeCategory.DEFENSE, self.view.priority_flags)

    def test_priority_flag_is_saved(self) -> None:
        self.view.priority_checks[UpgradeCategory.HERO].setChecked(True)
        self.view.priority_flags[UpgradeCategory.HERO].setChecked(True)
        widget = self.view.priority_lists[UpgradeCategory.HERO]
        widget.addItem(self.view._make_item("Archer Queen", True))
        self.view.wall_enabled.setChecked(True)
        _APP.processEvents()
        self.view.save_btn.click()
        _APP.processEvents()
        saved = self.vm.config
        self.assertTrue(saved.hero.priority)
        self.assertTrue(saved.wall.enabled)
        plan = self.vm.upgrade_plan(3)
        self.assertTrue(plan.wall_reserved)
        self.assertEqual(plan.budget, 2)
        self.assertIn("Archer Queen", plan.order)


if __name__ == "__main__":
    unittest.main()
