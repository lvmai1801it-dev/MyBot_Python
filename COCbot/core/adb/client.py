"""Subprocess ADB client implementing :class:`COCbot.core.ports.AdbPort`.

The client is Qt-free and thread-safe. A fake runner can be injected in tests,
so no emulator is required for the unit suite.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from COCbot.core.adb import commands
from COCbot.core.config.defaults import (
    ADB_RETRY_COUNT,
    ADB_RETRY_DELAY_SEC,
    DEFAULT_ADB_TIMEOUT,
)
from COCbot.core.config.paths import get_project_paths
from COCbot.core.errors import AdbError
from COCbot.core.ports import ClockPort, LoggerPort

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True)
class CommandResult:
    """Minimal process result used by the injectable runner."""

    returncode: int
    stdout: bytes = b""
    stderr: bytes = b""

    @property
    def ok(self) -> bool:
        """Return ``True`` when the process exited with code 0."""
        return self.returncode == 0

    def text(self) -> str:
        """Decode stdout as UTF-8 with replacement for malformed bytes."""
        return self.stdout.decode("utf-8", errors="replace")


Runner = Callable[[Sequence[str], float], CommandResult]


def _creation_flags() -> int:
    """Return Windows no-window flags, or 0 on other platforms."""
    if sys.platform == "win32":
        return subprocess.CREATE_NO_WINDOW
    return 0


def default_runner(args: Sequence[str], timeout: float) -> CommandResult:
    """Run *args* with subprocess and capture stdout/stderr."""
    completed = subprocess.run(
        list(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        creationflags=_creation_flags(),
        check=False,
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


class AdbClient:
    """ADB transport for one emulator host."""

    def __init__(
        self,
        host: str | None = None,
        adb_path: Path | str | None = None,
        timeout: float = DEFAULT_ADB_TIMEOUT,
        retries: int = ADB_RETRY_COUNT,
        retry_delay: float = ADB_RETRY_DELAY_SEC,
        runner: Runner | None = None,
        clock: ClockPort | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        """Create a client; call :meth:`connect` before sending input."""
        self.host = host
        self.adb_path = Path(adb_path) if adb_path else get_project_paths().adb_bin
        self.timeout = timeout
        self.retries = max(0, int(retries))
        self.retry_delay = max(0.0, float(retry_delay))
        self._runner = runner or default_runner
        self._clock = clock
        self._logger = logger
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ helpers
    def _sleep(self, seconds: float) -> None:
        """Sleep through the injected clock when available."""
        if self._clock is not None:
            self._clock.sleep(seconds)
        elif seconds > 0:
            time.sleep(seconds)

    def _log(self, level: str, message: str) -> None:
        """Emit a log line when a logger was supplied."""
        if self._logger is None:
            return
        getattr(self._logger, level)(message)

    def _run(
        self,
        args: Sequence[str],
        timeout: float | None = None,
        retries: int | None = None,
    ) -> CommandResult:
        """Execute *args* with retries and return the last result."""
        attempts = self.retries if retries is None else max(0, int(retries))
        last = CommandResult(1, b"", b"no attempt made")
        for attempt in range(attempts + 1):
            try:
                with self._lock:
                    last = self._runner(args, timeout or self.timeout)
            except (OSError, subprocess.SubprocessError) as exc:
                last = CommandResult(1, b"", str(exc).encode("utf-8", errors="replace"))
            if last.ok:
                return last
            if attempt < attempts:
                self._log(
                    "warning",
                    f"ADB retry {attempt + 1}/{attempts} failed: {last.stderr.decode(errors='replace').strip()}",
                )
                self._sleep(self.retry_delay)
        return last

    # ------------------------------------------------------------------ contract
    def connect(self, host: str, timeout: float = 10.0) -> bool:
        """Connect to *host* and keep it as the active serial.

        Local serials such as ``emulator-5554`` are already registered by the
        ADB server, so only network hosts need an explicit ``adb connect``.
        """
        self.host = host
        if ":" not in host:
            return self.is_connected()
        result = self._run(commands.connect_args(self.adb_path, host), timeout=timeout)
        text = result.text().lower()
        connected = "connected" in text or "already connected" in text
        if not connected and not result.ok:
            self._log("error", f"ADB connect failed for {host}")
            return False
        return self.is_connected()

    def disconnect(self) -> None:
        """Disconnect the active serial, if any."""
        if self.host:
            self._run(commands.disconnect_args(self.adb_path, self.host), retries=0)
        self.host = None

    def is_connected(self) -> bool:
        """Return ``True`` when the selected serial is listed as ``device``."""
        result = self._run(commands.devices_args(self.adb_path), retries=0)
        if not result.ok:
            return False
        for line in result.text().splitlines()[1:]:
            parts = line.split()
            if len(parts) < 2:
                continue
            serial, state = parts[0], parts[1]
            if self.host and serial == self.host and state == "device":
                return True
            if not self.host and state == "device":
                return True
        return False

    def shell(self, command: str, timeout: float = DEFAULT_ADB_TIMEOUT) -> str:
        """Run a shell command and return decoded stdout."""
        result = self._run(
            commands.shell_args(self.adb_path, self.host, command),
            timeout=timeout,
        )
        if not result.ok:
            raise AdbError(
                f"adb shell failed ({result.returncode}): "
                f"{result.stderr.decode(errors='replace').strip()}"
            )
        return result.text()

    def tap(self, x: int, y: int) -> bool:
        """Tap once at ``(x, y)``."""
        result = self._run(commands.tap_args(self.adb_path, self.host, x, y))
        return result.ok

    def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration_ms: int = 300,
    ) -> bool:
        """Swipe between two screen coordinates."""
        result = self._run(
            commands.swipe_args(
                self.adb_path, self.host, x1, y1, x2, y2, duration_ms
            )
        )
        return result.ok

    def screenshot(self) -> bytes | None:
        """Capture the screen and return raw PNG bytes."""
        result = self._run(commands.screenshot_args(self.adb_path, self.host))
        if not result.ok:
            self._log("warning", "ADB screencap returned a non-zero exit code")
            return None
        index = result.stdout.find(PNG_MAGIC)
        if index < 0:
            self._log("warning", "ADB screencap returned no PNG signature")
            return None
        return result.stdout[index:]

    def screenshot_raw(self) -> bytes | None:
        """Capture the screen in Android's raw framebuffer format.

        The payload starts with ``width, height, format`` (three little-endian
        u32 values) followed by the pixels. It is 2-3x faster than PNG because
        no encode/decode step is involved.
        """
        result = self._run(commands.screencap_raw_args(self.adb_path, self.host))
        if not result.ok or len(result.stdout) < 12:
            self._log("debug", "ADB raw screencap returned no data")
            return None
        return result.stdout

    # --------------------------------------------------------------- convenience
    def keyevent(self, keycode: str) -> bool:
        """Send an Android key event such as ``KEYCODE_HOME``."""
        return self._run(
            commands.keyevent_args(self.adb_path, self.host, keycode)
        ).ok

    def launch_app(self, package: str) -> bool:
        """Start an installed Android package."""
        return self._run(
            commands.launch_app_args(self.adb_path, self.host, package)
        ).ok

    def stop_app(self, package: str) -> bool:
        """Force-stop an Android package."""
        return self._run(
            commands.stop_app_args(self.adb_path, self.host, package)
        ).ok

    def package_installed(self, package: str) -> bool:
        """Return ``True`` when *package* appears in ``pm list packages``."""
        result = self._run(
            commands.package_list_args(self.adb_path, self.host, package),
            retries=0,
        )
        return result.ok and package in result.text()
