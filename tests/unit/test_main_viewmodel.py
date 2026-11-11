"""Unit tests for the shell main view-model."""

from __future__ import annotations

import threading
import time
import unittest

from PyQt5.QtWidgets import QApplication

from COCbot.models.bot_state import BotEvent
from COCbot.models.enums import LogLevel
from COCbot.viewmodels.main_viewmodel import MainViewModel

_APP = QApplication.instance() or QApplication([])


class FakeEngine:
    """Engine stub that runs until stop is requested."""

    def __init__(self) -> None:
        self.stop_event = threading.Event()
        self.pause_requested = False
        self.resume_requested = False

    @property
    def is_running(self) -> bool:
        return not self.stop_event.is_set()

    def run_forever(self, sink=None) -> None:
        if sink is not None:
            sink.emit(BotEvent(level=LogLevel.INFO, message="fake loop"))
        self.stop_event.wait(5)

    def run_cycle(self):
        return None

    def request_stop(self) -> None:
        self.stop_event.set()

    def request_pause(self) -> None:
        self.pause_requested = True

    def request_resume(self) -> None:
        self.resume_requested = True


class MainViewModelTests(unittest.TestCase):
    """Verify worker lifecycle and event forwarding."""

    def setUp(self) -> None:
        self.engine = FakeEngine()
        self.vm = MainViewModel(self.engine)
        self.running: list[bool] = []
        self.events: list[BotEvent] = []
        self.status: list[tuple[str, str]] = []
        self.vm.running_changed.connect(self.running.append)
        self.vm.event_emitted.connect(self.events.append)
        self.vm.status_message.connect(lambda text, kind: self.status.append((text, kind)))

    def _pump(self, count: int = 20) -> None:
        """Process queued Qt signals with a short scheduling window."""
        for _ in range(count):
            _APP.processEvents()
            time.sleep(0.005)

    def test_start_and_stop(self) -> None:
        self.assertTrue(self.vm.start())
        worker = self.vm._worker
        self.assertIsNotNone(worker)
        self.assertTrue(worker.isRunning())
        self._pump()
        self.assertEqual(self.running, [True])
        self.assertEqual([event.message for event in self.events], ["fake loop"])

        self.vm.stop()
        self.assertTrue(worker.wait(5000))
        self._pump()
        self.assertIn(False, self.running)
        self.assertFalse(self.vm.is_running)

    def test_pause_and_resume_delegate(self) -> None:
        self.vm.start()
        worker = self.vm._worker
        self.vm.pause()
        self.vm.resume()
        self.assertTrue(self.engine.pause_requested)
        self.assertTrue(self.engine.resume_requested)
        self.vm.stop()
        worker.wait(5000)
        self._pump()

    def test_double_start_is_rejected(self) -> None:
        self.vm.start()
        worker = self.vm._worker
        self.assertFalse(self.vm.start())
        self.vm.stop()
        worker.wait(5000)
        self._pump()

    def test_shutdown_stops_worker(self) -> None:
        self.vm.start()
        self.vm.shutdown(wait_ms=3000)
        self.assertFalse(self.vm.is_running)
        self.assertTrue(self.engine.stop_event.is_set())


if __name__ == "__main__":
    unittest.main()
