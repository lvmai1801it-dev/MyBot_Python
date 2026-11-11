"""Screenshot capture with retries and blank-frame detection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from COCbot.core.clock import SystemClock
from COCbot.core.config.defaults import (
    DEFAULT_CAPTURE_MIN_STDDEV,
    DEFAULT_CAPTURE_RETRIES,
    DEFAULT_CAPTURE_RETRY_DELAY,
)
from COCbot.core.ports import AdbPort, ClockPort, LoggerPort
from COCbot.core.vision.image import decode_image, is_blank
from COCbot.models.frame import Frame


@dataclass(frozen=True)
class CaptureConfig:
    """Retry and validation policy for screen capture."""

    max_retries: int = DEFAULT_CAPTURE_RETRIES
    retry_delay: float = DEFAULT_CAPTURE_RETRY_DELAY
    min_stddev: float = DEFAULT_CAPTURE_MIN_STDDEV
    save_raw_dir: Path | None = None


class ScreenCapture:
    """Capture frames from an ADB device implementing :class:`AdbPort`."""

    def __init__(
        self,
        adb: AdbPort,
        config: CaptureConfig | None = None,
        clock: ClockPort | None = None,
        logger: LoggerPort | None = None,
        on_failure: Callable[[], None] | None = None,
    ) -> None:
        """Create a capture adapter with optional recovery callback."""
        self._adb = adb
        self._config = config or CaptureConfig()
        self._clock = clock or SystemClock()
        self._logger = logger
        self._on_failure = on_failure

    def _log(self, level: str, message: str) -> None:
        """Emit a log line when a logger was supplied."""
        if self._logger is not None:
            getattr(self._logger, level)(message)

    def _save_raw(self, png: bytes) -> None:
        """Persist raw PNG bytes for debugging when configured."""
        directory = self._config.save_raw_dir
        if directory is None:
            return
        try:
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / f"screen_{int(self._clock.now())}.png"
            path.write_bytes(png)
        except OSError as exc:
            self._log("warning", f"Could not save screenshot: {exc}")

    def capture(self) -> Frame | None:
        """Capture one validated frame, or ``None`` after all retries."""
        attempts = max(1, int(self._config.max_retries))
        for attempt in range(1, attempts + 1):
            png = self._adb.screenshot()
            if not png:
                self._log("warning", f"Screenshot attempt {attempt}/{attempts} returned no data")
            else:
                image = decode_image(png)
                if image is None:
                    self._log("warning", f"Screenshot attempt {attempt}/{attempts} could not be decoded")
                elif is_blank(image, self._config.min_stddev):
                    self._log(
                        "warning",
                        f"Blank screen on attempt {attempt}/{attempts}",
                    )
                else:
                    self._save_raw(png)
                    height, width = image.shape[:2]
                    return Frame(
                        image=image,
                        width=width,
                        height=height,
                        captured_at=self._clock.now(),
                        source="adb",
                        raw=png,
                    )
            if attempt < attempts:
                self._clock.sleep(self._config.retry_delay)

        self._log("error", "Screen capture failed after all retries")
        if self._on_failure is not None:
            self._on_failure()
        return None
