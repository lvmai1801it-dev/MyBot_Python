"""Unit tests for the pause/stop session state."""

from __future__ import annotations

import threading
import time
import unittest

from COCbot.app.session import BotSession
from COCbot.models.enums import BotPhase


class BotSessionTests(unittest.TestCase):
    """Verify cooperative pause and stop semantics."""

    def test_start_resets_state(self) -> None:
        session = BotSession()
        session.record_attack()
        session.record_error("old")
        session.start()
        self.assertTrue(session.status.is_running)
        self.assertEqual(session.status.phase, BotPhase.STARTING)
        self.assertEqual(session.status.attacks_done, 0)
        self.assertEqual(session.status.last_error, "")

    def test_pause_blocks_until_resume(self) -> None:
        session = BotSession()
        session.start()
        session.request_pause()
        results: list[bool] = []
        worker = threading.Thread(target=lambda: results.append(session.wait_until_resumed()))
        worker.start()
        time.sleep(0.05)
        self.assertTrue(worker.is_alive())
        session.request_resume()
        worker.join(timeout=2.0)
        self.assertEqual(results, [True])
        self.assertFalse(session.is_paused)
        self.assertEqual(session.status.phase, BotPhase.RUNNING)

    def test_stop_wakes_paused_waiter(self) -> None:
        session = BotSession()
        session.start()
        session.request_pause()
        results: list[bool] = []
        worker = threading.Thread(target=lambda: results.append(session.wait_until_resumed()))
        worker.start()
        time.sleep(0.05)
        session.request_stop()
        worker.join(timeout=2.0)
        self.assertEqual(results, [False])
        self.assertTrue(session.stop_requested)
        self.assertEqual(session.status.phase, BotPhase.STOPPING)

    def test_snapshot_is_detached(self) -> None:
        session = BotSession()
        session.start()
        snapshot = session.snapshot()
        snapshot.attacks_done = 99
        self.assertEqual(session.status.attacks_done, 0)

    def test_finish_marks_stopped(self) -> None:
        session = BotSession()
        session.start()
        session.finish()
        self.assertFalse(session.status.is_running)
        self.assertFalse(session.status.is_paused)
        self.assertEqual(session.status.phase, BotPhase.STOPPED)


if __name__ == "__main__":
    unittest.main()
