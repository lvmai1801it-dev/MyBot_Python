"""Offscreen GUI smoke test for the village and clan config views."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from COCbot.core.config import AppConfig, ConfigStore, load_config
from COCbot.features.clan.model import ClanModel
from COCbot.features.clan.view import ClanView
from COCbot.features.clan.viewmodel import ClanViewModel
from COCbot.features.settings.model import SettingsModel
from COCbot.features.village.model import VillageModel
from COCbot.features.village.view import VillageView
from COCbot.features.village.viewmodel import VillageViewModel
from COCbot.ui_components import apply_theme

_APP = QApplication.instance() or QApplication([])


class VillageClanViewTests(unittest.TestCase):
    """Verify both config views render and save."""

    def setUp(self) -> None:
        apply_theme(_APP)
        self._temp = tempfile.TemporaryDirectory()
        self.path = Path(self._temp.name) / "settings.json"
        self.settings = SettingsModel(self.path)
        self.store = ConfigStore(AppConfig())

    def tearDown(self) -> None:
        self._temp.cleanup()

    def test_village_view(self) -> None:
        model = VillageModel(self.store, self.settings)
        vm = VillageViewModel(model)
        view = VillageView(vm)
        view.show()
        _APP.processEvents()
        self.assertEqual(view.wall_level.value(), AppConfig().upgrades.wall.level)
        view.wall_enabled.setChecked(True)
        view.wall_level.setValue(11)
        _APP.processEvents()
        self.assertTrue(view.save_btn.isEnabled())
        view.save_btn.click()
        _APP.processEvents()
        loaded = load_config(self.path)
        self.assertTrue(loaded.upgrades.wall.enabled)
        self.assertEqual(loaded.upgrades.wall.level, 11)
        view.close()
        view.deleteLater()
        _APP.processEvents()

    def test_clan_view(self) -> None:
        model = ClanModel(self.store, self.settings)
        vm = ClanViewModel(model)
        view = ClanView(vm)
        view.show()
        _APP.processEvents()
        view.games_check.setChecked(True)
        view.capital_check.setChecked(True)
        view.capital_level.setValue(9)
        _APP.processEvents()
        view.save_btn.click()
        _APP.processEvents()
        loaded = load_config(self.path)
        self.assertTrue(loaded.clan.enable_clan_games)
        self.assertTrue(loaded.clan.enable_clan_capital)
        self.assertEqual(loaded.clan.capital_hall_level, 9)
        view.close()
        view.deleteLater()
        _APP.processEvents()


if __name__ == "__main__":
    unittest.main()
