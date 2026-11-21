"""Unit tests for the accounts feature model and view-model."""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from COCbot.features.accounts.model import AccountsModel, default_switch_config
from COCbot.features.accounts.viewmodel import AccountsViewModel
from COCbot.models.account import AccountsSnapshot

_APP = QApplication.instance() or QApplication([])


class FakeManager:
    """Record shared_prefs operations without a device."""

    def __init__(self) -> None:
        self.pulled: list[str] = []
        self.pushed: list[tuple[str, str]] = []
        self.switched: list[tuple[str, str]] = []
        self.deleted: list[str] = []

    def list_profiles(self):
        return [
            {
                "safe_name": "main",
                "name": "Main",
                "saved_at": "2026-11-11T10:00:00",
                "android_id": "abc",
                "files": 8,
                "exists": True,
            },
            {
                "safe_name": "alt",
                "name": "Alt",
                "saved_at": "",
                "android_id": "",
                "files": 0,
                "exists": False,
            },
        ]

    def root_label(self) -> str:
        return "root"

    def pull_profile(self, name: str, close_game: bool = True) -> None:
        self.pulled.append(name)

    def push_profile(self, name: str, current_profile: str = "", close_game: bool = True) -> None:
        self.pushed.append((name, current_profile))

    def switch_profile(self, current_profile: str, target_profile: str) -> None:
        self.switched.append((current_profile, target_profile))

    def delete_profile(self, name: str) -> None:
        self.deleted.append(name)


class AccountsModelTests(unittest.TestCase):
    """Verify profile mapping and switch-config persistence."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.path = Path(self._temp.name) / "switch_accounts.json"
        self.manager = FakeManager()
        self.model = AccountsModel(self.manager, self.path)

    def tearDown(self) -> None:
        self._temp.cleanup()

    def test_snapshot(self) -> None:
        snapshot = self.model.snapshot()
        self.assertEqual(len(snapshot.profiles), 2)
        self.assertEqual(snapshot.profiles[0].name, "Main")
        self.assertTrue(snapshot.profiles[0].exists)
        self.assertEqual(snapshot.root_label, "root")
        self.assertEqual(snapshot.current_profile, "")

    def test_pull_push_switch_delete(self) -> None:
        self.model.pull("New")
        self.assertEqual(self.manager.pulled, ["New"])

        self.model.push("Main", current_profile="Old")
        self.assertEqual(self.manager.pushed, [("Main", "Old")])
        self.assertEqual(self.model.load_switch_config()["current_profile"], "Main")

        self.model.switch("Alt", current_profile="Main")
        self.assertEqual(self.manager.switched, [("Main", "Alt")])
        self.assertEqual(self.model.load_switch_config()["current_profile"], "Alt")

        self.model.delete("Alt")
        self.assertEqual(self.manager.deleted, ["Alt"])

    def test_auto_switch_config(self) -> None:
        config = self.model.update_auto_switch(True, 5)
        self.assertTrue(config["enabled"])
        self.assertEqual(config["consecutive_attacks"], 5)
        loaded = self.model.load_switch_config()
        self.assertTrue(loaded["enabled"])
        self.assertEqual(loaded["consecutive_attacks"], 5)

    def test_default_config_shape(self) -> None:
        config = default_switch_config()
        self.assertIn("accounts", config)
        self.assertEqual(len(config["accounts"]), 16)
        self.assertFalse(config["enabled"])


class AccountsViewModelTests(unittest.TestCase):
    """Verify worker-backed refresh and actions."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.path = Path(self._temp.name) / "switch_accounts.json"
        self.manager = FakeManager()
        self.model = AccountsModel(self.manager, self.path)
        self.vm = AccountsViewModel(self.model)
        self.snapshots: list[AccountsSnapshot] = []
        self.status: list[tuple[str, str]] = []
        self.actions: list[str] = []
        self.vm.snapshot_loaded.connect(self.snapshots.append)
        self.vm.status_message.connect(lambda text, kind: self.status.append((text, kind)))
        self.vm.action_finished.connect(self.actions.append)

    def tearDown(self) -> None:
        self._temp.cleanup()

    def _pump(self) -> None:
        for _ in range(20):
            _APP.processEvents()
            time.sleep(0.005)

    def _wait(self, worker) -> None:
        self.assertTrue(worker.wait(5000))
        self._pump()

    def test_refresh(self) -> None:
        self.vm.refresh()
        self._wait(self.vm._worker)
        self.assertEqual(len(self.snapshots), 1)
        self.assertEqual(self.snapshots[0].profiles[0].name, "Main")
        self.assertFalse(self.vm.is_busy)

    def test_pull_action(self) -> None:
        self.vm.refresh()
        self._wait(self.vm._worker)
        self.vm.pull("Main")
        self._wait(self.vm._worker)
        self.assertEqual(self.manager.pulled, ["Main"])
        self.assertIn("Pull", self.actions)
        self.assertFalse(self.vm.is_busy)

    def test_save_auto_switch(self) -> None:
        self.vm.save_auto_switch(True, 4)
        config = self.model.load_switch_config()
        self.assertTrue(config["enabled"])
        self.assertEqual(config["consecutive_attacks"], 4)


if __name__ == "__main__":
    unittest.main()
