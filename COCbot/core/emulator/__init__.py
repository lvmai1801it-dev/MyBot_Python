"""Emulator adapters and lifecycle helpers."""

from COCbot.core.emulator.base import BaseEmulator, ToolPaths
from COCbot.core.emulator.bluestacks import BlueStacksEmulator
from COCbot.core.emulator.ldplayer import LDPlayerEmulator
from COCbot.core.emulator.memu import MemuEmulator
from COCbot.core.emulator.registry import create_emulator
from COCbot.core.emulator.setup import CLASH_PACKAGE, EmulatorSetup

__all__ = [
    "CLASH_PACKAGE",
    "BaseEmulator",
    "BlueStacksEmulator",
    "EmulatorSetup",
    "LDPlayerEmulator",
    "MemuEmulator",
    "ToolPaths",
    "create_emulator",
]
