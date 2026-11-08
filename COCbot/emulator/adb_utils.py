# ==== COCbot/emulator/adb_utils.py ====
import subprocess
import time

import COCbot.core.paths  # noqa: F401
from COCbot.core.config import ADB_BIN, CREATE_NO_WINDOW
from COCbot.core.coords import RETURN_HOME_TAP
import COCbot.core.state as state


def _get_target_device(device: str = None) -> str:
    if device:
        return device
    if state.host:
        return state.host
    try:
        import COCbot.core.main as main
        if getattr(main, 'host', None):
            return main.host
    except Exception:
        pass
    try:
        import main
        if getattr(main, 'host', None):
            return main.host
    except Exception:
        pass
    return None


def run_adb(cmd_args, device: str = None):
    dev = _get_target_device(device)
    base_cmd = [ADB_BIN]
    if dev:
        base_cmd += ['-s', dev]
    proc = subprocess.run(
        base_cmd + cmd_args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )
    return proc.returncode == 0


def tap(x: int, y: int, device: str = None) -> bool:
    dev = _get_target_device(device)
    if dev is None:
        raise RuntimeError(
            'ADB target device is not set! Make sure choose_emulator() has run.'
        )

    subprocess.run(
        [ADB_BIN, '-s', dev, 'connect'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )

    proc = subprocess.run(
        [ADB_BIN, '-s', dev, 'shell', 'input', 'tap',
         str(x), str(y)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )
    return proc.returncode == 0


def return_home(device: str = None):
    dev = _get_target_device(device)
    base_cmd = [ADB_BIN]
    if dev:
        base_cmd += ['-s', dev]
    subprocess.run(
        base_cmd + ['shell', 'input', 'tap',
         str(RETURN_HOME_TAP[0]), str(RETURN_HOME_TAP[1])],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )
    time.sleep(3)
