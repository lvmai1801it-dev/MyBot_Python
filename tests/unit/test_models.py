"""Unit tests for pure domain models."""

from __future__ import annotations

import unittest

from COCbot.models.attack import AttackPlan, AttackResult, Detection
from COCbot.models.bot_state import Progress
from COCbot.models.emulator import EmulatorInstance
from COCbot.models.enums import AttackSide, EmulatorType, ResourceKind
from COCbot.models.frame import Frame
from COCbot.models.geometry import BoundingBox, Point, Rect
from COCbot.models.resources import ResourceSnapshot


class GeometryTests(unittest.TestCase):
    """Verify rectangle and bounding-box helpers."""

    def test_rect_center_and_contains(self) -> None:
        rect = Rect(10, 20, 100, 50)
        self.assertEqual(rect.center, Point(60, 45))
        self.assertTrue(rect.contains(Point(10, 20)))
        self.assertFalse(rect.contains(Point(110, 20)))
        self.assertEqual(rect.as_xyxy(), (10, 20, 110, 70))

    def test_bounding_box_iou(self) -> None:
        first = BoundingBox(0, 0, 10, 10)
        second = BoundingBox(5, 5, 15, 15)
        self.assertAlmostEqual(first.iou(second), 25 / 175)
        self.assertAlmostEqual(first.iou(first), 1.0)
        self.assertEqual(first.center, Point(5, 5))

    def test_bounding_box_rejects_inverted(self) -> None:
        with self.assertRaises(ValueError):
            BoundingBox(10, 10, 5, 20)


class ResourceTests(unittest.TestCase):
    """Verify resource snapshots and loot deltas."""

    def test_fill_ratio_and_full(self) -> None:
        snapshot = ResourceSnapshot(gold=990, gold_capacity=1000)
        self.assertAlmostEqual(snapshot.fill_ratio(ResourceKind.GOLD), 0.99)
        self.assertTrue(snapshot.is_full(ResourceKind.GOLD))
        self.assertFalse(snapshot.is_full(ResourceKind.ELIXIR))

    def test_loot_gain_is_non_negative(self) -> None:
        before = ResourceSnapshot(gold=100, elixir=100)
        after = ResourceSnapshot(gold=50, elixir=250)
        gain = after.loot_gain(before)
        self.assertEqual(gain.gold, 0)
        self.assertEqual(gain.elixir, 150)

    def test_total(self) -> None:
        self.assertEqual(ResourceSnapshot(gold=1, elixir=2, dark_elixir=3).total(), 6)


class MiscModelTests(unittest.TestCase):
    """Verify enums, progress, frames, and attack results."""

    def test_progress_percent(self) -> None:
        self.assertEqual(Progress(1, 4).percent, 25)
        self.assertEqual(Progress(10, 4).percent, 100)
        self.assertEqual(Progress(0, 0).percent, 0)
        self.assertTrue(Progress(4, 4).is_complete)

    def test_enum_aliases(self) -> None:
        self.assertEqual(EmulatorType.from_value("LDPlayer"), EmulatorType.LDPLAYER)
        self.assertEqual(EmulatorType.from_value("blue-stacks"), EmulatorType.BLUESTACKS)
        self.assertEqual(AttackSide.from_value("Ngẫu nhiên"), AttackSide.RANDOM)
        self.assertEqual(AttackSide.from_value("Trên Trái (TL)"), AttackSide.TOP_LEFT)
        self.assertEqual(AttackSide.from_value("Nửa Dưới (BL + BR)"), AttackSide.BOTTOM)

    def test_frame(self) -> None:
        frame = Frame(image=object(), width=860, height=732, captured_at=100.0)
        self.assertFalse(frame.is_empty())
        self.assertEqual(frame.age(now=105.0), 5.0)
        self.assertTrue(Frame(image=None, width=0, height=0).is_empty())

    def test_attack_plan_units(self) -> None:
        plan = AttackPlan(troops={"dragon": 2}, spells={"rage": 1})
        self.assertEqual(plan.total_units(), 3)
        self.assertFalse(plan.is_empty())

    def test_attack_result_victory(self) -> None:
        self.assertTrue(AttackResult(success=True, stars=2).is_victory)
        self.assertFalse(AttackResult(success=True, stars=0).is_victory)

    def test_detection_center(self) -> None:
        detection = Detection("town_hall", 0.9, BoundingBox(0, 0, 10, 20))
        self.assertEqual(detection.center(), Point(5, 10))

    def test_emulator_instance_fallback(self) -> None:
        instance = EmulatorInstance(index=2, name="")
        self.assertEqual(instance.display_name(), "Instance 2")
        self.assertEqual(instance.connect_host(), "127.0.0.1:5557")


if __name__ == "__main__":
    unittest.main()
