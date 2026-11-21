"""Offscreen GUI smoke test for the settings vertical slice."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from COCbot.core.config import AppConfig, load_config
from COCbot.features.settings.model import SettingsModel
from COCbot.features.settings.view import SettingsView
from COCbot.features.settings.viewmodel import SettingsViewModel
from COCbot.ui_components import apply_theme

_APP = QApplication.instance() or QApplication([])


class SettingsViewTests(unittest.TestCase):
    """Verify the view renders config and saves user edits."""

    def setUp(self) -> None:
        apply_theme(_APP)
        self._temp = tempfile.TemporaryDirectory()
        self.path = Path(self._temp.name) / "settings.json"
        self.vm = SettingsViewModel(SettingsModel(self.path))
        self.view = SettingsView(self.vm)
        self.view.show()
        _APP.processEvents()

    def tearDown(self) -> None:
        self.view.close()
        self.view.deleteLater()
        _APP.processEvents()
        self._temp.cleanup()

    def test_initial_values(self) -> None:
        defaults = AppConfig()
        self.assertEqual(self.view.gold_spin.value(), defaults.resources.gold)
        self.assertEqual(self.view.wall_level.value(), defaults.upgrades.wall.level)
        self.assertFalse(self.view.save_btn.isEnabled())

    def test_edit_and_save(self) -> None:
        self.view.gold_spin.setValue(43210)
        self.view.wall_enabled.setChecked(True)
        _APP.processEvents()
        self.assertTrue(self.vm.is_dirty)
        self.assertTrue(self.view.save_btn.isEnabled())

        self.view.save_btn.click()
        _APP.processEvents()
        self.assertFalse(self.vm.is_dirty)
        self.assertFalse(self.view.save_btn.isEnabled())
        saved = load_config(self.path)
        self.assertEqual(saved.resources.gold, 43210)
        self.assertTrue(saved.upgrades.wall.enabled)

    def test_defaults_button_marks_dirty(self) -> None:
        self.view.gold_spin.setValue(1)
        self.view.save_btn.click()
        _APP.processEvents()
        self.view.defaults_btn.click()
        _APP.processEvents()
        self.assertEqual(self.vm.config.resources.gold, AppConfig().resources.gold)
        self.assertTrue(self.view.save_btn.isEnabled())

    def test_reload_restores_saved_values(self) -> None:
        self.view.gold_spin.setValue(777)
        self.view.save_btn.click()
        _APP.processEvents()
        self.view.gold_spin.setValue(999)
        _APP.processEvents()
        self.view.reload_btn.click()
        _APP.processEvents()
        self.assertEqual(self.view.gold_spin.value(), 777)
        self.assertFalse(self.vm.is_dirty)


if __name__ == "__main__":
    unittest.main()
