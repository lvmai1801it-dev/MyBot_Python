"""Unit tests for the clean-port army scanner and attack executor."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from COCbot.app.orchestrator import BotSession, CycleContext
from COCbot.features.attack.army_bar import ArmyBarScanner, ArmySlot, ArmySlotKind
from COCbot.features.attack.battle import BattleService
from COCbot.features.attack.executor import AttackExecutor, spread_points
from COCbot.models.attack import AttackPlan, Detection, RedlineResult
from COCbot.models.frame import Frame
from COCbot.models.geometry import BoundingBox, Point


class FakeClock:
    """No-op clock."""

    def now(self) -> float:
        return 0.0

    def monotonic(self) -> float:
        return 0.0

    def sleep(self, seconds: float) -> None:
        pass


class FakeOcr:
    """Return a fixed count for any badge."""

    def read_number(self, frame, region=None, max_value=None) -> int:
        return 5


class FakeAdb:
    """Record taps."""

    def __init__(self) -> None:
        self.taps: list[tuple[int, int]] = []

    def tap(self, x: int, y: int) -> bool:
        self.taps.append((x, y))
        return True


class FakeCapture:
    """Return a frame with a template placed in slot 0."""

    def __init__(self, frame: Frame) -> None:
        self.frame = frame

    def capture(self) -> Frame:
        return self.frame


class FakeMatcher:
    """Return scripted template matches."""

    def __init__(self, next_button: bool = True) -> None:
        self.next_button = next_button

    def match(self, frame, name, region=None, threshold=None):
        if name == "next_button.png" and self.next_button:
            return Detection("next", 0.9, BoundingBox(700, 560, 760, 600))
        return None


class ArmyBarScannerTests(unittest.TestCase):
    """Verify slot template matching and count OCR."""

    def test_scan_slot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            troops = root / "Smart_Auto_train" / "Army Troops"
            troops.mkdir(parents=True)
            rng = np.random.default_rng(7)
            template = rng.integers(0, 255, size=(45, 45, 3), dtype=np.uint8)
            self.assertTrue(cv2.imwrite(str(troops / "dragon.png"), template))

            frame_image = np.zeros((732, 860, 3), dtype=np.uint8)
            frame_image[663:708, 40:85] = template
            frame_image[638:658, 38:92] = (200, 40, 20)  # blue badge
            frame = Frame(image=frame_image, width=860, height=732)

            scanner = ArmyBarScanner(templates_dir=root, ocr=FakeOcr())
            slots = scanner.scan(frame)
            self.assertTrue(slots)
            self.assertEqual(slots[0].name, "dragon")
            self.assertEqual(slots[0].kind, ArmySlotKind.TROOP)
            self.assertEqual(slots[0].count, 5)


class AttackExecutorTests(unittest.TestCase):
    """Verify dry-run planning and real tap counts."""

    def _plan(self) -> AttackPlan:
        target = Detection("town_hall", 0.9, BoundingBox(400, 300, 460, 360))
        return AttackPlan(target=target, side="TR", troops={"dragon": 3})

    def _redline(self, inside_points: bool = False) -> RedlineResult:
        edge = (Point(400, 600), Point(425, 600), Point(450, 600))
        if inside_points:
            # A no-deploy polygon that wraps the deploy points themselves.
            polygon = (
                Point(380, 580),
                Point(470, 580),
                Point(470, 620),
                Point(380, 620),
            )
        else:
            # A far-away no-deploy polygon: the edge is safe to tap.
            polygon = (Point(100, 100), Point(160, 100), Point(160, 160), Point(100, 160))
        return RedlineResult(polygon=polygon, edges=(edge, edge, edge, edge), source="cv")

    def test_dry_run(self) -> None:
        adb = FakeAdb()
        executor = AttackExecutor(adb, clock=FakeClock(), execute=False)
        slots = [ArmySlot("dragon", 0, 3, ArmySlotKind.TROOP)]
        result = executor.deploy(self._plan(), self._redline(), slots)
        self.assertTrue(result.ok)
        self.assertEqual(result.planned, 3)
        self.assertEqual(result.taps, 0)
        self.assertEqual(adb.taps, [])

    def test_real_execute(self) -> None:
        adb = FakeAdb()
        executor = AttackExecutor(adb, clock=FakeClock(), execute=True)
        slots = [ArmySlot("dragon", 0, 3, ArmySlotKind.TROOP)]
        result = executor.deploy(self._plan(), self._redline(), slots)
        self.assertEqual(result.taps, 3)
        self.assertEqual(len(adb.taps), 6)  # 3 selects + 3 deploy taps

    def test_points_inside_the_no_deploy_zone_are_never_tapped(self) -> None:
        # Regression: ``contains`` means "inside the forbidden zone"; such
        # points must be skipped, not preferred.
        adb = FakeAdb()
        executor = AttackExecutor(adb, clock=FakeClock(), execute=True)
        slots = [ArmySlot("dragon", 0, 3, ArmySlotKind.TROOP)]
        result = executor.deploy(self._plan(), self._redline(inside_points=True), slots)
        self.assertTrue(result.ok)
        self.assertEqual(result.planned, 0)
        self.assertEqual(result.taps, 0)
        self.assertEqual(adb.taps, [])

    def test_heroes_inside_the_no_deploy_zone_are_skipped(self) -> None:
        adb = FakeAdb()
        executor = AttackExecutor(adb, clock=FakeClock(), execute=True)
        slots = [ArmySlot("King", 0, 1, ArmySlotKind.HERO)]
        result = executor.deploy(self._plan(), self._redline(inside_points=True), slots)
        self.assertEqual(result.planned, 0)
        self.assertEqual(adb.taps, [])

    def test_spread_points(self) -> None:
        edge = (Point(0, 0), Point(10, 0), Point(20, 0))
        points = spread_points(edge, 3)
        self.assertEqual(len(points), 3)
        self.assertEqual(points[0], Point(0, 0))


class BattleServiceTests(unittest.TestCase):
    """Verify next-button detection and loot reading."""

    def test_next_button_and_loot(self) -> None:
        frame = Frame(image=np.zeros((732, 860, 3), dtype=np.uint8), width=860, height=732)
        service = BattleService(
            FakeAdb(),  # type: ignore[arg-type]
            FakeCapture(frame),  # type: ignore[arg-type]
            FakeMatcher(),  # type: ignore[arg-type]
            ocr=FakeOcr(),  # type: ignore[arg-type]
            clock=FakeClock(),
            execute=False,
        )
        button = service.find_next_button()
        self.assertIsNotNone(button)
        loot = service.read_loot(stars=2)
        self.assertEqual(loot.gold, 10)
        self.assertEqual(loot.elixir, 10)
        self.assertEqual(loot.dark_elixir, 10)

    def test_read_loot_offer_without_ocr_returns_none(self) -> None:
        frame = Frame(image=np.zeros((732, 860, 3), dtype=np.uint8), width=860, height=732)
        service = BattleService(
            FakeAdb(),  # type: ignore[arg-type]
            FakeCapture(frame),  # type: ignore[arg-type]
            FakeMatcher(),  # type: ignore[arg-type]
            clock=FakeClock(),
            execute=False,
        )
        self.assertIsNone(service.read_loot_offer())


class FullAttackStepTests(unittest.TestCase):
    """Verify the legacy-parity loot threshold gate."""

    def _step(self, offers, thresholds):
        from COCbot.core.config.schema import AppConfig
        from COCbot.features.attack.battle import FullAttackStep
        from COCbot.models.resources import ResourceSnapshot

        class FakeBattle:
            def __init__(self):
                self.nexts = 0

            def return_home(self):
                pass

            def search_attack(self):
                pass

            def wait_for_scout(self, cancel):
                return True

            def read_loot_offer(self):
                return offers[min(self.nexts, len(offers) - 1)]

            def search_next(self):
                self.nexts += 1
                return True

            def capture(self):
                return None

            def wait_for_battle_end(self, cancel):
                return True

            def read_result(self):
                from COCbot.models.attack import AttackResult

                return AttackResult(success=True, stars=1)

            def warn(self, message):
                pass

        class FakeScan:
            frame = None
            plan = None
            redline = None

        class FakeAttack:
            def scan(self, cancel_event=None, progress=None):
                from COCbot.features.attack.model import AttackScan

                return AttackScan(
                    frame=Frame(image=np.zeros((4, 4, 3), np.uint8), width=4, height=4),
                    detections=(),
                    redline=RedlineResult(
                        polygon=(Point(0, 0), Point(4, 0), Point(4, 4), Point(0, 4)),
                        edges=((Point(9, 9), Point(9, 9), Point(9, 9)),) * 4,
                        source="onnx",
                    ),
                    plan=AttackPlan(),
                    duration=0.0,
                )

        class FakeScanner:
            def scan(self, frame):
                return [ArmySlot("dragon", 0, 3, ArmySlotKind.TROOP)]

        class FakeExecutor:
            def __init__(self):
                self.deployed = False

            def deploy(self, plan, redline, slots, execute=None, cancel_event=None,
                       activate_heroes=True):
                from COCbot.features.attack.executor import AttackExecutionResult

                self.deployed = True
                return AttackExecutionResult(True, planned=3, taps=0, message="planned")

        battle = FakeBattle()
        executor = FakeExecutor()
        config = AppConfig.from_legacy_dict(
            {
                "gold_threshold": thresholds[0],
                "elixir_threshold": thresholds[1],
                "dark_elixir_threshold": thresholds[2],
            }
        )
        step = FullAttackStep(FakeAttack(), battle, FakeScanner(), executor, execute=True)
        context = CycleContext(session=BotSession(), config=config)
        context.session.start()
        result = step.run(context)
        return result, battle, executor, FakeScan

    def test_below_threshold_nexts_until_good_base(self) -> None:
        from COCbot.models.resources import ResourceSnapshot

        offers = [
            ResourceSnapshot(gold=100, elixir=100, dark_elixir=0),
            ResourceSnapshot(gold=100, elixir=100, dark_elixir=0),
            ResourceSnapshot(gold=999, elixir=999, dark_elixir=99),
        ]
        result, battle, executor, _ = self._step(offers, (500, 500, 5))
        self.assertTrue(result.success)
        self.assertEqual(battle.nexts, 2)
        self.assertTrue(executor.deployed)

    def test_ocr_unavailable_attacks_current_base(self) -> None:
        offers = [None]
        result, battle, executor, _ = self._step(offers, (500, 500, 5))
        self.assertTrue(result.success)
        self.assertEqual(battle.nexts, 0)

    def test_max_nexts_attacks_current_base(self) -> None:
        from COCbot.models.resources import ResourceSnapshot

        offers = [ResourceSnapshot(gold=1, elixir=1, dark_elixir=0)]
        result, battle, executor, _ = self._step(offers, (500, 500, 5))
        self.assertTrue(result.success)
        self.assertGreaterEqual(battle.nexts, 1)


if __name__ == "__main__":
    unittest.main()
