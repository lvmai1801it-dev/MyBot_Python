# ==== adb_utils.py ====
import subprocess
import time

from config import ADB_BIN, CREATE_NO_WINDOW
from core.coords import RETURN_HOME_TAP
import state


def run_adb(cmd_args):
    subprocess.run(
        [ADB_BIN, '-s', state.host] + cmd_args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )


def tap(x: int, y: int, device: str = None) -> bool:
    device = device or state.host
    if device is None:
        raise RuntimeError(
            'ADB target device is not set!  Make sure choose_emulator() has run.'
        )

    subprocess.run(
        [ADB_BIN, '-s', device, 'connect'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )

    proc = subprocess.run(
        [ADB_BIN, '-s', device, 'shell', 'input', 'tap',
         str(x), str(y)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )
    return proc.returncode == 0


def return_home():
    run_adb(['shell', 'input', 'tap',
             str(RETURN_HOME_TAP[0]), str(RETURN_HOME_TAP[1])])
    time.sleep(3)