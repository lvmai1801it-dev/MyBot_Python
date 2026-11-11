"""Pure builders for ADB command argument lists.

Keeping the argument layout in one place makes the client easy to test with a
fake process runner and prevents shell-quoting mistakes.
"""

from __future__ import annotations

from pathlib import Path


def connect_args(adb_path: Path, host: str) -> list[str]:
    """Build ``adb connect <host>``."""
    return [str(adb_path), "connect", host]


def disconnect_args(adb_path: Path, host: str) -> list[str]:
    """Build ``adb disconnect <host>``."""
    return [str(adb_path), "disconnect", host]


def devices_args(adb_path: Path) -> list[str]:
    """Build ``adb devices``."""
    return [str(adb_path), "devices"]


def shell_args(adb_path: Path, host: str | None, command: str) -> list[str]:
    """Build ``adb [-s host] shell <command>``."""
    args = [str(adb_path)]
    if host:
        args += ["-s", host]
    return args + ["shell", command]


def tap_args(adb_path: Path, host: str | None, x: int, y: int) -> list[str]:
    """Build ``input tap`` for the selected device."""
    return shell_args(adb_path, host, f"input tap {int(x)} {int(y)}")


def swipe_args(
    adb_path: Path,
    host: str | None,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    duration_ms: int,
) -> list[str]:
    """Build ``input swipe`` for the selected device."""
    command = f"input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {int(duration_ms)}"
    return shell_args(adb_path, host, command)


def screenshot_args(adb_path: Path, host: str | None) -> list[str]:
    """Build the binary-safe ``exec-out screencap -p`` command."""
    args = [str(adb_path)]
    if host:
        args += ["-s", host]
    return args + ["exec-out", "screencap", "-p"]


def keyevent_args(adb_path: Path, host: str | None, keycode: str) -> list[str]:
    """Build ``input keyevent`` for the selected device."""
    return shell_args(adb_path, host, f"input keyevent {keycode}")


def launch_app_args(adb_path: Path, host: str | None, package: str) -> list[str]:
    """Build a launcher intent for *package*."""
    command = (
        f"monkey -p {package} -c android.intent.category.LAUNCHER 1"
    )
    return shell_args(adb_path, host, command)


def stop_app_args(adb_path: Path, host: str | None, package: str) -> list[str]:
    """Build ``am force-stop`` for *package*."""
    return shell_args(adb_path, host, f"am force-stop {package}")


def package_list_args(adb_path: Path, host: str | None, package: str) -> list[str]:
    """Build ``pm list packages`` filtered to *package*."""
    return shell_args(adb_path, host, f"pm list packages {package}")
