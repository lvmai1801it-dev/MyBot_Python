"""Unit tests for the template + OCR driven hero/defense upgrade flow."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from COCbot.features.village.upgrades import (
    DEFAULT_BUTTONS,
    DIALOG_TITLE_REGION,
    PANEL_TITLE_REGION,
    HeroDefenseUpgrader,
    UpgradeRow,
    UpgradeTarget,
)
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
    """Record taps and swipes."""

    def __init__(self) -> None:
        self.taps: list[tuple[int, int]] = []
        self.swipes: list[tuple[int, int, int, int]] = []

    def tap(self, x: int, y: int) -> bool:
        self.taps.append((x, y))
        return True

    def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration_ms: int = 300,
    ) -> bool:
        self.swipes.append((x1, y1, x2, y2))
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


class FakeText:
    """Return canned OCR text per screen region."""

    def __init__(self, mapping: dict[object, str]) -> None:
        self.mapping = mapping

    def __call__(self, frame: Frame, region: object) -> str:
        return self.mapping.get(region, "")


class HeroDefenseUpgraderTests(unittest.TestCase):
    """Verify dry-run, row matching, and the guarded confirm step."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.dir = Path(self._temp.name)
        (self.dir / "hero").mkdir()
        rng = np.random.default_rng(21)
        self.portrait = rng.integers(0, 255, size=(30, 30, 3), dtype=np.uint8)
        self.upgrade = rng.integers(0, 255, size=(24, 24, 3), dtype=np.uint8)
        self.confirm = rng.integers(0, 255, size=(24, 24, 3), dtype=np.uint8)
        self.close = rng.integers(0, 255, size=(24, 24, 3), dtype=np.uint8)
        cv2.imwrite(str(self.dir / "hero" / "queen.png"), self.portrait)
        cv2.imwrite(str(self.dir / DEFAULT_BUTTONS["upgrade"]), self.upgrade)
        cv2.imwrite(str(self.dir / DEFAULT_BUTTONS["confirm"]), self.confirm)
        cv2.imwrite(str(self.dir / DEFAULT_BUTTONS["close"]), self.close)
        self.rows = [UpgradeRow("Archer Queen", Point(620, 118))]
        self.panel_frame = frame_with(self.upgrade, 200, 600)
        self.dialog_frame = frame_with(self.confirm, 300, 300)
        self.done_frame = frame_with(self.close, 800, 130)

    def tearDown(self) -> None:
        self._temp.cleanup()

    def _upgrader(
        self,
        execute: bool,
        frames: list[Frame],
        text: dict[object, str] | None = None,
        rows: list[UpgradeRow] | None = None,
    ) -> tuple[HeroDefenseUpgrader, FakeAdb]:
        adb = FakeAdb()
        mapping = {
            PANEL_TITLE_REGION: "buildings & heroes",
            DIALOG_TITLE_REGION: "upgrade archer queen to level 70?",
        }
        if text is not None:
            mapping.update(text)
        upgrader = HeroDefenseUpgrader(
            adb,  # type: ignore[arg-type]
            SequenceCapture(frames),  # type: ignore[arg-type]
            clock=FakeClock(),
            template_dir=self.dir,
            targets=(UpgradeTarget("Archer Queen", "hero", "hero/queen.png"),),
            execute=execute,
            rows_provider=lambda _frame: self.rows if rows is None else rows,
            text_reader=FakeText(mapping),
        )
        return upgrader, adb

    def test_available_targets(self) -> None:
        upgrader, _ = self._upgrader(False, [self.panel_frame])
        self.assertEqual(upgrader.available_targets(), ["Archer Queen"])

    def test_dry_run_plans_without_tapping(self) -> None:
        upgrader, adb = self._upgrader(False, [self.panel_frame, self.dialog_frame])
        result = upgrader.execute("Archer Queen")
        self.assertTrue(result.ok)
        self.assertFalse(result.executed)
        self.assertEqual(result.target, "Archer Queen")
        self.assertIn("would open Archer Queen", result.message)
        self.assertEqual(adb.taps, [])

    def test_dry_run_when_panel_closed(self) -> None:
        upgrader, adb = self._upgrader(
            False,
            [self.panel_frame],
            text={PANEL_TITLE_REGION: ""},
        )
        result = upgrader.execute("Archer Queen")
        self.assertTrue(result.ok)
        self.assertIn("would open the Buildings & Heroes panel", result.message)
        self.assertEqual(adb.taps, [])

    def test_missing_target_reports_rows(self) -> None:
        upgrader, adb = self._upgrader(False, [self.panel_frame])
        result = upgrader.execute("Monolith")
        self.assertFalse(result.ok)
        self.assertIn("Archer Queen", result.message)
        self.assertEqual(adb.taps, [])

    def test_execute_confirms_and_closes(self) -> None:
        upgrader, adb = self._upgrader(
            True,
            [self.panel_frame, self.dialog_frame, self.done_frame],
        )
        result = upgrader.execute("Archer Queen")
        self.assertTrue(result.ok, result.message)
        self.assertTrue(result.executed)
        self.assertEqual(result.taps, 3)
        self.assertEqual(adb.taps[0], (620, 118))
        self.assertEqual(len(adb.taps), 3)

    def test_title_mismatch_blocks_confirm(self) -> None:
        upgrader, adb = self._upgrader(
            True,
            [self.panel_frame, self.dialog_frame],
            text={DIALOG_TITLE_REGION: "upgrade elixir collector to level 6?"},
        )
        result = upgrader.execute("Archer Queen")
        self.assertFalse(result.ok)
        self.assertIn("does not mention", result.message)
        self.assertEqual(result.taps, 1)
        self.assertEqual(len(adb.taps), 1)

    def test_missing_confirm_template_blocks_tap(self) -> None:
        upgrader, adb = self._upgrader(
            True,
            [self.panel_frame, self.panel_frame],
        )
        result = upgrader.execute("Archer Queen")
        self.assertFalse(result.ok)
        self.assertIn("Confirm button template not found", result.message)
        self.assertEqual(result.taps, 1)
        self.assertEqual(len(adb.taps), 1)

    def test_label_template_overrides_ocr_name(self) -> None:
        labels = Path(self._temp.name) / "buildings"
        labels.mkdir()
        rng = np.random.default_rng(33)
        label = rng.integers(0, 255, size=(16, 90, 3), dtype=np.uint8)
        cv2.imwrite(str(labels / "grandwarden.png"), label)
        image = np.zeros((732, 860, 3), dtype=np.uint8)
        image[200 : 200 + label.shape[0], 600 : 600 + label.shape[1]] = label
        frame = Frame(image=image, width=860, height=732)
        upgrader = HeroDefenseUpgrader(
            FakeAdb(),  # type: ignore[arg-type]
            SequenceCapture([frame, frame]),  # type: ignore[arg-type]
            clock=FakeClock(),
            template_dir=self.dir,
            label_dir=labels,
            execute=False,
            rows_provider=lambda _frame: [UpgradeRow("Brand Warden", Point(620, 200))],
            text_reader=FakeText({PANEL_TITLE_REGION: "buildings & heroes"}),
        )
        names = [row.name for row in upgrader.rows(frame)]
        self.assertIn("Grand Warden", names)

    def test_label_title_marks_panel_open(self) -> None:
        labels = Path(self._temp.name) / "buildings"
        labels.mkdir()
        rng = np.random.default_rng(44)
        title = rng.integers(0, 255, size=(18, 160, 3), dtype=np.uint8)
        cv2.imwrite(str(labels / "Buildings&Heroes.png"), title)
        image = np.zeros((732, 860, 3), dtype=np.uint8)
        image[60 : 60 + title.shape[0], 560 : 560 + title.shape[1]] = title
        frame = Frame(image=image, width=860, height=732)
        upgrader = HeroDefenseUpgrader(
            FakeAdb(),  # type: ignore[arg-type]
            SequenceCapture([frame]),  # type: ignore[arg-type]
            clock=FakeClock(),
            template_dir=self.dir,
            label_dir=labels,
            text_reader=FakeText({}),
        )
        self.assertTrue(upgrader.panel_open(frame))

    def test_scan_reads_one_page_without_tapping_when_dry(self) -> None:
        frames = [
            frame_with(self.close, 800, 130),
            frame_with(self.close, 800, 130),
        ]
        upgrader, adb = self._upgrader(False, frames)
        rows = upgrader.scan_rows(execute=False)
        self.assertEqual([row.name for row in rows], ["Archer Queen"])
        self.assertEqual(adb.swipes, [])
        self.assertEqual(adb.taps, [])

    def test_dismiss_falls_back_to_the_corner_button(self) -> None:
        frame = frame_with(self.upgrade, 200, 600)
        upgrader, adb = self._upgrader(
            True,
            [frame, frame],
            text={PANEL_TITLE_REGION: "buildings & heroes"},
        )
        self.assertTrue(upgrader.dismiss(execute=True))
        self.assertEqual(adb.taps, [(824, 30)])


if __name__ == "__main__":
    unittest.main()
