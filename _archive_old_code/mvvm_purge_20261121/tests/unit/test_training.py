"""Unit tests for the quick-train feature."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from COCbot.app.session import BotSession
from COCbot.features.training.model import TrainingActions, TrainingStep
from COCbot.models.attack import Detection
from COCbot.models.frame import Frame
from COCbot.models.geometry import BoundingBox


class FakeClock:
    """No-op clock."""

    def now(self) -> float:
        return 0.0

    def monotonic(self) -> float:
        return 0.0

    def sleep(self, seconds: float) -> None:
        pass


class FakeAdb:
    """Record taps."""

    def __init__(self) -> None:
        self.taps: list[tuple[int, int]] = []

    def tap(self, x: int, y: int) -> bool:
        self.taps.append((x, y))
        return True


class FakeCapture:
    """Return a fixed frame."""

    def capture(self) -> Frame:
        return Frame(image=object(), width=860, height=732)


class FakeMatcher:
    """Return matches for the use and recipe-window templates."""

    def match(self, frame, name, region=None, threshold=None):
        if name.endswith("edit_army_btn.png"):
            return Detection("edit", 0.95, BoundingBox(50, 690, 100, 720))
        if name.endswith("army_window.png"):
            return Detection("window", 0.95, BoundingBox(80, 175, 300, 205))
        if name.endswith("use_button.png"):
            return Detection("use", 0.95, BoundingBox(740, 200, 800, 240))
        if name.endswith("use_army_recipe_window.png"):
            return Detection("window", 0.95, BoundingBox(300, 300, 600, 500))
        return None


class TrainingTests(unittest.TestCase):
    """Verify dry-run, execution taps, and the CycleStep result."""

    def _actions(self, execute: bool) -> tuple[TrainingActions, FakeAdb]:
        adb = FakeAdb()
        actions = TrainingActions(
            adb,  # type: ignore[arg-type]
            FakeCapture(),  # type: ignore[arg-type]
            FakeMatcher(),  # type: ignore[arg-type]
            clock=FakeClock(),
            execute=execute,
        )
        return actions, adb

    def test_dry_run(self) -> None:
        actions, adb = self._actions(False)
        result = actions.quick_train(1)
        self.assertTrue(result.ok)
        self.assertEqual(result.taps, 0)
        self.assertEqual(adb.taps, [])

    def test_execute(self) -> None:
        actions, adb = self._actions(True)
        result = actions.quick_train(1)
        self.assertTrue(result.ok)
        self.assertGreaterEqual(result.taps, 5)
        self.assertGreaterEqual(len(adb.taps), 5)

    def test_step(self) -> None:
        actions, _ = self._actions(False)
        result = TrainingStep(actions, slot=1).run(
            SimpleNamespace(session=BotSession())
        )
        self.assertTrue(result.success)
        self.assertEqual(result.data["slot"], 1)


if __name__ == "__main__":
    unittest.main()
