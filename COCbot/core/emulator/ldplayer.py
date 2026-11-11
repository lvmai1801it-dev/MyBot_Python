"""LDPlayer emulator adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from COCbot.core.emulator.base import BaseEmulator, ToolPaths
from COCbot.models.emulator import EmulatorInstance
from COCbot.models.enums import EmulatorType


class LDPlayerEmulator(BaseEmulator):
    """Control LDPlayer instances through ``ldconsole.exe``."""

    emulator_type = EmulatorType.LDPLAYER
    default_host = "127.0.0.1:5555"
    console_name = "ldconsole.exe"
    player_name = "dnplayer.exe"
    process_name = "dnplayer.exe"

    def find_tools(self) -> ToolPaths:
        """Locate ``ldconsole.exe`` and ``dnplayer.exe``."""
        directories = [
            *self._candidate_dirs(
                "LDPLAYER_HOME",
                (
                    "LDPlayer/LDPlayer9",
                    "LDPlayer/LDPlayer4.0",
                    "LDPlayer9",
                    "LDPlayer",
                ),
            )
        ]
        for directory in directories:
            console = self._first_existing(directory / self.console_name)
            player = self._first_existing(directory / self.player_name)
            if console is not None:
                return ToolPaths(console=console, player=player)
        return ToolPaths()

    def instance_host(self, index: int) -> str:
        """Return the LDPlayer ADB port for *index* (5555 + index*2)."""
        return f"127.0.0.1:{5555 + index * 2}"

    def list_instances(self) -> Sequence[EmulatorInstance]:
        """List instances reported by ``ldconsole list2``."""
        console = self.tools().console
        if console is None:
            return []
        result = self._run([str(console), "list2"])
        if not result.ok:
            return []
        return self._parse_instances(
            result.text(),
            self._is_running_row,
        )

    @staticmethod
    def _is_running_row(line: str, parts: list[str]) -> bool:
        """Interpret ``list2`` columns: index,name,handle,android_started,..."""
        if len(parts) >= 4 and parts[3] in ("0", "1"):
            return parts[3] == "1"
        return "running" in line.lower()

    def start_instance(self, index: int) -> bool:
        """Launch the LDPlayer instance at *index*."""
        console = self.tools().console
        if console is None:
            self._log("error", "LDPlayer console not found")
            return False
        result = self._run(
            [str(console), "launch", "--index", str(index)],
            timeout=30.0,
        )
        if not result.ok:
            self._log("error", f"Could not launch LDPlayer instance {index}")
        return result.ok

    def is_instance_running(self, index: int) -> bool:
        """Return ``True`` when ``ldconsole isrunning`` says so."""
        console = self.tools().console
        if console is None:
            return self.is_process_running()
        result = self._run(
            [str(console), "isrunning", "--index", str(index)]
        )
        text = result.text().strip().lower()
        return result.ok and text in ("1", "true", "running")

    def stop_instance(self, index: int) -> bool:
        """Quit the LDPlayer instance at *index*."""
        console = self.tools().console
        if console is None:
            return False
        return self._run(
            [str(console), "quit", "--index", str(index)]
        ).ok

    def player_path(self) -> Path | None:
        """Return the player executable path, if discovered."""
        return self.tools().player
