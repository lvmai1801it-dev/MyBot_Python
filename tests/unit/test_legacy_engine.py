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

    def test_resource_hook_is_installed_for_the_run(self) -> None:
        from COCbot.app import state

        store = ConfigStore(AppConfig())
        published = []
        engine = LegacyEngine(store, on_resources=published.append)

        seen_hooks = {}

        def fake_bot_loop(cfg) -> None:
            seen_hooks["hook"] = state.resource_hook
            state.resource_hook({"gold": 12, "elixir": 34, "dark_elixir": 56})

        with patch("COCbot.app.bootstrap.bot_loop", fake_bot_loop):
            engine.run_forever(FakeSink())

        self.assertIsNotNone(seen_hooks["hook"])
        self.assertIsNone(state.resource_hook)
        self.assertEqual(len(published), 1)
        snapshot = published[0]
        self.assertEqual(snapshot.gold, 12)
        self.assertEqual(snapshot.elixir, 34)
        self.assertEqual(snapshot.dark_elixir, 56)

    def test_legacy_currency_readout_wins_over_generic_ocr(self) -> None:
        from COCbot.features.village.resources import VillageResources

        class FakeReader:
            def read(self) -> VillageResources:
                return VillageResources(
                    gold=101_287,
                    dark_elixir=50_168,
                    gems=991,
                    builders_available=3,
                    builders_total=6,
                )

        published = []
        engine = LegacyEngine(
            ConfigStore(AppConfig()),
            resource_reader=FakeReader(),  # type: ignore[arg-type]
            on_resources=published.append,
        )
        engine._publish_resources(
            {"gold": 10_128_117, "elixir": 7_822_777, "dark_elixir": 90_168}
        )
        snapshot = published[0]
        self.assertEqual(snapshot.gold, 10_128_117)
        self.assertEqual(snapshot.elixir, 7_822_777)
        self.assertEqual(snapshot.dark_elixir, 90_168)
        self.assertEqual(snapshot.gems, 991)
        self.assertEqual(snapshot.builders_available, 3)
        self.assertEqual(snapshot.builders_total, 6)

    def test_generic_read_fills_in_missing_currency(self) -> None:
        from COCbot.features.village.resources import VillageResources

        class FakeReader:
            def read(self) -> VillageResources:
                return VillageResources(gold=500, elixir=600, dark_elixir=700)

        published = []
        engine = LegacyEngine(
            ConfigStore(AppConfig()),
            resource_reader=FakeReader(),  # type: ignore[arg-type]
            on_resources=published.append,
        )
        engine._publish_resources({"gold": 0, "elixir": 0, "dark_elixir": 0})
        snapshot = published[0]
        self.assertEqual(snapshot.gold, 500)
        self.assertEqual(snapshot.elixir, 600)
        self.assertEqual(snapshot.dark_elixir, 700)

    def test_resource_publish_skips_empty_snapshots(self) -> None:
        published = []
        engine = LegacyEngine(ConfigStore(AppConfig()), on_resources=published.append)
        engine._publish_resources({})
        self.assertEqual(published, [])


if __name__ == "__main__":
    unittest.main()
