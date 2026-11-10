"""Captured frame value object shared by capture and vision ports."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Frame:
    """A single screen capture.

    ``image`` is intentionally typed as ``Any`` so this module stays free of
    numpy/OpenCV imports. Concrete adapters store a ``numpy.ndarray`` here.
    """

    image: Any
    width: int
    height: int
    captured_at: float = field(default_factory=time.time)
    source: str = "adb"

    def is_empty(self) -> bool:
        """Return ``True`` when the frame carries no usable image."""
        return self.image is None or self.width <= 0 or self.height <= 0

    def age(self, now: float | None = None) -> float:
        """Return the number of seconds since the frame was captured."""
        reference = time.time() if now is None else now
        return max(0.0, reference - self.captured_at)
