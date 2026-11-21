"""Offscreen GUI smoke test for the logs feature."""

from __future__ import annotations

import unittest

from PyQt5.QtWidgets import QApplication

from COCbot.features.logs.model import LogsModel
from COCbot.features.logs.view import LogsView
from COCbot.features.logs.viewmodel import LogsViewModel
from COCbot.models.bot_state import BotEvent
from COCbot.models.enums import BotPhase, LogLevel
from COCbot.ui_components import apply_theme

_APP = QApplication.instance() or QApplication([])


class LogsViewTests(unittest.TestCase):
    """Verify table rows, filtering, and clearing."""

    def setUp(self) -> None:
        apply_theme(_APP)
        self.model = LogsModel()
        self.vm = LogsViewModel(self.model)
        self.view = LogsView(self.vm)
        self.view.show()
        _APP.processEvents()

    def tearDown(self) -> None:
        self.view.close()
        self.view.deleteLater()
        _APP.processEvents()

    def _append(self, message: str, level: LogLevel) -> None:
        self.vm.append_event(
            BotEvent(
                level=level,
                message=message,
                phase=BotPhase.RUNNING,
                timestamp=1_700_000_000.0,
            )
        )
        _APP.processEvents()

    def test_rows_and_filter(self) -> None:
        self._append("hello", LogLevel.INFO)
        self._append("boom", LogLevel.ERROR)
        self.assertEqual(self.view.table.rowCount(), 2)

        self.view.filter_combo.setCurrentText("ERROR")
        _APP.processEvents()
        self.assertEqual(self.view.table.rowCount(), 1)
        self.assertEqual(self.view.table.item(0, 2).text(), "boom")

    def test_search_filter(self) -> None:
        self._append("attack started", LogLevel.INFO)
        self._append("village ready", LogLevel.INFO)
        self.view.search_edit.setText("attack")
        _APP.processEvents()
        self.assertEqual(self.view.table.rowCount(), 1)
        self.assertIn("attack", self.view.table.item(0, 2).text())

    def test_clear(self) -> None:
        self._append("one", LogLevel.INFO)
        self.view.clear_btn.click()
        _APP.processEvents()
        self.assertEqual(self.view.table.rowCount(), 0)


if __name__ == "__main__":
    unittest.main()
