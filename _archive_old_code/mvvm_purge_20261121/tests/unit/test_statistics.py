"""Unit tests for the statistics feature model and view-model."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from COCbot.features.statistics.model import StatisticsModel
from COCbot.features.statistics.viewmodel import StatisticsViewModel

_APP = QApplication.instance() or QApplication([])


def write_stats(path: Path, gold: int, attacks: int, stars: list[int]) -> None:
    """Write one stats file in the legacy shape."""
    path.write_text(
        json.dumps(
            {
                "gold": gold,
                "elixir": gold * 2,
                "de": 100,
                "attacks": attacks,
                "stars": {str(index): value for index, value in enumerate(stars)},
                "last_update_ts": 1_700_000_000,
            }
        ),
        encoding="utf-8",
    )


class StatisticsModelTests(unittest.TestCase):
    """Verify reading, aggregation, and reset."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.dir = Path(self._temp.name)
        self.model = StatisticsModel(self.dir, max_villages=5)

    def tearDown(self) -> None:
        self._temp.cleanup()

    def test_missing_files_use_defaults(self) -> None:
        snapshot = self.model.load()
        self.assertEqual(len(snapshot.villages), 5)
        self.assertEqual(snapshot.overall.gold, 0)
        self.assertFalse(snapshot.villages[0].exists)

    def test_load_and_aggregate(self) -> None:
        write_stats(self.dir / "Stats_1.json", 1000, 3, [0, 0, 1, 2])
        write_stats(self.dir / "Stats_2.json", 2000, 2, [0, 1, 0, 1])
        snapshot = self.model.load()
        self.assertEqual(snapshot.overall.gold, 3000)
        self.assertEqual(snapshot.overall.elixir, 6000)
        self.assertEqual(snapshot.overall.attacks, 5)
        self.assertEqual(snapshot.overall.stars, (0, 1, 1, 3))
        self.assertEqual(snapshot.overall.total_stars, 5)
        self.assertTrue(snapshot.villages[0].exists)

    def test_zero_all(self) -> None:
        write_stats(self.dir / "Stats_1.json", 1000, 3, [0, 0, 1, 2])
        snapshot = self.model.zero_all()
        self.assertEqual(snapshot.overall.gold, 0)
        for index in range(1, 6):
            path = self.dir / f"Stats_{index}.json"
            self.assertTrue(path.is_file())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["gold"], 0)


class StatisticsViewModelTests(unittest.TestCase):
    """Verify snapshot signals and reset."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.dir = Path(self._temp.name)
        write_stats(self.dir / "Stats_1.json", 500, 1, [0, 0, 0, 1])
        self.model = StatisticsModel(self.dir, max_villages=5)
        self.vm = StatisticsViewModel(self.model)
        self.snapshots: list[object] = []
        self.status: list[tuple[str, str]] = []
        self.vm.snapshot_loaded.connect(self.snapshots.append)
        self.vm.status_message.connect(lambda text, kind: self.status.append((text, kind)))

    def tearDown(self) -> None:
        self._temp.cleanup()

    def test_refresh(self) -> None:
        self.vm.refresh()
        self.assertEqual(len(self.snapshots), 1)
        self.assertEqual(self.vm.snapshot.overall.gold, 500)

    def test_reset(self) -> None:
        self.vm.refresh()
        self.vm.reset()
        self.assertEqual(self.vm.snapshot.overall.gold, 0)
        self.assertIn("Statistics reset", [item[0] for item in self.status])


if __name__ == "__main__":
    unittest.main()
