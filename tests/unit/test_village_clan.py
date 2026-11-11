"""Unit tests for the village and clan config features."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from COCbot.core.config import AppConfig, ConfigStore, load_config
from COCbot.features.clan.model import ClanModel
from COCbot.features.clan.viewmodel import ClanViewModel
from COCbot.features.settings.model import SettingsModel
from COCbot.features.village.model import VillageModel
from COCbot.features.village.viewmodel import VillageViewModel
from COCbot.models.enums import UpgradeCategory

_APP = QApplication.instance() or QApplication([])


class VillageFeatureTests(unittest.TestCase):
    """Verify wall/priority draft edits and persistence."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.path = Path(self._temp.name) / "settings.json"
        self.settings = SettingsModel(self.path)
        self.store = ConfigStore(AppConfig())
        self.model = VillageModel(self.store, self.settings)
        self.vm = VillageViewModel(self.model)

    def tearDown(self) -> None:
        self._temp.cleanup()

    def test_defaults_and_save(self) -> None:
        self.vm.load()
        self.assertFalse(self.vm.is_dirty)
        self.vm.set_wall(True, 12, 4_000_000, 3_000_000)
        self.vm.set_priority(UpgradeCategory.HERO, True, ["Queen", "King"])
        self.assertTrue(self.vm.is_dirty)
        self.assertTrue(self.vm.save())
        self.assertFalse(self.vm.is_dirty)

        loaded = load_config(self.path)
        self.assertTrue(loaded.upgrades.wall.enabled)
        self.assertEqual(loaded.upgrades.wall.level, 12)
        self.assertEqual(loaded.upgrades.hero.priorities, ["Queen", "King"])
        self.assertTrue(self.store.get().upgrades.wall.enabled)

    def test_reset_defaults(self) -> None:
        self.vm.load()
        self.vm.set_wall(True, 15, 1, 1)
        self.vm.save()
        self.vm.reset_defaults()
        self.assertTrue(self.vm.is_dirty)
        self.assertEqual(self.vm.config.wall.level, AppConfig().upgrades.wall.level)


class ClanFeatureTests(unittest.TestCase):
    """Verify clan toggles and persistence."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.path = Path(self._temp.name) / "settings.json"
        self.settings = SettingsModel(self.path)
        self.store = ConfigStore(AppConfig())
        self.model = ClanModel(self.store, self.settings)
        self.vm = ClanViewModel(self.model)

    def tearDown(self) -> None:
        self._temp.cleanup()

    def test_save(self) -> None:
        self.vm.load()
        self.vm.set_options(True, True, 10, False)
        self.assertTrue(self.vm.is_dirty)
        self.assertTrue(self.vm.save())
        loaded = load_config(self.path)
        self.assertTrue(loaded.clan.enable_clan_games)
        self.assertTrue(loaded.clan.enable_clan_capital)
        self.assertEqual(loaded.clan.capital_hall_level, 10)
        self.assertFalse(loaded.clan.request_troops)
        self.assertEqual(self.store.get().clan.capital_hall_level, 10)

    def test_reset_defaults(self) -> None:
        self.vm.load()
        self.vm.set_options(True, True, 15, False)
        self.vm.save()
        self.vm.reset_defaults()
        self.assertTrue(self.vm.is_dirty)
        self.assertEqual(self.vm.config.capital_hall_level, AppConfig().clan.capital_hall_level)


if __name__ == "__main__":
    unittest.main()
