"""Offscreen GUI smoke test for the attack feature."""

from __future__ import annotations

import unittest

from PyQt5.QtWidgets import QApplication

from COCbot.features.attack.model import AttackScan
from COCbot.features.attack.view import AttackView
from COCbot.features.attack.viewmodel import AttackViewModel
from COCbot.models.attack import AttackPlan, Detection, RedlineResult
from COCbot.models.frame import Frame
from COCbot.models.geometry import BoundingBox, Point
from COCbot.ui_components import apply_theme

_APP = QApplication.instance() or QApplication([])


def make_scan() -> AttackScan:
    """Return a deterministic scan for the view test."""
    edge = (Point(400, 600), Point(425, 600), Point(450, 600))
    redline = RedlineResult(edges=(edge, edge, edge, edge), source="cv")
    target = Detection("town_hall", 0.91, BoundingBox(400, 300, 460, 360))
    plan = AttackPlan(target=target, side="TR", troops={"dragon": 8}, spells={"rage": 5})
    return AttackScan(
        frame=Frame(image=object(), width=860, height=732),
        detections=(target,),
        redline=redline,
        plan=plan,
        duration=0.05,
    )


class FakeAttackModel:
    """Minimal model for the view."""

    def __init__(self) -> None:
        self._scan = make_scan()
        self._last = None

    @property
    def last_scan(self) -> AttackScan | None:
        return self._last

    def scan(self, cancel_event=None, progress=None) -> AttackScan:
        if progress is not None:
            progress(4, 4, "Scan complete")
        self._last = self._scan
        return self._scan

    def deploy(self, plan, redline, dry_run: bool = True) -> int:
        return 0


class AttackViewTests(unittest.TestCase):
    """Verify scan and dry-run deployment update the view."""

    def setUp(self) -> None:
        apply_theme(_APP)
        self.model = FakeAttackModel()
        self.vm = AttackViewModel(self.model)
        self.view = AttackView(self.vm)
        self.view.show()
        _APP.processEvents()

    def tearDown(self) -> None:
        self.view.close()
        self.view.deleteLater()
        _APP.processEvents()

    def _wait_worker(self) -> None:
        worker = self.vm._worker
        self.assertIsNotNone(worker)
        self.assertTrue(worker.wait(5000))
        _APP.processEvents()

    def test_scan_updates_plan(self) -> None:
        self.view.scan_btn.click()
        self._wait_worker()
        self.assertIn("town_hall", self.view.target_label.text())
        self.assertIn("TR", self.view.detail_label.text())
        self.assertTrue(self.view.deploy_btn.isEnabled())
        self.assertIn("Plan:", self.view.log_view.toPlainText())

    def test_dry_run_deploy_logs(self) -> None:
        self.view.scan_btn.click()
        self._wait_worker()
        self.view.deploy_btn.click()
        self._wait_worker()
        self.assertIn("Deployment finished: 0 taps", self.view.log_view.toPlainText())


if __name__ == "__main__":
    unittest.main()
