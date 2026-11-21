"""Statistics feature domain model (pure Python, no Qt)."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from COCbot.core.config.defaults import MAX_VILLAGES
from COCbot.core.config.paths import get_project_paths
from COCbot.core.errors import StorageError


def _as_int(value: Any, default: int = 0) -> int:
    """Convert *value* to a non-negative int."""
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class StatsTotals:
    """Loot, attacks, and star distribution."""

    gold: int = 0
    elixir: int = 0
    dark_elixir: int = 0
    attacks: int = 0
    stars: tuple[int, int, int, int] = (0, 0, 0, 0)
    last_update: float = 0.0

    @property
    def total_stars(self) -> int:
        """Return the sum of all star buckets."""
        return sum(self.stars)

    def add(self, other: "StatsTotals") -> "StatsTotals":
        """Return the element-wise sum of two totals."""
        return StatsTotals(
            gold=self.gold + other.gold,
            elixir=self.elixir + other.elixir,
            dark_elixir=self.dark_elixir + other.dark_elixir,
            attacks=self.attacks + other.attacks,
            stars=tuple(
                left + right for left, right in zip(self.stars, other.stars)
            ),
            last_update=max(self.last_update, other.last_update),
        )

    def star_count(self, stars: int) -> int:
        """Return the bucket count for *stars* (clamped to 0..3)."""
        return self.stars[max(0, min(3, int(stars)))]


@dataclass(frozen=True)
class VillageStats:
    """Totals for one village slot."""

    index: int
    totals: StatsTotals = StatsTotals()
    exists: bool = False


@dataclass(frozen=True)
class StatisticsSnapshot:
    """Aggregated statistics for the whole profile."""

    overall: StatsTotals = StatsTotals()
    villages: tuple[VillageStats, ...] = ()

    @property
    def updated_at(self) -> float:
        """Return the newest update timestamp."""
        return self.overall.last_update


class StatisticsModel:
    """Read and reset ``profiles/Stats_N.json`` files."""

    def __init__(
        self,
        profiles_dir: Path | str | None = None,
        max_villages: int = MAX_VILLAGES,
    ) -> None:
        """Resolve the profiles directory and village count."""
        self._dir = (
            Path(profiles_dir)
            if profiles_dir is not None
            else get_project_paths().profiles_dir
        )
        self._max_villages = max(1, int(max_villages))

    @property
    def directory(self) -> Path:
        """Return the directory holding stats files."""
        return self._dir

    def file_path(self, index: int) -> Path:
        """Return the stats file for village *index*."""
        return self._dir / f"Stats_{int(index)}.json"

    def _read(self, index: int) -> VillageStats:
        """Read one village file, returning defaults when missing/broken."""
        path = self.file_path(index)
        if not path.is_file():
            return VillageStats(index=index, exists=False)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return VillageStats(index=index, exists=False)
        stars_raw = raw.get("stars", {}) if isinstance(raw, dict) else {}
        stars = tuple(_as_int(stars_raw.get(str(star), 0)) for star in range(4))
        totals = StatsTotals(
            gold=_as_int(raw.get("gold", 0)),
            elixir=_as_int(raw.get("elixir", 0)),
            dark_elixir=_as_int(raw.get("de", 0)),
            attacks=_as_int(raw.get("attacks", 0)),
            stars=stars,
            last_update=float(raw.get("last_update_ts", 0) or 0),
        )
        return VillageStats(index=index, totals=totals, exists=True)

    def load(self) -> StatisticsSnapshot:
        """Read every village file and aggregate the totals."""
        villages = tuple(self._read(index) for index in range(1, self._max_villages + 1))
        overall = StatsTotals()
        for village in villages:
            overall = overall.add(village.totals)
        return StatisticsSnapshot(overall=overall, villages=villages)

    def zero_all(self) -> StatisticsSnapshot:
        """Reset every village stats file to zero."""
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StorageError(f"Could not create stats directory: {exc}") from exc
        payload = {
            "gold": 0,
            "elixir": 0,
            "de": 0,
            "attacks": 0,
            "stars": {"0": 0, "1": 0, "2": 0, "3": 0},
            "last_update_ts": 0,
        }
        for index in range(1, self._max_villages + 1):
            path = self.file_path(index)
            temp = path.with_suffix(path.suffix + ".tmp")
            try:
                temp.write_text(
                    json.dumps(payload, indent=2),
                    encoding="utf-8",
                )
                temp.replace(path)
            except OSError as exc:
                raise StorageError(f"Could not reset {path}: {exc}") from exc
        return self.load()

    @staticmethod
    def now() -> float:
        """Return the current Unix timestamp (injectable seam for tests)."""
        return time.time()
