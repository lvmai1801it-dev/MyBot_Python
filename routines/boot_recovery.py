# ==== boot_recovery.py ====
import subprocess
import time
import sys
import core.paths
from emulators.adb_config import ADB_BIN
from core.coords import BOOT_DISMISS_TAP

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0


def boot_recovery():
    import main
    host = main.host
    if not host:
        raise RuntimeError('No emulator selected for boot_recovery()')

    print('🔁 Restarting Clash of Clans...')

    subprocess.run(
        [ADB_BIN, '-s', host, 'shell', 'am', 'force-stop', 'com.supercell.clashofclans'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )

    subprocess.run(
        [
            ADB_BIN, '-s', host, 'shell', 'monkey',
            '-p', 'com.supercell.clashofclans',
            '-c', 'android.intent.category.LAUNCHER', '1',
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )

    print('⏳ Waiting 10 seconds for game to load...')
    time.sleep(10)

    print('👆 Dismissing pop-ups…')
    subprocess.run(
        [ADB_BIN, '-s', host, 'shell', 'input', 'tap',
         str(BOOT_DISMISS_TAP[0]), str(BOOT_DISMISS_TAP[1])],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )
