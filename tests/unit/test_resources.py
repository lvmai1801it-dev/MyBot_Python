"""Unit tests for the home-village resource readout."""

from __future__ import annotations

import unittest

import numpy as np

from COCbot.features.village.resources import (
    MAX_BUILDERS,
    MAX_RESOURCE,
    ResourceReader,
    VillageResources,
)
from COCbot.models.frame import Frame


class FakeCapture:
    """Return one fixed frame."""

    def __init__(self, frame: Frame | None) -> None:
        self._frame = frame

    def capture(self) -> Frame | None:
        return self._frame


def blank_frame() -> Frame:
    """Return a black 860x732 frame."""
    return Frame(image=np.zeros((732, 860, 3), dtype=np.uint8), width=860, height=732)


class ScriptedNumbers:
    """Return numbers in order, repeating the last value."""

    def __init__(self, values: list[int | None]) -> None:
        self.values = values
        self.index = 0
        self.calls = 0

    def __call__(self, image: np.ndarray) -> int | None:
        self.calls += 1
        value = self.values[min(self.index, len(self.values) - 1)]
        self.index += 1
        return value


class ResourceReaderTests(unittest.TestCase):
    """Verify counter parsing, bounds, and failure handling."""

    def test_reads_all_counters(self) -> None:
        numbers = ScriptedNumbers([1_000, 2_000, 3_000, 40])
        reader = ResourceReader(
            FakeCapture(blank_frame()),
            number_reader=numbers,
            fraction_reader=lambda _image: (5, 6),
        )
        snapshot = reader.read()
        self.assertEqual(snapshot.gold, 1_000)
        self.assertEqual(snapshot.elixir, 2_000)
        self.assertEqual(snapshot.dark_elixir, 3_000)
        self.assertEqual(snapshot.gems, 40)
        self.assertEqual(snapshot.builders_available, 5)
        self.assertEqual(snapshot.builders_total, 6)
        self.assertTrue(snapshot.has_values())

    def test_out_of_range_numbers_are_dropped(self) -> None:
        numbers = ScriptedNumbers([MAX_RESOURCE + 1, -5, 10, 10])
        reader = ResourceReader(
            FakeCapture(blank_frame()),
            number_reader=numbers,
            fraction_reader=lambda _image: None,
        )
        snapshot = reader.read()
        self.assertIsNone(snapshot.gold)
        self.assertIsNone(snapshot.elixir)
        self.assertEqual(snapshot.dark_elixir, 10)
        self.assertIsNone(snapshot.builders_available)

    def test_invalid_builder_fraction_is_dropped(self) -> None:
        reader = ResourceReader(
            FakeCapture(blank_frame()),
            number_reader=lambda _image: 1,
            fraction_reader=lambda _image: (MAX_BUILDERS + 1, MAX_BUILDERS + 1),
        )
        snapshot = reader.read()
        self.assertIsNone(snapshot.builders_available)

    def test_capture_failure_returns_empty_snapshot(self) -> None:
        reader = ResourceReader(FakeCapture(None))
        self.assertEqual(reader.read(), VillageResources())
        self.assertFalse(reader.read().has_values())

    def test_glm_reads_every_counter_in_two_requests(self) -> None:
        prompts: list[str] = []

        def client(image, prompt):
            prompts.append(prompt)
            if "top to bottom" in prompt:
                return "\n16 000 000\n13 086 862\n250 000\n1 497"
            return "\n5/6"

        reader = ResourceReader(
            FakeCapture(blank_frame()),
            glm_client=client,
        )
        snapshot = reader.read()
        self.assertEqual(snapshot.gold, 16_000_000)
        self.assertEqual(snapshot.elixir, 13_086_862)
        self.assertEqual(snapshot.dark_elixir, 250_000)
        self.assertEqual(snapshot.gems, 1_497)
        self.assertEqual(snapshot.builders_available, 5)
        self.assertEqual(snapshot.builders_total, 6)
        self.assertEqual(len(prompts), 2)

    def test_glm_garbage_falls_back_to_tesseract(self) -> None:
        numbers = ScriptedNumbers([1_000, 2_000, 3_000, 40])
        reader = ResourceReader(
            FakeCapture(blank_frame()),
            number_reader=numbers,
            fraction_reader=lambda _image: (2, 6),
            glm_client=lambda image, prompt: "no numbers here",
        )
        snapshot = reader.read()
        self.assertEqual(snapshot.gold, 1_000)
        self.assertEqual(snapshot.builders_available, 2)

    def test_capacity_tooltip_is_parsed_and_closed(self) -> None:
        class FakeAdb:
            def __init__(self) -> None:
                self.taps = []

            def tap(self, x, y):
                self.taps.append((x, y))
                return True

        adb = FakeAdb()
        reader = ResourceReader(
            FakeCapture(blank_frame()),
            glm_client=lambda image, prompt: (
                "Max: 7,950,000\nProduction per hour: 31,400\nIn treasury: 0.49M"
            ),
            adb=adb,
        )
        capacity = reader.read_capacity("gold")
        self.assertIsNotNone(capacity)
        self.assertEqual(capacity.maximum, 7_950_000)
        self.assertEqual(capacity.production, 31_400)
        self.assertEqual(capacity.treasury, 490_000)
        self.assertEqual(adb.taps, [(760, 30), (760, 30)])

    def test_capacity_needs_adb_and_glm(self) -> None:
        reader = ResourceReader(FakeCapture(blank_frame()))
        self.assertIsNone(reader.read_capacity("gold"))


if __name__ == "__main__":
    unittest.main()
