"""Unit tests for emulator adapters using fake console output."""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Sequence

from COCbot.core.adb.client import CommandResult
from COCbot.core.emulator import (
    BlueStacksEmulator,
    EmulatorSetup,
    LDPlayerEmulator,
    MemuEmulator,
    ToolPaths,
    create_emulator,
)
from COCbot.models.enums import EmulatorType


class FakeRunner:
    """Return scripted results keyed by command fragments."""

    def __init__(self, responses: dict[str, CommandResult]) -> None:
        self.responses = responses
        self.calls: list[list[str]] = []

    def __call__(self, args: Sequence[str], timeout: float) -> CommandResult:
        self.calls.append(list(args))
        joined = " ".join(args)
        for fragment, result in self.responses.items():
            if fragment in joined:
                return result
        return CommandResult(0)


class MemuTests(unittest.TestCase):
    """Verify MEmu parsing and lifecycle commands."""

    def setUp(self) -> None:
        self.runner = FakeRunner(
            {
                "listvms": CommandResult(0, b"0,My VM,Running\n1,Second,Stopped\n"),
                "isvmrunning": CommandResult(0, b"running\n"),
                "start": CommandResult(0),
            }
        )
        self.emulator = MemuEmulator(
            runner=self.runner,
            tools=ToolPaths(console=Path("memuc.exe")),
        )

    def test_list_instances(self) -> None:
        instances = self.emulator.list_instances()
        self.assertEqual(len(instances), 2)
        self.assertEqual(instances[0].index, 0)
        self.assertEqual(instances[0].name, "My VM")
        self.assertTrue(instances[0].running)
        self.assertFalse(instances[1].running)
        self.assertEqual(instances[0].host, "127.0.0.1:21503")
        self.assertEqual(instances[1].host, "127.0.0.1:21513")

    def test_start_and_running(self) -> None:
        self.assertTrue(self.emulator.start_instance(0))
        self.assertTrue(self.emulator.is_instance_running(0))
        self.assertEqual(self.emulator.emulator_type, EmulatorType.MEMU)


class LDPlayerTests(unittest.TestCase):
    """Verify ``list2`` column parsing."""

    def test_list2(self) -> None:
        runner = FakeRunner(
            {
                "list2": CommandResult(
                    0,
                    b"0,LDPlayer,123,1,456,789\n1,LDPlayer2,0,0,0,0\n",
                )
            }
        )
        emulator = LDPlayerEmulator(
            runner=runner,
            tools=ToolPaths(console=Path("ldconsole.exe")),
        )
        instances = emulator.list_instances()
        self.assertEqual(len(instances), 2)
        self.assertTrue(instances[0].running)
        self.assertFalse(instances[1].running)
        self.assertEqual(instances[1].host, "127.0.0.1:5557")


class BlueStacksTests(unittest.TestCase):
    """Verify the single-instance adapter."""

    def test_single_instance_running(self) -> None:
        runner = FakeRunner({"tasklist": CommandResult(0, b"HD-Player.exe")})
        emulator = BlueStacksEmulator(
            runner=runner,
            tools=ToolPaths(player=Path("HD-Player.exe")),
        )
        instances = emulator.list_instances()
        self.assertEqual(len(instances), 1)
        self.assertTrue(instances[0].running)
        self.assertEqual(instances[0].host, "127.0.0.1:5556")


class FactoryTests(unittest.TestCase):
    """Verify the registry maps every supported type."""

    def test_create(self) -> None:
        self.assertIsInstance(create_emulator("memu"), MemuEmulator)
        self.assertIsInstance(create_emulator("ldplayer"), LDPlayerEmulator)
        self.assertIsInstance(create_emulator("bluestacks"), BlueStacksEmulator)
        self.assertIsInstance(create_emulator("unknown"), MemuEmulator)


class FakeEmulator:
    """Minimal EmulatorPort stub."""

    default_host = "127.0.0.1:5555"

    def __init__(self) -> None:
        self.started = False

    def is_instance_running(self, index: int) -> bool:
        return self.started

    def start_instance(self, index: int) -> bool:
        self.started = True
        return True


class FakeAdb:
    """Minimal AdbPort stub for setup tests."""

    def __init__(self) -> None:
        self.connected = False
        self.launched = False
        self.stopped = False

    def connect(self, host: str, timeout: float = 10.0) -> bool:
        self.connected = True
        return True

    def is_connected(self) -> bool:
        return self.connected

    def package_installed(self, package: str) -> bool:
        return True

    def stop_app(self, package: str) -> bool:
        self.stopped = True
        return True

    def launch_app(self, package: str) -> bool:
        self.launched = True
        return True


class SetupTests(unittest.TestCase):
    """Verify the setup orchestrator starts, connects, and launches."""

    def test_ensure_ready(self) -> None:
        emulator = FakeEmulator()
        adb = FakeAdb()
        setup = EmulatorSetup(emulator, adb)
        self.assertTrue(setup.ensure_ready())
        self.assertTrue(emulator.started)
        self.assertTrue(adb.connected)
        self.assertTrue(adb.stopped)
        self.assertTrue(adb.launched)


if __name__ == "__main__":
    unittest.main()
