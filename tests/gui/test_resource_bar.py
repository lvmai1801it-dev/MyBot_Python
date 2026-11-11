"""Offscreen GUI test for the always-visible resource bar."""

from __future__ import annotations

import unittest

from PyQt5.QtWidgets import QApplication

from COCbot.features.village.resources import VillageResources
from COCbot.ui_components import apply_theme
from COCbot.viewmodels.resource_bar import ResourceBarViewModel
from COCbot.views.resource_bar import ResourceBar

_APP = QApplication.instance() or QApplication([])


def sample() -> VillageResources:
    """Return a full live-looking snapshot."""
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
        self.viewmodel = ResourceBarViewModel()
        self.bar = ResourceBar(self.viewmodel)
        self.bar.show()
        _APP.processEvents()

    def tearDown(self) -> None:
        self.bar.close()
        _APP.processEvents()

    def test_empty_until_the_bot_publishes(self) -> None:
        self.assertEqual(self.bar._values["gold"].text(), "—")
        self.assertEqual(self.bar._values["builders"].text(), "—")
        self.assertEqual(self.viewmodel.snapshot, VillageResources())

    def test_apply_snapshot(self) -> None:
        self.viewmodel.publish(sample())
        _APP.processEvents()
        self.assertEqual(self.bar._values["gold"].text(), "16,000,000")
        self.assertEqual(self.bar._values["elixir"].text(), "13,086,862")
        self.assertEqual(self.bar._values["dark"].text(), "250,000")
        self.assertEqual(self.bar._values["gems"].text(), "1,497")
        self.assertEqual(self.bar._values["builders"].text(), "5/5")

    def test_start_clears_previous_values(self) -> None:
        self.viewmodel.publish(sample())
        _APP.processEvents()
        self.viewmodel.on_running_changed(True)
        _APP.processEvents()
        self.assertEqual(self.bar._values["gold"].text(), "—")
        self.assertEqual(self.bar._values["builders"].text(), "—")

    def test_ignores_non_snapshot_values(self) -> None:
        self.viewmodel.publish({"gold": 5})
        self.assertEqual(self.viewmodel.snapshot, VillageResources())


if __name__ == "__main__":
    unittest.main()
