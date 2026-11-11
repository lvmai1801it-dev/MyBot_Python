"""Port definitions (interfaces) for dependency inversion.

Only the standard library and the pure ``COCbot.models`` package may be
imported here. Adapters live in ``COCbot.core.*``, ``COCbot.workers``, and the
feature packages. This keeps the contracts free of PyQt5 and easy to fake in
tests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, Sequence, runtime_checkable

from COCbot.models.attack import Detection
from COCbot.models.bot_state import BotEvent, CycleResult
from COCbot.models.emulator import EmulatorInstance
from COCbot.models.enums import EmulatorType
from COCbot.models.frame import Frame
from COCbot.models.geometry import Rect

if TYPE_CHECKING:
    from COCbot.core.config.schema import AppConfig


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
class EmulatorPort(Protocol):
    """Discovery and lifecycle operations for one emulator family."""

    @property
    def emulator_type(self) -> EmulatorType:
        """Return the emulator family handled by this adapter."""

    @property
    def default_host(self) -> str:
        """Return the default ADB host for this emulator."""

    def list_instances(self) -> Sequence[EmulatorInstance]:
        """Return every discovered instance for this emulator."""

    def start_instance(self, index: int) -> bool:
        """Start the instance identified by *index*."""

    def is_instance_running(self, index: int) -> bool:
        """Return ``True`` when the instance is running."""


@runtime_checkable
class CapturePort(Protocol):
    """Screen-capture adapter."""

    def capture(self) -> Frame | None:
        """Return the latest screen frame, or ``None`` on failure."""


@runtime_checkable
class DetectorPort(Protocol):
    """Object detector adapter (YOLO or OpenCV fallback)."""

    def detect(self, frame: Frame, confidence: float | None = None) -> Sequence[Detection]:
        """Return detections for *frame*."""


@runtime_checkable
class OcrPort(Protocol):
    """Number/text OCR adapter."""

    def read_number(self, frame: Frame, region: Rect | None = None) -> int | None:
        """Read an integer from *region* of *frame*."""


@runtime_checkable
class SettingsPort(Protocol):
    """Persistent application settings store."""

    def load(self) -> "AppConfig":
        """Load settings from disk, returning defaults on first run."""

    def save(self, config: "AppConfig") -> None:
        """Persist the complete settings object."""

    def reload(self) -> "AppConfig":
        """Discard the in-memory copy and load from disk again."""


@runtime_checkable
class ClockPort(Protocol):
    """Injectable clock so long-running loops can be tested instantly."""

    def now(self) -> float:
        """Return the current Unix timestamp."""

    def monotonic(self) -> float:
        """Return a monotonic counter in seconds."""

    def sleep(self, seconds: float) -> None:
        """Sleep for *seconds* without importing ``time`` at call sites."""


@runtime_checkable
class EventSinkPort(Protocol):
    """Consumer for structured bot events."""

    def emit(self, event: BotEvent) -> None:
        """Publish one event to the sink."""


class BotEnginePort(Protocol):
    """Long-running bot engine started by a background worker."""

    @property
    def is_running(self) -> bool:
        """Return ``True`` while the engine loop is active."""

    def run_forever(self, sink: EventSinkPort | None = None) -> None:
        """Run until stopped, forwarding events to *sink*."""

    def run_cycle(self) -> CycleResult:
        """Execute one complete bot cycle and return its result."""

    def request_stop(self) -> None:
        """Ask the engine to stop after the current step."""

    def request_pause(self) -> None:
        """Ask the engine to pause at the next safe point."""

    def request_resume(self) -> None:
        """Resume a paused engine."""
