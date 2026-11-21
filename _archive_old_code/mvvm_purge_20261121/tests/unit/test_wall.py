"""Unit tests for wall scanning and guarded upgrade execution."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from COCbot.core.config.coordinates import HR_VALIDATION_ROI, HR_WALL_ROI
from COCbot.features.village.wall import WallUpgrader
from COCbot.models.frame import Frame
from COCbot.models.geometry import Point


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

    def __init__(self, frame: Frame) -> None:
        self.frame = frame

    def capture(self) -> Frame:
        return self.frame


class WallUpgraderTests(unittest.TestCase):
    """Verify template scan, dry-run, and validated execution."""

    def test_scan_and_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            level_dir = root / "17"
            level_dir.mkdir()
            rng = np.random.default_rng(5)
            template = rng.integers(0, 255, size=(24, 24, 3), dtype=np.uint8)
            cv2.imwrite(str(level_dir / "2.png"), template)

            image = np.zeros((732, 860, 3), dtype=np.uint8)
            image[
                HR_WALL_ROI.y + 100 : HR_WALL_ROI.y + 124,
                HR_WALL_ROI.x + 120 : HR_WALL_ROI.x + 144,
            ] = template
            frame = Frame(image=image, width=860, height=732)
            adb = FakeAdb()
            upgrader = WallUpgrader(
                adb,  # type: ignore[arg-type]
                FakeCapture(frame),  # type: ignore[arg-type]
                clock=FakeClock(),
                walls_dir=root,
                execute=False,
            )
            scan = upgrader.scan(frame, 17)
            self.assertTrue(scan.points)
            result = upgrader.execute(scan.points[0], "gold", 17)
            self.assertFalse(result.executed)
            self.assertEqual(adb.taps, [])

    def test_validated_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            level_dir = root / "17"
            validation_dir = level_dir / "Validate_Upgrade"
            validation_dir.mkdir(parents=True)
            rng = np.random.default_rng(9)
            template = rng.integers(0, 255, size=(30, 30, 3), dtype=np.uint8)
            cv2.imwrite(str(validation_dir / "verify_wall_level.png"), template)

            image = np.zeros((732, 860, 3), dtype=np.uint8)
            image[
                HR_VALIDATION_ROI.y + 50 : HR_VALIDATION_ROI.y + 80,
                HR_VALIDATION_ROI.x + 100 : HR_VALIDATION_ROI.x + 130,
            ] = template
            frame = Frame(image=image, width=860, height=732)
            adb = FakeAdb()
            upgrader = WallUpgrader(
                adb,  # type: ignore[arg-type]
                FakeCapture(frame),  # type: ignore[arg-type]
                clock=FakeClock(),
                walls_dir=root,
                execute=True,
            )
            result = upgrader.execute(Point(400, 300), "gold", 17)
            self.assertTrue(result.executed)
            self.assertGreaterEqual(result.validation, 0.88)
            self.assertEqual(len(adb.taps), 5)


if __name__ == "__main__":
    unittest.main()
