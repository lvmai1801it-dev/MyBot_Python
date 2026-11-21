"""Unit tests for the logs feature model and view-model."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from COCbot.features.logs.model import LogsModel
from COCbot.features.logs.viewmodel import LogsViewModel
from COCbot.models.bot_state import BotEvent
from COCbot.models.enums import BotPhase, LogLevel

_APP = QApplication.instance() or QApplication([])


def event(message: str, level: LogLevel = LogLevel.INFO) -> BotEvent:
    """Build a deterministic event."""
    return BotEvent(level=level, message=message, phase=BotPhase.RUNNING, timestamp=1_700_000_000.0)


class LogsModelTests(unittest.TestCase):
    """Verify buffering, filtering, and export."""

    def setUp(self) -> None:
        self.model = LogsModel(max_entries=100)

    def test_add_and_filter_level(self) -> None:
        self.model.add_event(event("info"))
        self.model.add_event(event("bad", LogLevel.ERROR))
        self.assertEqual(len(self.model.all_entries()), 2)
        self.model.set_filter(LogLevel.ERROR)
        self.assertEqual([row.message for row in self.model.entries()], ["bad"])

    def test_filter_search(self) -> None:
        self.model.add_event(event("attack started"))
        self.model.add_event(event("village ready"))
        self.model.set_filter(None, "ATTACK")
        self.assertEqual([row.message for row in self.model.entries()], ["attack started"])

    def test_clear(self) -> None:
        self.model.add_event(event("one"))
        self.model.clear()
        self.assertEqual(self.model.entries(), ())

    def test_export(self) -> None:
        self.model.add_event(event("one"))
        self.model.add_event(event("two", LogLevel.WARNING))
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bot.txt"
            self.assertEqual(self.model.export(path), 2)
            self.assertIn("one", path.read_text(encoding="utf-8"))

    def test_entry_text(self) -> None:
        entry = self.model.add_event(event("hello"))
        self.assertEqual(len(entry.time_text), 8)
        self.assertIn("hello", entry.as_text())


class LogsViewModelTests(unittest.TestCase):
    """Verify signal-driven row updates."""

    def setUp(self) -> None:
        self.model = LogsModel()
        self.vm = LogsViewModel(self.model)
        self.added: list[object] = []
        self.loaded: list[object] = []
        self.cleared: list[bool] = []
        self.vm.entry_added.connect(self.added.append)
        self.vm.entries_loaded.connect(self.loaded.append)
        self.vm.entries_cleared.connect(lambda: self.cleared.append(True))

    def test_append_matching_event(self) -> None:
        self.vm.append_event(event("visible", LogLevel.INFO))
        self.assertEqual(len(self.added), 1)

    def test_filter_suppresses_non_matching(self) -> None:
        self.vm.set_filter(LogLevel.ERROR)
        self.vm.append_event(event("info only", LogLevel.INFO))
        self.assertEqual(self.added, [])
        self.vm.append_event(event("error", LogLevel.ERROR))
        self.assertEqual(len(self.added), 1)

    def test_refresh_and_clear(self) -> None:
        self.vm.append_event(event("one"))
        self.vm.refresh()
        self.assertEqual(len(self.loaded), 1)
        self.vm.clear()
        self.assertEqual(self.cleared, [True])

    def test_export(self) -> None:
        self.vm.append_event(event("export me"))
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "log.txt"
            self.assertTrue(self.vm.export(path))
            self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main()
