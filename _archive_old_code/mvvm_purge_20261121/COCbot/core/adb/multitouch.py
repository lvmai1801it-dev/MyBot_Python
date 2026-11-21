"""UIAutomator2 multi-touch adapter for map zoom."""

from __future__ import annotations

import time
from typing import Any

from COCbot.core.ports import LoggerPort


class Uiautomator2MultiTouch:
    """Pinch gestures through uiautomator2 with safe retries."""

    def __init__(
        self,
        host: str,
        retries: int = 5,
        logger: LoggerPort | None = None,
    ) -> None:
        """Store the ADB host; the device connects lazily."""
        self._host = host
        self._retries = max(1, int(retries))
        self._logger = logger
        self._device: Any = None
        self._connected = False

    def _log(self, level: str, message: str) -> None:
        """Emit a log line when a logger was supplied."""
        if self._logger is not None:
            getattr(self._logger, level)(message)

    def _connect(self) -> Any:
        """Connect to uiautomator2 once."""
        if self._connected:
            return self._device
        self._connected = True
        try:
            import uiautomator2 as u2

            self._device = u2.connect(self._host)
        except Exception as exc:
            self._log("warning", f"uiautomator2 unavailable: {exc}")
            self._device = None
        return self._device

    def pinch_in(self, percent: int = 100, steps: int = 20) -> bool:
        """Perform a pinch-in gesture, retrying on transient errors."""
        device = self._connect()
        if device is None:
            return False
        delay = 0.35
        for attempt in range(1, self._retries + 1):
            try:
                device().pinch_in(percent=percent, steps=steps)
                return True
            except Exception as exc:
                if attempt == self._retries:
                    self._log("warning", f"pinch_in failed after {attempt} attempts: {exc}")
                    return False
                try:
                    device.shell("input tap 5 5")
                except Exception:
                    pass
                time.sleep(delay)
                delay = min(delay * 1.5, 2.0)
        return False
