"""Unit tests for QThread workers (offscreen, no GUI required)."""

from __future__ import annotations

import unittest

from PyQt5.QtCore import QCoreApplication

from COCbot.models.bot_state import BotEvent
from COCbot.models.enums import LogLevel
from COCbot.workers import BotWorker, TaskWorker


_APP = QCoreApplication.instance() or QCoreApplication([])


def app() -> QCoreApplication:
    """Return the process-wide QCoreApplication, creating it if needed."""
    return _APP


class TaskWorkerTests(unittest.TestCase):
    """Verify success, failure, and cancellation signals."""

    def test_success(self) -> None:
        application = app()
        worker = TaskWorker(lambda: 42)
        results: list[object] = []
        worker.work_finished.connect(results.append)
        worker.start()
        self.assertTrue(worker.wait(5000))
        application.processEvents()
        self.assertEqual(results, [42])

    def test_failure(self) -> None:
        application = app()

        def boom() -> None:
            raise ValueError("bad input")

        worker = TaskWorker(boom)
        errors: list[tuple[str, str]] = []
        worker.failed.connect(lambda kind, message: errors.append((kind, message)))
        worker.start()
        self.assertTrue(worker.wait(5000))
        application.processEvents()
        self.assertEqual(errors, [("ValueError", "bad input")])
        self.assertIn("ValueError", worker.error_traceback)

    def test_cancel(self) -> None:
        application = app()

        def target(cancel_event) -> str:
            return "finished"

        worker = TaskWorker(target, pass_cancel_event=True)
        canceled: list[bool] = []
        worker.canceled.connect(lambda: canceled.append(True))
        worker.cancel()
        worker.start()
        self.assertTrue(worker.wait(5000))
        application.processEvents()
        self.assertEqual(canceled, [True])


class FakeEngine:
    """BotEnginePort stub that emits one event and returns."""

    def __init__(self) -> None:
        self.sink = None
        self.stop_requested = False

    @property
    def is_running(self) -> bool:
        return False

    def run_forever(self, sink=None) -> None:
        self.sink = sink
        if sink is not None:
            sink.emit(BotEvent(level=LogLevel.INFO, message="hello from engine"))

    def run_cycle(self):
        return None

    def request_stop(self) -> None:
        self.stop_requested = True

    def request_pause(self) -> None:
        pass

    def request_resume(self) -> None:
        pass


class BotWorkerTests(unittest.TestCase):
    """Verify BotWorker forwards events and lifecycle signals."""

    def test_event_forwarding(self) -> None:
        application = app()
        engine = FakeEngine()
        worker = BotWorker(engine)
        events: list[BotEvent] = []
        started: list[bool] = []
        finished: list[bool] = []
        worker.event_emitted.connect(events.append)
        worker.work_started.connect(lambda: started.append(True))
        worker.work_finished.connect(lambda: finished.append(True))
        worker.start()
        self.assertTrue(worker.wait(5000))
        application.processEvents()
        self.assertEqual([event.message for event in events], ["hello from engine"])
        self.assertEqual(started, [True])
        self.assertEqual(finished, [True])

    def test_stop_delegates(self) -> None:
        engine = FakeEngine()
        worker = BotWorker(engine)
        worker.stop()
        self.assertTrue(engine.stop_requested)


if __name__ == "__main__":
    unittest.main()
