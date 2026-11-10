# ==== COCbot/game/account/boot_recovery.py ====
import subprocess
import time
import sys
import COCbot.app.paths  # noqa: F401
import COCbot.app.state as state
from COCbot.platform.adb_config import ADB_BIN
from COCbot.app.coords import BOOT_DISMISS_TAP

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0


def _get_host():
    if state.host:
        return state.host
    try:
        import COCbot.app.bootstrap as main
        if getattr(main, 'host', None):
            return main.host
    except Exception:
        pass
    try:
        from COCbot.app import state as main
        if getattr(main, 'host', None):
            return main.host
    except Exception:
        pass
    return None


def boot_recovery():
    host = _get_host()
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
    # BACK closes most CoC popups without risking a UI button.
    for _ in range(2):
        subprocess.run(
            [ADB_BIN, '-s', host, 'shell', 'input', 'keyevent', '4'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        time.sleep(0.4)

    from COCbot.platform.tap_guard import blocked
    if not blocked(BOOT_DISMISS_TAP[0], BOOT_DISMISS_TAP[1], "boot_dismiss"):
        subprocess.run(
            [ADB_BIN, '-s', host, 'shell', 'input', 'tap',
             str(BOOT_DISMISS_TAP[0]), str(BOOT_DISMISS_TAP[1])],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
