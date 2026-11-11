"""Unit tests for the ADB client using an injected process runner."""

from __future__ import annotations

import unittest
from typing import Sequence

from COCbot.core.adb.client import AdbClient, CommandResult
from COCbot.core.errors import AdbError

PNG = b"\x89PNG\r\n\x1a\n" + b"payload"


class FakeRunner:
    """Record calls and return scripted results."""

    def __init__(self, handler) -> None:
        self.handler = handler
        self.calls: list[tuple[list[str], float]] = []

    def __call__(self, args: Sequence[str], timeout: float) -> CommandResult:
        self.calls.append((list(args), timeout))
        return self.handler(list(args))


class AdbClientTests(unittest.TestCase):
    """Verify command construction and response parsing."""

    def _client(self, handler) -> tuple[AdbClient, FakeRunner]:
        runner = FakeRunner(handler)
        return AdbClient(host="127.0.0.1:5555", adb_path="adb.exe", runner=runner, retries=0), runner

    def test_tap_builds_input_tap(self) -> None:
        client, runner = self._client(lambda args: CommandResult(0))
        self.assertTrue(client.tap(10, 20))
        self.assertEqual(
            runner.calls[0][0],
            ["adb.exe", "-s", "127.0.0.1:5555", "shell", "input tap 10 20"],
        )

    def test_swipe_uses_duration(self) -> None:
        client, runner = self._client(lambda args: CommandResult(0))
        self.assertTrue(client.swipe(1, 2, 3, 4, duration_ms=250))
        self.assertIn("input swipe 1 2 3 4 250", runner.calls[0][0][-1])

    def test_shell_decodes_stdout(self) -> None:
        client, _ = self._client(lambda args: CommandResult(0, b"hello\n"))
        self.assertEqual(client.shell("echo hello"), "hello\n")

    def test_shell_raises_on_failure(self) -> None:
        client, _ = self._client(lambda args: CommandResult(1, b"", b"boom"))
        with self.assertRaises(AdbError):
            client.shell("bad")

    def test_screenshot_strips_leading_noise(self) -> None:
        client, _ = self._client(lambda args: CommandResult(0, b"warning" + PNG))
        self.assertEqual(client.screenshot(), PNG)

    def test_screenshot_rejects_missing_png(self) -> None:
        client, _ = self._client(lambda args: CommandResult(0, b"not an image"))
        self.assertIsNone(client.screenshot())

    def test_is_connected_matches_selected_serial(self) -> None:
        def handler(args: list[str]) -> CommandResult:
            if "devices" in args:
                return CommandResult(
                    0,
                    b"List of devices attached\n127.0.0.1:5555\tdevice\n",
                )
            return CommandResult(0)

        client, _ = self._client(handler)
        self.assertTrue(client.is_connected())

    def test_retries_until_success(self) -> None:
        results = [CommandResult(1, b"", b"fail"), CommandResult(0, b"ok")]

        def handler(args: list[str]) -> CommandResult:
            return results.pop(0)

        runner = FakeRunner(handler)
        client = AdbClient(host="h", adb_path="adb.exe", runner=runner, retries=1, retry_delay=0)
        self.assertEqual(client.shell("ping"), "ok")
        self.assertEqual(len(runner.calls), 2)

    def test_package_installed(self) -> None:
        client, _ = self._client(
            lambda args: CommandResult(0, b"package:com.supercell.clashofclans\n")
        )
        self.assertTrue(client.package_installed("com.supercell.clashofclans"))


if __name__ == "__main__":
    unittest.main()
