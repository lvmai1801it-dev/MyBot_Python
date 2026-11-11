"""Offscreen GUI test for the always-visible resource bar."""

from __future__ import annotations

import time
import unittest

from PyQt5.QtWidgets import QApplication

from COCbot.features.village.resources import VillageResources
from COCbot.ui_components import apply_theme
from COCbot.viewmodels.resource_bar import ResourceBarViewModel
from COCbot.views.resource_bar import ResourceBar

_APP = QApplication.instance() or QApplication([])


class FakeReader:
    """Reader stub that never touches ADB."""

    def __init__(self) -> None:
        self.reads = 0

    def read(self) -> VillageResources:
        self.reads += 1
        return VillageResources(
            gold=16_000_000,
            elixir=13_086_862,
            dark_elixir=250_000,
            gems=1_497,
            builders_available=5,
            builders_total=5,
        )


class ResourceBarTests(unittest.TestCase):
    """Verify the bar renders each counter and the builder fraction."""

    def setUp(self) -> None:
        apply_theme(_APP)
        self.reader = FakeReader()
        self.viewmodel = ResourceBarViewModel(self.reader, interval=3600)
        self.bar = ResourceBar(self.viewmodel)
        self.bar.show()
        _APP.processEvents()

    def tearDown(self) -> None:
        self.bar.close()
        _APP.processEvents()

    def test_starts_empty(self) -> None:
        self.assertEqual(self.bar._values["gold"].text(), "—")
        self.assertEqual(self.bar._values["builders"].text(), "—")

    def test_apply_snapshot(self) -> None:
        self.viewmodel.snapshot_updated.emit(self.reader.read())
        _APP.processEvents()
        self.assertEqual(self.bar._values["gold"].text(), "16,000,000")
        self.assertEqual(self.bar._values["elixir"].text(), "13,086,862")
        self.assertEqual(self.bar._values["dark"].text(), "250,000")
        self.assertEqual(self.bar._values["gems"].text(), "1,497")
        self.assertEqual(self.bar._values["builders"].text(), "5/5")

    def test_poller_reads_off_thread(self) -> None:
        self.viewmodel.start()
        for _ in range(300):
            _APP.processEvents()
            if self.viewmodel.snapshot.gold is not None:
                break
            time.sleep(0.01)
        self.viewmodel.stop()
        self.assertEqual(self.viewmodel.snapshot.gold, 16_000_000)
        self.assertGreaterEqual(self.reader.reads, 1)


if __name__ == "__main__":
    unittest.main()
