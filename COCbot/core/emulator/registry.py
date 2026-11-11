"""Emulator adapter factory."""

from __future__ import annotations

from typing import Type

from COCbot.core.adb.client import Runner
from COCbot.core.emulator.base import BaseEmulator
from COCbot.core.emulator.bluestacks import BlueStacksEmulator
from COCbot.core.emulator.ldplayer import LDPlayerEmulator
from COCbot.core.emulator.memu import MemuEmulator
from COCbot.core.ports import ClockPort, EmulatorPort, LoggerPort
from COCbot.models.enums import EmulatorType

_EMULATORS: dict[EmulatorType, Type[BaseEmulator]] = {
    EmulatorType.MEMU: MemuEmulator,
    EmulatorType.LDPLAYER: LDPlayerEmulator,
    EmulatorType.BLUESTACKS: BlueStacksEmulator,
}


def create_emulator(
    emulator_type: EmulatorType | str,
    runner: Runner | None = None,
    clock: ClockPort | None = None,
    logger: LoggerPort | None = None,
) -> EmulatorPort:
    """Create the adapter for *emulator_type*.

    Unknown or custom emulator types fall back to MEmu so a bad config value
    never prevents the GUI from opening.
    """
    normalized = EmulatorType.from_value(emulator_type)
    adapter = _EMULATORS.get(normalized, MemuEmulator)
    return adapter(runner=runner, clock=clock, logger=logger)
