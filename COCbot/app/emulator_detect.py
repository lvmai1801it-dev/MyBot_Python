"""MEmu auto-detection shared by the Qt GUI and the web UI.

Probe order:
1. ADB online: try ``adb connect <host>`` and confirm the device is listed
   (the same check ``start_and_connect`` performs).
2. Installed: ``find_memu_tools`` (running-process path first, then the
   standard install directories).

Only MEmu is auto-detected for now; other emulators stay on the manual
picker until they are supported.
"""

from __future__ import annotations

import os
import subprocess
import sys

MEMU_HOST = "127.0.0.1:21503"

_CREATION = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _adb_online(host: str) -> bool:
    """Return True when ADB can connect and list *host* as a device."""
    from COCbot.platform.adb_config import ADB_BIN

    try:
        out = subprocess.check_output(
            [ADB_BIN, "connect", host],
            stderr=subprocess.DEVNULL, creationflags=_CREATION, timeout=10,
        ).decode(errors="replace")
        if "connected" not in out.lower():
            return False
        devices = subprocess.check_output(
            [ADB_BIN, "devices"],
            stderr=subprocess.DEVNULL, creationflags=_CREATION, timeout=10,
        ).decode(errors="replace")
        return any(host in line and "device" in line
                   for line in devices.splitlines())
    except Exception as exc:
        print(f"[AUTO] ADB probe failed: {exc}")
        return False


def detect_memu(host: str = MEMU_HOST) -> tuple[bool, str]:
    """Return (detected, reason) for MEmu at *host*.

    reason is one of "online", "installed", "missing" - callers log it and
    decide what to do (use now / launch during bot_loop / fall back to the
    manual picker).
    """
    if _adb_online(host):
        print(f"[AUTO] MEmu dang chay (ADB {host} online) - dung ngay.")
        return True, "online"

    from COCbot.emulator.memu import find_memu_tools

    exe, memuc, _ = find_memu_tools()
    if exe and os.path.isfile(exe):
        print("[AUTO] Phat hien MEmu tren may (chua chay) - bot se tu mo no.")
        return True, "installed"

    print("[AUTO] Khong thay MEmu online hay cai san - chon thu cong.")
    return False, "missing"
