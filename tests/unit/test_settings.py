"""Unit tests for the settings feature model and view-model."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from COCbot.core.config import AppConfig, load_config
from COCbot.features.settings.model import SettingsModel
from COCbot.features.settings.viewmodel import SettingsViewModel
from COCbot.models.enums import EmulatorType

_APP = QApplication.instance() or QApplication([])


class SettingsModelTests(unittest.TestCase):
    """Verify persistence through the pure-Python model."""

    def test_missing_file_returns_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model = SettingsModel(Path(temp_dir) / "settings.json")
            self.assertEqual(model.load(), AppConfig())

    def test_save_and_reload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            model = SettingsModel(path)
            config = model.load()
            config = AppConfig.from_legacy_dict(
                {**config.to_dict(), "gold_threshold": 12345}
            )
            model.save(config)
            self.assertTrue(path.is_file())
            self.assertEqual(model.load().resources.gold, 12345)
            self.assertEqual(load_config(path).resources.gold, 12345)


class SettingsViewModelTests(unittest.TestCase):
    """Verify load/dirty/save behaviour and signal order."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.path = Path(self._temp.name) / "settings.json"
        self.model = SettingsModel(self.path)
        self.vm = SettingsViewModel(self.model)
        self.loaded: list[object] = []
        self.saved: list[object] = []
        self.dirty: list[bool] = []
        self.status: list[tuple[str, str]] = []
        self.errors: list[str] = []
        self.vm.loaded.connect(self.loaded.append)
        self.vm.saved.connect(self.saved.append)
        self.vm.dirty_changed.connect(self.dirty.append)
        self.vm.status_message.connect(lambda text, kind: self.status.append((text, kind)))
        self.vm.error_occurred.connect(self.errors.append)

    def tearDown(self) -> None:
        self._temp.cleanup()

    def test_load_emits_config(self) -> None:
        self.vm.load()
        self.assertEqual(len(self.loaded), 1)
        self.assertIsInstance(self.loaded[0], AppConfig)
        self.assertEqual(self.dirty, [False])
        self.assertFalse(self.vm.is_dirty)

    def test_edit_and_save(self) -> None:
        self.vm.load()
        self.vm.set_resources(111, 222, 333)
        self.assertTrue(self.vm.is_dirty)
        self.assertIn(True, self.dirty)
        self.assertTrue(self.vm.save())
        self.assertFalse(self.vm.is_dirty)
        self.assertEqual(len(self.saved), 1)
        loaded = load_config(self.path)
        self.assertEqual(loaded.resources.gold, 111)
        self.assertEqual(loaded.resources.elixir, 222)
        self.assertEqual(loaded.resources.dark_elixir, 333)

    def test_reset_defaults_is_dirty(self) -> None:
        self.vm.load()
        self.vm.set_resources(999, 999, 999)
        self.vm.save()
        self.vm.reset_defaults()
        self.assertTrue(self.vm.is_dirty)
        self.assertEqual(self.vm.config.resources.gold, AppConfig().resources.gold)

    def test_emulator_defaults_host(self) -> None:
        self.vm.load()
        self.vm.set_emulator(EmulatorType.LDPLAYER, "")
        self.assertEqual(self.vm.config.emulator.emulator_type, EmulatorType.LDPLAYER)
        self.assertEqual(self.vm.config.emulator.host, "127.0.0.1:5555")

    def test_empty_attack_name_is_rejected(self) -> None:
        self.vm.load()
        self.vm.set_attack("", "Ngẫu nhiên")
        self.assertFalse(self.vm.save())
        self.assertTrue(self.errors)
        self.assertFalse(self.path.exists())

    def test_wall_and_clan_updates(self) -> None:
        self.vm.load()
        self.vm.set_wall_upgrade(True, 12, 4_000_000, 3_000_000)
        self.vm.set_clan(True, True, 10, False)
        self.vm.set_stats(True)
        config = self.vm.config
        self.assertTrue(config.upgrades.wall.enabled)
        self.assertEqual(config.upgrades.wall.level, 12)
        self.assertTrue(config.clan.enable_clan_games)
        self.assertTrue(config.clan.enable_clan_capital)
        self.assertEqual(config.clan.capital_hall_level, 10)
        self.assertFalse(config.clan.request_troops)
        self.assertTrue(config.enable_stats)


if __name__ == "__main__":
    unittest.main()
