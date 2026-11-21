"""BlueStacks emulator adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from COCbot.core.emulator.base import BaseEmulator, ToolPaths
from COCbot.models.emulator import EmulatorInstance
from COCbot.models.enums import EmulatorType


class BlueStacksEmulator(BaseEmulator):
    """Control the default BlueStacks instance (single-instance MVP)."""

    emulator_type = EmulatorType.BLUESTACKS
    default_host = "127.0.0.1:5556"
    console_name = ""
    player_name = "HD-Player.exe"
    process_name = "HD-Player.exe"

    def find_tools(self) -> ToolPaths:
        """Locate ``HD-Player.exe``."""
        for directory in self._candidate_dirs(
            "BLUESTACKS_HOME",
            (
                "BlueStacks_nxt",
                "BlueStacks",
                "Program Files/BlueStacks_nxt",
                "Program Files/BlueStacks",
            ),
        ):
            player = self._first_existing(directory / self.player_name)
            if player is not None:
                return ToolPaths(player=player)
        return ToolPaths()

    def list_instances(self) -> Sequence[EmulatorInstance]:
        """Return the default instance and its running state."""
        return [
            EmulatorInstance(
                index=0,
                name="BlueStacks",
                host=self.default_host,
                running=self.is_process_running(),
            )
        ]

    def start_instance(self, index: int) -> bool:
        """Launch BlueStacks (the first instance only)."""
        player = self.tools().player
        if player is None:
            self._log("error", "BlueStacks player not found")
            return False
        result = self._run([str(player)], timeout=30.0)
        return result.ok

    def is_instance_running(self, index: int) -> bool:
        """Return ``True`` when ``HD-Player.exe`` is running."""
        return self.is_process_running()

    def player_path(self) -> Path | None:
        """Return the player executable path, if discovered."""
        return self.tools().player
