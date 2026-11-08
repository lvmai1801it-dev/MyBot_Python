# ==== COCbot/emulator/emulator_setup.py ====
import subprocess
import sys
import time

import COCbot.core.paths  # noqa: F401
import COCbot.core.state as state
from COCbot.core.config import ADB_BIN, MEMU, BLUESTACKS, CREATE_NO_WINDOW
from COCbot.emulator.memu_manager import ensure_memu
from COCbot.emulator.ldplayer_manager import ensure_ldplayer
from COCbot.emulator.bluestacks_manager import ensure_bluestacks


def setup_emulator():
    key = state.emulator_key
    if not key:
        h = state.host
        if h == MEMU:
            key = 'memu'
        elif h == BLUESTACKS:
            key = 'bluestacks'
    if not key:
        try:
            import COCbot.core.main as main
            key = getattr(main, 'emulator_key', None)
        except Exception:
            pass
    if not key:
        raise RuntimeError('No emulator selected for setup_emulator()')

    if key == 'memu':
        ensure_memu()
    elif key == 'bluestacks':
        ensure_bluestacks()
    elif key == 'ldplayer':
        ensure_ldplayer(index=state.ld_index)
    else:
        raise RuntimeError(f'Unsupported emulator: {key}')

    print('▶ Checking if Clash of Clans is installed…')
    target_host = state.host
    if not target_host:
        try:
            import COCbot.core.main as main
            target_host = getattr(main, 'host', None)
        except Exception:
            pass

    try:
        pkg_list = subprocess.check_output(
            [ADB_BIN, '-s', target_host, 'shell', 'pm', 'list', 'packages',
             'com.supercell.clashofclans'],
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        ).decode().strip()
    except subprocess.CalledProcessError:
        pkg_list = ''

    if 'com.supercell.clashofclans' not in pkg_list:
        print('❌ Clash of Clans is not installed. Please install it and retry.')
        sys.exit(1)

    pkg = 'com.supercell.clashofclans'
    print('▶ Launching Clash of Clans…')
    try:
        pid = subprocess.check_output(
            [ADB_BIN, '-s', target_host, 'shell', 'pidof', pkg],
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        ).decode().strip()
    except subprocess.CalledProcessError:
        pid = ''

    if pid:
        print(f'🔄 Clash of Clans is running (pid={pid})—restarting...')
        subprocess.run(
            [ADB_BIN, '-s', target_host, 'shell', 'am', 'force-stop', pkg],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        time.sleep(1)

    subprocess.run(
        [ADB_BIN, '-s', target_host, 'shell', 'monkey',
         '-p', pkg,
         '-c', 'android.intent.category.LAUNCHER', '1'],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )
    print('✅ Clash of Clans should now be in the foreground.')
