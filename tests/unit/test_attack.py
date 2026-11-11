"""Unit tests for the attack feature model and view-model."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from PyQt5.QtWidgets import QApplication

from COCbot.app.session import BotSession
from COCbot.features.attack.model import AttackModel, AttackScan, AttackStep
from COCbot.features.attack.viewmodel import AttackViewModel
from COCbot.models.attack import AttackPlan, Detection, RedlineResult
from COCbot.models.frame import Frame
from COCbot.models.geometry import BoundingBox, Point

_APP = QApplication.instance() or QApplication([])


def make_redline() -> RedlineResult:
    """Return four valid deploy edges."""
    edge = (Point(400, 600), Point(425, 600), Point(450, 600))
    return RedlineResult(
        polygon=(Point(425, 150), Point(700, 345), Point(425, 540), Point(150, 345)),
        edges=(edge, edge, edge, edge),
        source="cv",
    )


class FakeCapture:
    """Capture stub returning a pre-built frame."""

    def __init__(self, frame: Frame) -> None:
        self.frame = frame
        self.calls = 0

    def capture(self) -> Frame:
        self.calls += 1
        return self.frame


class FakeDetector:
    """Detector stub returning fixed detections."""

    def __init__(self, detections: list[Detection]) -> None:
        self.detections = detections

    def detect(self, frame: Frame, confidence: float | None = None):
        return list(self.detections)


class FakeAdb:
    """Record taps."""

    def __init__(self) -> None:
        self.taps: list[tuple[int, int]] = []

    def tap(self, x: int, y: int) -> bool:
        self.taps.append((x, y))
        return True


class FakeRedline:
    """Redline detector stub."""

    def __init__(self, result: RedlineResult) -> None:
        self.result = result

    def detect(self, frame: Frame) -> RedlineResult:
        return self.result


class AttackModelTests(unittest.TestCase):
    """Verify plan ranking, progress, and deployment safety."""

    def setUp(self) -> None:
        self.frame = Frame(image=object(), width=860, height=732)
        self.detections = [
            Detection("archer_tower", 0.90, BoundingBox(10, 10, 30, 30)),
            Detection("town_hall", 0.80, BoundingBox(400, 300, 460, 360)),
        ]
        self.redline = make_redline()
        self.adb = FakeAdb()

    def model(self, allow_input: bool = False) -> AttackModel:
        return AttackModel(
            capture=FakeCapture(self.frame),
            detector=FakeDetector(self.detections),
            redline=FakeRedline(self.redline),
            adb=self.adb,
            allow_input=allow_input,
        )

    def test_scan_prefers_high_value_target(self) -> None:
        progress: list[tuple[int, int, str]] = []
        scan = self.model().scan(progress=lambda c, t, m: progress.append((c, t, m)))
        self.assertIsNotNone(scan.plan.target)
        assert scan.plan.target is not None
        self.assertEqual(scan.plan.target.label, "town_hall")
        self.assertEqual(scan.source, "cv")
        self.assertEqual(len(progress), 5)
        self.assertEqual(progress[-1][0], 4)

    def test_dry_run_sends_no_taps(self) -> None:
        model = self.model(allow_input=True)
        scan = model.scan()
        self.assertEqual(model.deploy(scan.plan, scan.redline, dry_run=True), 0)
        self.assertEqual(self.adb.taps, [])

    def test_real_deploy_taps_selected_edge(self) -> None:
        model = self.model(allow_input=True)
        scan = model.scan()
        taps = model.deploy(scan.plan, scan.redline, dry_run=False)
        self.assertEqual(taps, 3)
        self.assertEqual(len(self.adb.taps), 3)

    def test_capture_failure_raises(self) -> None:
        model = AttackModel(
            capture=FakeCapture(None),  # type: ignore[arg-type]
            detector=FakeDetector([]),
            redline=FakeRedline(self.redline),
        )
        with self.assertRaises(Exception):
            model.scan()

    def test_attack_step(self) -> None:
        step = AttackStep(self.model())
        result = step.run(SimpleNamespace(session=BotSession()))
        self.assertTrue(result.success)
        self.assertIn("town_hall", result.message)


class FakeAttackModel:
    """AttackModel stub for the view-model tests."""

    def __init__(self, scan: AttackScan) -> None:
        self._scan = scan
        self._last = None
        self.deploy_calls = 0

    @property
    def last_scan(self) -> AttackScan | None:
        return self._last

    def scan(self, cancel_event=None, progress=None) -> AttackScan:
        if progress is not None:
            progress(2, 4, "halfway")
        self._last = self._scan
        return self._scan

    def deploy(self, plan, redline, dry_run: bool = True) -> int:
        self.deploy_calls += 1
        return 0 if dry_run else 4


class AttackViewModelTests(unittest.TestCase):
    """Verify background scan/deploy workers and signals."""

    def setUp(self) -> None:
        frame = Frame(image=object(), width=860, height=732)
        plan = AttackPlan(
            target=Detection("town_hall", 0.9, BoundingBox(1, 2, 3, 4)),
            side="TR",
            troops={"dragon": 8},
        )
        scan = AttackScan(
            frame=frame,
            detections=tuple(plan.target and [plan.target] or []),
            redline=make_redline(),
            plan=plan,
            duration=0.1,
        )
        self.model = FakeAttackModel(scan)
        self.vm = AttackViewModel(self.model)
        self.plans: list[object] = []
        self.progress: list[tuple[int, int, str]] = []
        self.deployed: list[int] = []
        self.vm.plan_ready.connect(self.plans.append)
        self.vm.progress.connect(lambda c, t, m: self.progress.append((c, t, m)))
        self.vm.deployed.connect(self.deployed.append)

    def _wait(self, worker) -> None:
        self.assertTrue(worker.wait(5000))
        _APP.processEvents()

    def test_scan_runs_in_worker(self) -> None:
        self.vm.scan()
        worker = self.vm._worker
        self.assertIsNotNone(worker)
        self._wait(worker)
        self.assertEqual(len(self.plans), 1)
        self.assertIn((2, 4, "halfway"), self.progress)
        self.assertFalse(self.vm.is_busy)

    def test_deploy_dry_run(self) -> None:
        self.vm.scan()
        self._wait(self.vm._worker)
        self.vm.deploy_current(dry_run=True)
        worker = self.vm._worker
        self._wait(worker)
        self.assertEqual(self.deployed, [0])
        self.assertEqual(self.model.deploy_calls, 1)

    def test_deploy_without_scan_reports_error(self) -> None:
        errors: list[str] = []
        self.vm.error_occurred.connect(errors.append)
        self.vm.deploy_current()
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
