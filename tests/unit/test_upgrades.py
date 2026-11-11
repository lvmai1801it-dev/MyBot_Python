"""Unit tests for the template-driven hero/defense upgrade flow."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from COCbot.features.village.upgrades import (
    DEFAULT_BUTTONS,
    HeroDefenseUpgrader,
    UpgradeTarget,
)
from COCbot.models.frame import Frame


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


class SequenceCapture:
    """Return frames in sequence, repeating the last one."""

    def __init__(self, frames: list[Frame]) -> None:
        self.frames = frames
        self.index = 0

    def capture(self) -> Frame:
        frame = self.frames[min(self.index, len(self.frames) - 1)]
        self.index += 1
        return frame


def frame_with(template: np.ndarray, x: int, y: int) -> Frame:
    """Place *template* at ``(x, y)`` on a blank 860x732 frame."""
    image = np.zeros((732, 860, 3), dtype=np.uint8)
    image[y : y + template.shape[0], x : x + template.shape[1]] = template
    return Frame(image=image, width=860, height=732)


class HeroDefenseUpgraderTests(unittest.TestCase):
    """Verify dry-run and template-validated execution."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.dir = Path(self._temp.name)
        rng = np.random.default_rng(21)
        self.target = rng.integers(0, 255, size=(30, 30, 3), dtype=np.uint8)
        self.upgrade = rng.integers(0, 255, size=(24, 24, 3), dtype=np.uint8)
        self.confirm = rng.integers(0, 255, size=(24, 24, 3), dtype=np.uint8)
        self.close = rng.integers(0, 255, size=(24, 24, 3), dtype=np.uint8)
        cv2.imwrite(str(self.dir / "hero_queen.png"), self.target)
        cv2.imwrite(str(self.dir / DEFAULT_BUTTONS["upgrade"]), self.upgrade)
        cv2.imwrite(str(self.dir / DEFAULT_BUTTONS["confirm"]), self.confirm)
        cv2.imwrite(str(self.dir / DEFAULT_BUTTONS["close"]), self.close)
        self.frames = [
            frame_with(self.target, 100, 100),
            frame_with(self.upgrade, 200, 200),
            frame_with(self.confirm, 300, 300),
            frame_with(self.close, 400, 400),
        ]

    def tearDown(self) -> None:
        self._temp.cleanup()

    def _upgrader(self, execute: bool) -> tuple[HeroDefenseUpgrader, FakeAdb]:
        adb = FakeAdb()
        upgrader = HeroDefenseUpgrader(
            adb,  # type: ignore[arg-type]
            SequenceCapture(self.frames),  # type: ignore[arg-type]
            clock=FakeClock(),
            template_dir=self.dir,
            targets=(UpgradeTarget("Queen", "hero", "hero_queen.png"),),
            execute=execute,
        )
        return upgrader, adb

    def test_available_and_dry_run(self) -> None:
        upgrader, adb = self._upgrader(execute=False)
        self.assertEqual(upgrader.available_targets(), ["Queen"])
        result = upgrader.execute("Queen")
        self.assertTrue(result.ok)
        self.assertFalse(result.executed)
        self.assertEqual(adb.taps, [])

    def test_execute(self) -> None:
        upgrader, adb = self._upgrader(execute=True)
        result = upgrader.execute("Queen")
        self.assertTrue(result.ok)
        self.assertTrue(result.executed)
        self.assertEqual(result.taps, 4)
        self.assertEqual(len(adb.taps), 4)


if __name__ == "__main__":
    unittest.main()
