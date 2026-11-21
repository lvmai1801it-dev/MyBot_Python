"""Port definitions (interfaces) for dependency inversion.

Only the standard library and the pure ``COCbot.models`` package may be
imported here. Adapters live in ``COCbot.core.*`` and the village/upgrade
feature. This keeps the contracts free of PyQt5 and easy to fake in tests.

The five protocols below are the ones the legacy runtime still exercises:
``AdbClient`` implements AdbPort, ``ScreenCapture`` implements CapturePort,
``NumberOcr`` implements OcrPort, ``SystemClock`` implements ClockPort, and
the village/upgrade services consume LoggerPort.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from COCbot.models.frame import Frame
from COCbot.models.geometry import Rect


@runtime_checkable
class LoggerPort(Protocol):
    """Minimal logging surface consumed by services and view-models."""

    def debug(self, message: str, *args: object, **kwargs: object) -> None:
        """Log a debug message."""

    def info(self, message: str, *args: object, **kwargs: object) -> None:
        """Log an informational message."""

    def warning(self, message: str, *args: object, **kwargs: object) -> None:
        """Log a warning."""

    def error(self, message: str, *args: object, **kwargs: object) -> None:
        """Log an error."""

    def exception(self, message: str, *args: object, **kwargs: object) -> None:
        """Log an error with the active exception traceback."""


@runtime_checkable
class AdbPort(Protocol):
    """ADB transport used to control an emulator."""

    def connect(self, host: str, timeout: float = 10.0) -> bool:
        """Connect to an ADB serial such as ``127.0.0.1:5555``."""

    def disconnect(self) -> None:
        """Close the current ADB connection."""

    def is_connected(self) -> bool:
        """Return ``True`` when a device is available."""

    def shell(self, command: str, timeout: float = 10.0) -> str:
        """Run a shell command and return decoded stdout."""

    def tap(self, x: int, y: int) -> bool:
        """Tap once at screen coordinates ``(x, y)``."""

    def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration_ms: int = 300,
    ) -> bool:
        """Swipe between two screen coordinates."""

    def screenshot(self) -> bytes | None:
        """Capture the device screen as PNG/JPEG bytes."""


@runtime_checkable
class CapturePort(Protocol):
    """Screen-capture adapter."""

    def capture(self) -> Frame | None:
        """Return the latest screen frame, or ``None`` on failure."""


@runtime_checkable
class OcrPort(Protocol):
    """Number/text OCR adapter."""

    def read_number(self, frame: Frame, region: Rect | None = None) -> int | None:
        """Read an integer from *region* of *frame*."""


@runtime_checkable
class ClockPort(Protocol):
    """Injectable clock so long-running loops can be tested instantly."""

    def now(self) -> float:
        """Return the current Unix timestamp."""

    def monotonic(self) -> float:
        """Return a monotonic counter in seconds."""

    def sleep(self, seconds: float) -> None:
        """Sleep for *seconds* without importing ``time`` at call sites."""
