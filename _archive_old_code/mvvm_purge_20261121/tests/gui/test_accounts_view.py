"""Offscreen GUI smoke test for the accounts feature."""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from COCbot.features.accounts.model import AccountsModel
from COCbot.features.accounts.view import AccountsView
from COCbot.features.accounts.viewmodel import AccountsViewModel
from COCbot.ui_components import apply_theme

_APP = QApplication.instance() or QApplication([])


class FakeManager:
    """Shared_prefs stub for the view test."""

    def __init__(self) -> None:
        self.pulled: list[str] = []
        self.pushed: list[tuple[str, str]] = []

    def list_profiles(self):
        return [
            {"name": "Main", "saved_at": "2026-11-11", "files": 8, "exists": True},
            {"name": "Alt", "saved_at": "", "files": 7, "exists": True},
        ]

    def root_label(self) -> str:
        return "root"

    def pull_profile(self, name: str, close_game: bool = True) -> None:
        self.pulled.append(name)

    def push_profile(self, name: str, current_profile: str = "", close_game: bool = True) -> None:
        self.pushed.append((name, current_profile))

    def switch_profile(self, current_profile: str, target_profile: str) -> None:
        pass

    def delete_profile(self, name: str) -> None:
        pass


class AccountsViewTests(unittest.TestCase):
    """Verify profile rendering, pull, push, and auto-switch save."""

    def setUp(self) -> None:
        apply_theme(_APP)
        self._temp = tempfile.TemporaryDirectory()
        self.path = Path(self._temp.name) / "switch_accounts.json"
        self.manager = FakeManager()
        self.model = AccountsModel(self.manager, self.path)
        self.vm = AccountsViewModel(self.model)
        self.view = AccountsView(self.vm)
        self.view.show()
        self._wait_initial()

    def tearDown(self) -> None:
        self.view.close()
        self.view.deleteLater()
        _APP.processEvents()
        self._temp.cleanup()

    def _wait_initial(self) -> None:
        for _ in range(50):
            _APP.processEvents()
            if self.vm._worker is None:
                break
            time.sleep(0.005)
        if self.vm._worker is not None:
            self.assertTrue(self.vm._worker.wait(5000))
        _APP.processEvents()

    def test_profiles_loaded(self) -> None:
        self.assertEqual(self.view.profile_combo.count(), 2)
        self.assertIn("Main", self.view.profile_combo.itemText(0))
        self.assertIn("root", self.view.root_label.text())

    def test_pull_and_push(self) -> None:
        self.view.name_edit.setText("New")
        self.view.pull_btn.click()
        self._wait_initial()
        self.assertEqual(self.manager.pulled, ["New"])

        self.view.profile_combo.setCurrentIndex(0)
        self.view.push_btn.click()
        self._wait_initial()
        self.assertEqual(self.manager.pushed[0][0], "Main")

    def test_save_auto_switch(self) -> None:
        self.view.auto_enabled.setChecked(True)
        self.view.attacks_spin.setValue(3)
        self.view.save_auto_btn.click()
        _APP.processEvents()
        config = self.model.load_switch_config()
        self.assertTrue(config["enabled"])
        self.assertEqual(config["consecutive_attacks"], 3)


if __name__ == "__main__":
    unittest.main()
