# ==== bluestacks_manager.py ====
"""BlueStacks manager: ensures BlueStacks meets required settings (resolution,
render mode, ads off, ADB on) and can launch without config-file errors.
"""

import os
import subprocess
import string
import sys
import re
import time
import contextlib
import cv2
import glob
import datetime
import shutil

import core.paths
from emulators.adb_config import ADB_BIN, WIDTH, HEIGHT, DPI
from utils.screenshot_utils import take_screenshot
from routines.boot_recovery import boot_recovery
from utils.unicode import imread_unicode

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

LAUNCH_WAIT, ADB_WAIT = (15, 90)

TEMPLATE_DIR = str(core.paths.TEMPLATE_DIR)


def run(cmd: list[str], **kw) -> str:
    import main
    host = main.host
    if host and cmd and cmd[0] == ADB_BIN:
        cmd = [ADB_BIN, '-s', host] + cmd[1:]
    try:
        return subprocess.check_output(
            cmd,
            **{
                'stderr': subprocess.DEVNULL,
                'creationflags': CREATE_NO_WINDOW,
                **kw,
            },
        ).decode().strip()
    except subprocess.CalledProcessError:
        return ''


def find_bluestacks_tools():
    for drive in string.ascii_uppercase:
        root = f'{drive}:\\'
        if not os.path.isdir(root):
            continue
        for folder in ('BlueStacks_nxt', 'BlueStacks'):
            base = os.path.join(root, 'Program Files', folder)
            player = os.path.join(base, 'HD-Player.exe')
            if not os.path.isfile(player):
                continue
            conf = os.path.join(
                os.getenv('PROGRAMDATA', 'C:\\ProgramData'),
                folder,
                'bluestacks.conf',
            )
            if not os.path.isfile(conf):
                continue
            return (player, conf)
    return (None, None)


def _read_conf(conf):
    with open(conf, 'r', encoding='utf-8', errors='ignore') as fh:
        return fh.readlines()


def _write_conf(conf_path: str, new_lines: list[str]):
    dir_ = os.path.dirname(conf_path)
    stem = os.path.basename(conf_path)
    pattern = os.path.join(dir_, f'{stem}.bak.*')

    backups = sorted(glob.glob(pattern), key=os.path.getmtime)

    if backups:
        newest = backups[-1]
        for old in backups[:-1]:
            try:
                os.remove(old)
            except OSError:
                pass
        backup_path = newest
    else:
        ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        backup_path = f'{conf_path}.bak.{ts}'

    shutil.copy2(conf_path, backup_path)
    print(f'🗄️  Backup saved → {backup_path}')

    with open(conf_path, 'w', encoding='utf-8', errors='ignore') as fh:
        fh.writelines(new_lines)


def _detect_instance_prefix(lines):
    m = re.search(r'^bst\.instance\.([^.]+)\.dpi=', '\n'.join(lines), re.M)
    if m:
        return f'bst.instance.{m.group(1)}.'
    return 'bst.instance.0.'


def _get(lines: list[str], key: str) -> str | None:
    for ln in lines:
        if not ln.startswith(key + '='):
            continue
        val = ln.split('=', 1)[1].strip()
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        return val
    return None


def _set(lines: list[str], key: str, value: str):
    pat = key + '='
    lines[:] = [ln for ln in lines if not ln.lstrip().startswith(pat)]
    lines.append(f'{key}="{value}"\n')


def is_running():
    try:
        out = subprocess.check_output(
            ['tasklist', '/FI', 'IMAGENAME eq HD-Player.exe'],
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
            shell=True,
        )
        return b'HD-Player.exe' in out
    except subprocess.SubprocessError:
        return False


def stop_player():
    subprocess.run(
        ['taskkill', '/IM', 'HD-Player.exe', '/F'],
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )
    time.sleep(3)


def start_and_connect(player):
    import main
    host = main.host

    if not is_running():
        print('🔄 BlueStacks not running—launching emulator…')
        subprocess.Popen(
            [player],
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        time.sleep(LAUNCH_WAIT)

    subprocess.run(
        [ADB_BIN, 'disconnect', host],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )

    start = time.time()
    while time.time() - start < ADB_WAIT:
        res = run([ADB_BIN, 'connect', host]).lower()
        if 'connected' in res or 'already connected' in res:
            for d in run([ADB_BIN, 'devices']).splitlines()[1:]:
                if host in d and 'device' in d:
                    print('✅ Emulator connected and online.')
                    return True
        time.sleep(3)

    print('❌ ADB failed to connect.')
    return False


def _shot():
    return take_screenshot(output_path='home_page.png')


def wait_for_settings_icon(template='store_home_page.png', thresh=0.8, timeout=25):
    import main
    host = main.host
    tpl = imread_unicode(os.path.join(TEMPLATE_DIR, template), cv2.IMREAD_GRAYSCALE)
    if tpl is None:
        return False

    start = time.time()
    while time.time() - start < timeout:
        spath = _shot()
        if not spath:
            time.sleep(1)
            continue

        img = imread_unicode(spath)
        if img is None:
            time.sleep(1)
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img

        if cv2.minMaxLoc(cv2.matchTemplate(gray, tpl, cv2.TM_CCOEFF_NORMED))[1] >= thresh:
            print('✅ Homepage detected. Enjoy clashing!')
            return True

        subprocess.run(
            [ADB_BIN, '-s', host, 'shell', 'input', 'keyevent', 'KEYCODE_HOME'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        time.sleep(1)

    return False


def _first_diff(lines, desired):
    diffs = []
    for k, v in desired.items():
        cur = _get(lines, k)
        if cur != v:
            diffs.append((k, cur, v))
    return diffs


def ensure_bluestacks():
    player, conf = find_bluestacks_tools()
    if not (player and conf):
        print('❌ BlueStacks installation not found.')
        sys.exit(1)

    running_before = is_running()
    print(f'✅ Found HD-Player.exe at: {player}')
    print(f'✅ Found bluestacks.conf at: {conf}')

    lines = _read_conf(conf)
    pref = _detect_instance_prefix(lines)
    print(f'▶ Using instance prefix: {pref}')

    core_desired = {
        pref + 'fb_width': WIDTH,
        pref + 'fb_height': HEIGHT,
        pref + 'dpi': DPI,
        pref + 'graphics_renderer': 'dx',
        pref + 'graphics_engine': 'aga',
        pref + 'adb_port': '5556',
        pref + 'status.adb_port': '5556',
        'bst.qt_renderer': 'Direct3D11',
        'bst.enable_adb_access': '1',
        'bst.enable_adb_remote_access': '1',
    }
    bonus_desired = {
        'bst.feature.programmatic_ads': '0',
        'bst.enable_programmatic_ads': '0',
    }

    bonus_changed = False
    for key, val in bonus_desired.items():
        want = f'{key}="{val}"'
        if any(ln.strip().startswith(want) for ln in lines):
            continue
        print(f'▶ Setting bonus flag {key}={val}')
        _set(lines, key, val)
        bonus_changed = True

    core_diffs = []
    for key, val in core_desired.items():
        want = f'{key}="{val}"'
        if any(ln.strip().startswith(want) for ln in lines):
            continue
        core_diffs.append((key, val))

    if core_diffs:
        print('▶ Core mismatches detected:')
        for key, val in core_diffs:
            print(f'   • {key} should be "{val}"')
            _set(lines, key, val)

    if core_diffs or bonus_changed:
        _write_conf(conf, lines)
        if core_diffs:
            print('↻ Applied core fixes → restarting BlueStacks…')
            stop_player()
        else:
            print('↻ Applied bonus flags → no restart needed.')
    else:
        print('▶ All core settings perfect – no changes.')

    if not running_before or core_diffs:
        if not start_and_connect(player):
            sys.exit(1)

    if not wait_for_settings_icon():
        print('❌ Home screen not detected – attempting boot recovery…')
        boot_recovery()


if __name__ == '__main__':
    ensure_bluestacks()
