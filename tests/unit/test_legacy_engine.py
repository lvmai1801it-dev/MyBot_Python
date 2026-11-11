"""Unit tests for the legacy farm-engine adapter."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from COCbot.app.legacy_engine import LegacyEngine
from COCbot.core.config import AppConfig, ConfigStore
from COCbot.models.bot_state import BotEvent


class FakeSink:
    """Collect emitted events."""

    def __init__(self) -> None:
        self.events: list[BotEvent] = []

    def emit(self, event: BotEvent) -> None:
        self.events.append(event)


class LegacyEngineTests(unittest.TestCase):
    """Verify config hand-off and lifecycle signals."""

    def test_run_forever_delegates_to_bot_loop(self) -> None:
        store = ConfigStore(AppConfig())
        engine = LegacyEngine(store)
        sink = FakeSink()
        received = {}

        def fake_bot_loop(cfg) -> None:
            received.update(cfg)

        with patch("COCbot.app.bootstrap.bot_loop", fake_bot_loop):
            engine.run_forever(sink)

        self.assertEqual(received["gold_threshold"], 65000)
        self.assertEqual(received["attack"], "Dragon_Attack")
        self.assertFalse(engine.is_running)
        messages = [event.message for event in sink.events]
        self.assertIn("Legacy farm engine starting", messages)
        self.assertIn("Legacy farm engine stopped", messages)

    def test_stop_pause_resume_bridge(self) -> None:
        engine = LegacyEngine(ConfigStore(AppConfig()))
        from COCbot.app import state

        state.stop_event.clear()
        state.pause_event.set()
        engine.request_pause()
        self.assertFalse(state.pause_event.is_set())
        engine.request_resume()
        self.assertTrue(state.pause_event.is_set())
        engine.request_stop()
        self.assertTrue(state.stop_event.is_set())
        state.stop_event.clear()
        state.pause_event.set()


if __name__ == "__main__":
    unittest.main()
