"""MEmu emulator adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from COCbot.core.emulator.base import BaseEmulator, ToolPaths
from COCbot.models.emulator import EmulatorInstance
from COCbot.models.enums import EmulatorType


class MemuEmulator(BaseEmulator):
    """Control MEmu instances through ``memuc.exe``."""

    emulator_type = EmulatorType.MEMU
    default_host = "127.0.0.1:21503"
    console_name = "memuc.exe"
    player_name = "MEmu.exe"
    process_name = "MEmu.exe"

    def find_tools(self) -> ToolPaths:
        """Locate ``memuc.exe`` and ``MEmu.exe``."""
        for directory in self._candidate_dirs(
            "MEMU_HOME",
            (
                "Microvirt/MEmu",
                "Program Files/Microvirt/MEmu",
                "Program Files (x86)/Microvirt/MEmu",
            ),
        ):
            console = self._first_existing(directory / self.console_name)
            player = self._first_existing(directory / self.player_name)
            if console is not None:
                return ToolPaths(console=console, player=player)
        return ToolPaths()

    def instance_host(self, index: int) -> str:
        """Return the MEmu ADB port for *index* (21503 + index*10)."""
        return f"127.0.0.1:{21503 + index * 10}"

    def list_instances(self) -> Sequence[EmulatorInstance]:
        """List VMs reported by ``memuc listvms``."""
        console = self.tools().console
        if console is None:
            return []
        result = self._run([str(console), "listvms"])
        if not result.ok:
            return []
        instances: list[EmulatorInstance] = []
        for line in result.text().splitlines():
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
            if len(parts) >= 4:
                running = parts[3].strip().lower() in ("1", "true", "running")
            elif len(parts) >= 3:
                running = "running" in stripped.lower()
            else:
                running = self.is_instance_running(index)
            instances.append(
                EmulatorInstance(
                    index=index,
                    name=parts[1],
                    host=self.instance_host(index),
                    running=running,
                )
            )
        return instances

    def start_instance(self, index: int) -> bool:
        """Start VM *index*, trying both ``start`` and ``startvm``."""
        console = self.tools().console
        if console is None:
            self._log("error", "MEmu console not found")
            return False
        for verb in ("start", "startvm"):
            result = self._run([str(console), verb, "-i", str(index)])
            if result.ok:
                return True
        self._log("error", f"Could not start MEmu instance {index}")
        return False

    def is_instance_running(self, index: int) -> bool:
        """Return ``True`` when ``memuc isvmrunning`` reports running."""
        console = self.tools().console
        if console is None:
            return self.is_process_running()
        result = self._run([str(console), "isvmrunning", "-i", str(index)])
        return result.ok and "running" in result.text().lower()

    def player_path(self) -> Path | None:
        """Return the player executable path, if discovered."""
        return self.tools().player
