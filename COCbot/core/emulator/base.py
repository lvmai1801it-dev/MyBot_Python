"""Shared emulator adapter helpers."""

from __future__ import annotations

import os
import string
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from COCbot.core.adb.client import CommandResult, Runner, default_runner
from COCbot.core.clock import SystemClock
from COCbot.core.ports import ClockPort, LoggerPort
from COCbot.models.emulator import EmulatorInstance
from COCbot.models.enums import EmulatorType


@dataclass(frozen=True)
class ToolPaths:
    """Console and player executables for an emulator family."""

    console: Path | None = None
    player: Path | None = None


class BaseEmulator:
    """Base class for console-driven emulator adapters."""

    emulator_type: EmulatorType = EmulatorType.CUSTOM
    default_host: str = "127.0.0.1:5555"
    console_name: str = ""
    player_name: str = ""
    process_name: str = ""

    def __init__(
        self,
        runner: Runner | None = None,
        clock: ClockPort | None = None,
        logger: LoggerPort | None = None,
        timeout: float = 10.0,
        tools: ToolPaths | None = None,
    ) -> None:
        """Create an adapter with injectable process runner and clock."""
        self._runner = runner or default_runner
        self._clock = clock or SystemClock()
        self._logger = logger
        self._timeout = timeout
        self._tools = tools

    def _log(self, level: str, message: str) -> None:
        """Emit a log line when a logger was supplied."""
        if self._logger is not None:
            getattr(self._logger, level)(message)

    def _run(self, args: Sequence[str], timeout: float | None = None) -> CommandResult:
        """Run a console command and return its result."""
        try:
            return self._runner(list(args), timeout or self._timeout)
        except (OSError, subprocess.SubprocessError) as exc:
            return CommandResult(1, b"", str(exc).encode("utf-8", errors="replace"))

    def find_tools(self) -> ToolPaths:
        """Locate the emulator executables; override per family."""
        return ToolPaths()

    def tools(self) -> ToolPaths:
        """Return cached tool paths."""
        if self._tools is None:
            self._tools = self.find_tools()
        return self._tools

    @staticmethod
    def _candidate_dirs(env_name: str, names: Sequence[str]) -> list[Path]:
        """Build a short list of install directories to probe."""
        candidates: list[Path] = []
        env = os.environ.get(env_name)
        if env:
            candidates.append(Path(env))
        for base in (
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramFiles(x86)"),
            os.environ.get("LOCALAPPDATA"),
        ):
            if base:
                for name in names:
                    candidates.append(Path(base) / name)
        for name in names:
            candidates.append(Path("C:/") / name)
            candidates.append(Path("D:/") / name)
        # Installs are often on a secondary drive (MEmu/LDPlayer/BlueStacks).
        for letter in string.ascii_uppercase:
            drive = Path(f"{letter}:/")
            try:
                if not drive.exists():
                    continue
            except OSError:
                continue
            for name in names:
                candidates.append(drive / name)
        return candidates

    @staticmethod
    def _first_existing(*paths: Path) -> Path | None:
        """Return the first path that exists, if any."""
        for path in paths:
            if path.is_file():
                return path
        return None

    def is_process_running(self, process_name: str | None = None) -> bool:
        """Return ``True`` when the player process is visible to tasklist."""
        name = process_name or self.process_name
        if not name or sys.platform != "win32":
            return False
        result = self._run(["tasklist", "/FI", f"IMAGENAME eq {name}"])
        return result.ok and name.lower().encode() in result.stdout.lower()

    def _parse_instances(
        self,
        output: str,
        running_predicate: Callable[[str, list[str]], bool],
    ) -> list[EmulatorInstance]:
        """Parse console output into instances using a family-specific rule."""
        instances: list[EmulatorInstance] = []
        for line in output.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            parts = (
                [part.strip() for part in stripped.split(",")]
                if "," in stripped
                else stripped.split()
            )
            if len(parts) < 2 or not parts[0].isdigit():
                continue
            index = int(parts[0])
            instances.append(
                EmulatorInstance(
                    index=index,
                    name=parts[1],
                    host=self.instance_host(index),
                    running=running_predicate(line, parts),
                )
            )
        return instances

    def instance_host(self, index: int) -> str:
        """Return the ADB host for *index*; override when ports differ."""
        return self.default_host

    def list_instances(self) -> Sequence[EmulatorInstance]:
        """Return discovered instances; override per family."""
        return []

    def start_instance(self, index: int) -> bool:
        """Start an instance; override per family."""
        return False

    def is_instance_running(self, index: int) -> bool:
        """Return whether an instance is running; default checks the process."""
        return self.is_process_running()
