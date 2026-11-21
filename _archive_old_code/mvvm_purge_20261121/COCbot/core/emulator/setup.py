"""Emulator lifecycle orchestration (start + ADB connect + launch game)."""

from __future__ import annotations

from COCbot.core.clock import SystemClock
from COCbot.core.ports import AdbPort, ClockPort, EmulatorPort, LoggerPort

CLASH_PACKAGE = "com.supercell.clashofclans"


class EmulatorSetup:
    """Bring an emulator online and launch Clash of Clans."""

    def __init__(
        self,
        emulator: EmulatorPort,
        adb: AdbPort,
        logger: LoggerPort | None = None,
        package: str = CLASH_PACKAGE,
        clock: ClockPort | None = None,
    ) -> None:
        """Store the adapters used by the setup workflow."""
        self._emulator = emulator
        self._adb = adb
        self._logger = logger
        self._package = package
        self._clock = clock or SystemClock()

    def _log(self, level: str, message: str) -> None:
        """Emit a log line when a logger was supplied."""
        if self._logger is not None:
            getattr(self._logger, level)(message)

    def ensure_running(
        self,
        index: int = 0,
        host: str | None = None,
        wait_seconds: float = 45.0,
        poll_interval: float = 3.0,
    ) -> bool:
        """Start *index* when needed, then poll until ADB is online."""
        if not self._emulator.is_instance_running(index):
            self._log("info", f"Starting emulator instance {index}")
            if not self._emulator.start_instance(index):
                self._log("error", f"Could not start emulator instance {index}")
                return False

        target = host or self._emulator.default_host
        self._log("info", f"Connecting ADB to {target}")
        deadline = self._clock.monotonic() + max(0.0, wait_seconds)
        while True:
            if self._adb.connect(target):
                return True
            if self._clock.monotonic() >= deadline:
                self._log("error", f"ADB did not connect to {target} in time")
                return False
            self._clock.sleep(poll_interval)

    def launch_game(self) -> bool:
        """Restart Clash of Clans if it is installed."""
        if not self._adb.is_connected():
            self._log("error", "Cannot launch the game without an ADB device")
            return False
        if not self._adb.package_installed(self._package):
            self._log("error", f"{self._package} is not installed")
            return False
        self._adb.stop_app(self._package)
        self._log("info", "Launching Clash of Clans")
        return self._adb.launch_app(self._package)

    def ensure_ready(
        self,
        index: int = 0,
        host: str | None = None,
        wait_seconds: float = 45.0,
    ) -> bool:
        """Connect the emulator and launch the game end to end."""
        return self.ensure_running(index, host, wait_seconds) and self.launch_game()
