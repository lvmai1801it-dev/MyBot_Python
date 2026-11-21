"""Offscreen GUI smoke test for the statistics feature."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from COCbot.features.statistics.model import StatisticsModel
from COCbot.features.statistics.view import StatisticsView
from COCbot.features.statistics.viewmodel import StatisticsViewModel
from COCbot.ui_components import apply_theme

_APP = QApplication.instance() or QApplication([])


class StatisticsViewTests(unittest.TestCase):
    """Verify totals, table rows, and reset rendering."""

    def setUp(self) -> None:
        apply_theme(_APP)
        self._temp = tempfile.TemporaryDirectory()
        self.dir = Path(self._temp.name)
        (self.dir / "Stats_1.json").write_text(
            json.dumps(
                {
                    "gold": 12345,
                    "elixir": 67890,
                    "de": 500,
                    "attacks": 4,
                    "stars": {"0": 0, "1": 1, "2": 1, "3": 2},
                    "last_update_ts": 1_700_000_000,
                }
            ),
            encoding="utf-8",
        )
        self.model = StatisticsModel(self.dir, max_villages=5)
        self.vm = StatisticsViewModel(self.model)
        self.view = StatisticsView(self.vm)
        self.view.show()
        _APP.processEvents()

    def tearDown(self) -> None:
        self.view.close()
        self.view.deleteLater()
        _APP.processEvents()
        self._temp.cleanup()

    def test_totals_and_table(self) -> None:
        self.assertEqual(self.view.value_labels["gold"].text(), "12,345")
        self.assertEqual(self.view.value_labels["attacks"].text(), "4")
        self.assertEqual(self.view.value_labels["stars"].text(), "4")
        self.assertEqual(self.view.table.rowCount(), 5)
        self.assertEqual(self.view.table.item(0, 1).text(), "12,345")

    def test_reset_renders_zero(self) -> None:
        self.vm.reset()
        _APP.processEvents()
        self.assertEqual(self.view.value_labels["gold"].text(), "0")
        self.assertEqual(self.view.value_labels["attacks"].text(), "0")


if __name__ == "__main__":
    unittest.main()
