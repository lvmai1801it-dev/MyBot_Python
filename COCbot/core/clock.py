"""Concrete clock adapter used by capture and bot loops."""

from __future__ import annotations

import time


class SystemClock:
    """Default :class:`COCbot.core.ports.ClockPort` implementation."""

    def now(self) -> float:
        """Return the current Unix timestamp."""
        return time.time()

    def monotonic(self) -> float:
        """Return a monotonic counter in seconds."""
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        """Sleep for *seconds* (no-op for non-positive values)."""
        if seconds > 0:
            time.sleep(seconds)
