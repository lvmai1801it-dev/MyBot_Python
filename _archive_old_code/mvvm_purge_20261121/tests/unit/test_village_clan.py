"""Unit tests for the village and clan config features."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PyQt5.QtWidgets import QApplication

from COCbot.app.session import BotSession
from COCbot.core.config import AppConfig, ConfigStore, load_config
from COCbot.features.clan.model import ClanModel
from COCbot.features.clan.viewmodel import ClanViewModel
from COCbot.features.settings.model import SettingsModel
from COCbot.features.village.model import (
    VillageActions,
    VillageModel,
    VillageStep,
)
from COCbot.features.village.viewmodel import VillageViewModel
from COCbot.models.attack import Detection
from COCbot.models.enums import UpgradeCategory
from COCbot.models.frame import Frame
from COCbot.models.geometry import BoundingBox

_APP = QApplication.instance() or QApplication([])


class VillageFeatureTests(unittest.TestCase):
    """Verify wall/priority draft edits and persistence."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.path = Path(self._temp.name) / "settings.json"
        self.settings = SettingsModel(self.path)
        self.store = ConfigStore(AppConfig())
        self.model = VillageModel(self.store, self.settings)
        self.vm = VillageViewModel(self.model)

    def tearDown(self) -> None:
        self._temp.cleanup()

    def test_defaults_and_save(self) -> None:
        self.vm.load()
        self.assertFalse(self.vm.is_dirty)
        self.vm.set_wall(True, 12, 4_000_000, 3_000_000)
        self.vm.set_priority(UpgradeCategory.HERO, True, ["Queen", "King"])
        self.assertTrue(self.vm.is_dirty)
        self.assertTrue(self.vm.save())
        self.assertFalse(self.vm.is_dirty)

        loaded = load_config(self.path)
        self.assertTrue(loaded.upgrades.wall.enabled)
        self.assertEqual(loaded.upgrades.wall.level, 12)
        self.assertEqual(loaded.upgrades.hero.priorities, ["Queen", "King"])
        self.assertTrue(self.store.get().upgrades.wall.enabled)

    def test_reset_defaults(self) -> None:
        self.vm.load()
        self.vm.set_wall(True, 15, 1, 1)
        self.vm.save()
        self.vm.reset_defaults()
        self.assertTrue(self.vm.is_dirty)
        self.assertEqual(self.vm.config.wall.level, AppConfig().upgrades.wall.level)


class ClanFeatureTests(unittest.TestCase):
    """Verify clan toggles and persistence."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.path = Path(self._temp.name) / "settings.json"
        self.settings = SettingsModel(self.path)
        self.store = ConfigStore(AppConfig())
        self.model = ClanModel(self.store, self.settings)
        self.vm = ClanViewModel(self.model)

    def tearDown(self) -> None:
        self._temp.cleanup()

    def test_save(self) -> None:
        self.vm.load()
        self.vm.set_options(True, True, 10, False)
        self.assertTrue(self.vm.is_dirty)
        self.assertTrue(self.vm.save())
        loaded = load_config(self.path)
        self.assertTrue(loaded.clan.enable_clan_games)
        self.assertTrue(loaded.clan.enable_clan_capital)
        self.assertEqual(loaded.clan.capital_hall_level, 10)
        self.assertFalse(loaded.clan.request_troops)
        self.assertEqual(self.store.get().clan.capital_hall_level, 10)

    def test_reset_defaults(self) -> None:
        self.vm.load()
        self.vm.set_options(True, True, 15, False)
        self.vm.save()
        self.vm.reset_defaults()
        self.assertTrue(self.vm.is_dirty)
        self.assertEqual(self.vm.config.capital_hall_level, AppConfig().clan.capital_hall_level)


class FakeClock:
    """No-op clock for the village routine."""

    def now(self) -> float:
        return 0.0

    def monotonic(self) -> float:
        return 0.0

    def sleep(self, seconds: float) -> None:
        pass


class FakeCapture:
    """Capture stub returning a fixed frame."""

    def capture(self) -> Frame:
        return Frame(image=object(), width=860, height=732)


class FakeMatcher:
    """Return two gold-collector matches."""

    def match_all(self, frame, name, region=None, threshold=None, limit=20):
        if name == "gold_collector.png":
            return [
                Detection("gold", 0.9, BoundingBox(10, 20, 40, 50)),
                Detection("gold", 0.8, BoundingBox(60, 70, 90, 100)),
            ]
        return []


class FakeAdb:
    """Record taps."""

    def __init__(self) -> None:
        self.taps: list[tuple[int, int]] = []

    def tap(self, x: int, y: int) -> bool:
        self.taps.append((x, y))
        return True


class FakeMultiTouch:
    """Record pinch gestures."""

    def __init__(self) -> None:
        self.calls = 0

    def pinch_in(self, percent: int = 100, steps: int = 20) -> bool:
        self.calls += 1
        return True


class VillageActionsTests(unittest.TestCase):
    """Verify dry-run and real collector tapping."""

    def test_dry_run_taps_nothing(self) -> None:
        adb = FakeAdb()
        actions = VillageActions(
            adb,
            FakeCapture(),  # type: ignore[arg-type]
            FakeMatcher(),  # type: ignore[arg-type]
            clock=FakeClock(),
            execute=False,
        )
        result = actions.run()
        self.assertTrue(result.ok)
        self.assertEqual(result.found, 2)
        self.assertEqual(result.tapped, 0)
        self.assertEqual(adb.taps, [])

    def test_execute_taps_home_and_collectors(self) -> None:
        adb = FakeAdb()
        actions = VillageActions(
            adb,
            FakeCapture(),  # type: ignore[arg-type]
            FakeMatcher(),  # type: ignore[arg-type]
            clock=FakeClock(),
            execute=True,
        )
        result = actions.run()
        self.assertEqual(result.tapped, 2)
        self.assertEqual(len(adb.taps), 3)  # home + 2 collectors

    def test_village_step(self) -> None:
        actions = VillageActions(
            FakeAdb(),  # type: ignore[arg-type]
            FakeCapture(),  # type: ignore[arg-type]
            FakeMatcher(),  # type: ignore[arg-type]
            clock=FakeClock(),
            execute=False,
        )
        result = VillageStep(actions).run(SimpleNamespace(session=BotSession()))
        self.assertTrue(result.success)
        self.assertIn("collectors", result.message)

    def test_zoom_out_dry_run_and_execute(self) -> None:
        multitouch = FakeMultiTouch()
        dry = VillageActions(
            FakeAdb(),  # type: ignore[arg-type]
            FakeCapture(),  # type: ignore[arg-type]
            FakeMatcher(),  # type: ignore[arg-type]
            clock=FakeClock(),
            multitouch=multitouch,  # type: ignore[arg-type]
            execute=False,
        )
        self.assertFalse(dry.zoom_out(3))
        self.assertEqual(multitouch.calls, 0)

        live = VillageActions(
            FakeAdb(),  # type: ignore[arg-type]
            FakeCapture(),  # type: ignore[arg-type]
            FakeMatcher(),  # type: ignore[arg-type]
            clock=FakeClock(),
            multitouch=multitouch,  # type: ignore[arg-type]
            execute=True,
        )
        self.assertTrue(live.zoom_out(3))
        self.assertEqual(multitouch.calls, 3)


if __name__ == "__main__":
    unittest.main()
