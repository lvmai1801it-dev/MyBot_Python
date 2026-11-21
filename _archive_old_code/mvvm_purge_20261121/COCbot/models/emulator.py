"""Emulator instance model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmulatorInstance:
    """One emulator instance discovered on the host machine."""

    index: int
    name: str
    host: str = ""
    running: bool = False

    def display_name(self) -> str:
        """Return a human-readable label for pickers and logs."""
        return self.name or f"Instance {self.index}"

    def connect_host(self) -> str:
        """Return the ADB host, falling back to a local serial when unknown."""
        return self.host or f"127.0.0.1:{5555 + self.index}"
