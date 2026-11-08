# ==== memu_manager.py ====
import os
import string
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import core.paths
import cv2
from utils.screenshot_utils import take_screenshot
from utils.unicode import imread_unicode

from COCbot.emulator.adb_config import ADB_BIN, DPI, HEIGHT, WIDTH
from COCbot.routines.boot_recovery import boot_recovery

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

ADB_ADDRESS = '127.0.0.1:21503'
LAUNCH_WAIT = 12
ADB_WAIT = 90

MEMU = '127.0.0.1:21503'

TEMPLATE_DIR = str(core.paths.TEMPLATE_DIR)


def run(cmd, **kw):
    import main
    host = getattr(main, 'host', None)
    if host and cmd and cmd[0] == ADB_BIN:
        cmd = [ADB_BIN, '-s', host] + cmd[1:]
    try:
        return subprocess.check_output(
            cmd,
            **{'stderr': subprocess.DEVNULL, 'creationflags': CREATE_NO_WINDOW, **kw},
        ).decode().strip()
    except Exception:
        return ''


def find_memu_tools():
    # 1. Check running processes
    try:
        out = subprocess.check_output(
            ['wmic', 'process', 'where', "name='MEmu.exe'", 'get', 'ExecutablePath'],
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        ).decode()
        for line in out.splitlines():
            line = line.strip()
            if line.lower().endswith('memu.exe') and os.path.isfile(line):
                base = os.path.dirname(line)
                memuc = os.path.join(base, 'memuc.exe')
                if os.path.isfile(memuc):
                    return (line, memuc, None)
    except Exception:
        pass

    # 2. Check standard drives and directories
    for drive in string.ascii_uppercase:
        root = f'{drive}:\\'
        if not os.path.isdir(root):
            continue
        for sub in (
            os.path.join('Program Files', 'Microvirt', 'MEmu'),
            os.path.join('Program Files (x86)', 'Microvirt', 'MEmu'),
            os.path.join('Microvirt', 'MEmu'),
        ):
            base = os.path.join(root, sub)
            exe = os.path.join(base, 'MEmu.exe')
            memuc = os.path.join(base, 'memuc.exe')
            if os.path.isfile(exe) and os.path.isfile(memuc):
                return (exe, memuc, None)
    return (None, None, None)


def get_instance_index(memuc_path):
    out = run([memuc_path, 'listvms'])
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(',') if ',' in line else line.split()
        if parts and parts[0].strip().isdigit():
            return parts[0].strip()
    return '0'


def apply_resolution(memuc_path, index):
    print(f'▶ Applying resolution {WIDTH}×{HEIGHT}@{DPI}dpi to VM #{index}…')
    subprocess.run(
        [memuc_path, 'setconfigex', '-i', index, 'custom_resolution', WIDTH, HEIGHT, DPI],
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )


def _find_instance_cfg(memu_exe: str) -> str:
    install_dir = os.path.dirname(memu_exe)
    vms_dir = os.path.join(install_dir, 'MemuHyperv VMs')
    if not os.path.isdir(vms_dir):
        raise FileNotFoundError(f'No VM folder at {vms_dir}')
    for name in os.listdir(vms_dir):
        inst = os.path.join(vms_dir, name)
        cfg = os.path.join(inst, f'{name}.memu')
        if os.path.isfile(cfg):
            return cfg
    raise FileNotFoundError(f'Could not find any .memu under {vms_dir}')


def _current_render_mode_cfg(memu_exe: str) -> str | None:
    cfg = _find_instance_cfg(memu_exe)
    tree = ET.parse(cfg)
    for gp in tree.findall('.//GuestProperty'):
        if gp.get('name') == 'renderEngine':
            return gp.get('value')
    for gp in tree.findall('.//GuestProperty'):
        if gp.get('name') == 'RenderPath':
            return {'0': 'OpenGL', '1': 'DirectX', '2': 'Auto'}.get(gp.get('value'))
    return None


def _set_render_mode_cfg(memu_exe: str, target='DirectX') -> None:
    cfg = _find_instance_cfg(memu_exe)
    tree = ET.parse(cfg)
    root = tree.getroot()
    changed = False
    for gp in tree.findall('.//GuestProperty'):
        if gp.get('name') == 'renderEngine':
            gp.set('value', target)
            changed = True
    if not changed:
        new_gp = ET.Element('GuestProperty', {'name': 'renderEngine', 'value': target})
        root.append(new_gp)
    tree.write(cfg, encoding='utf-8', xml_declaration=True)


def stop_memu():
    print('Closing MEmu if open…')
    subprocess.run(
        ['taskkill', '/IM', 'MEmu.exe', '/F'],
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )
    time.sleep(2)


def is_memu_running() -> bool:
    try:
        out = subprocess.check_output(
            ['tasklist', '/FI', 'IMAGENAME eq MEmu.exe'],
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
            shell=True,
        )
        return b'MEmu.exe' in out
    except subprocess.SubprocessError:
        return False


def start_and_connect(emulator_exe):
    import main
    host = getattr(main, 'host', None)
    if not host:
        raise RuntimeError('No emulator selected before start_and_connect()')

    if host == MEMU:
        if not is_memu_running():
            print('🔄 MEmu not running—launching emulator.')
            subprocess.Popen(
                [emulator_exe],
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW,
            )
            print(f'⏳ Waiting {LAUNCH_WAIT}s for emulator startup…')
            time.sleep(LAUNCH_WAIT)
        else:
            print('✅ MEmu already running—skipping launch.')

        subprocess.run(
            [ADB_BIN, 'disconnect', host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
    else:
        print(f'▶ Using BlueStacks at {host}; skipping emulator launch & ADB reset.')

    start = time.time()
    while time.time() - start < ADB_WAIT:
        out = run([ADB_BIN, 'connect', host])
        if 'connected' in out.lower() or 'already connected' in out.lower():
            devices = run([ADB_BIN, 'devices']).splitlines()[1:]
            for d in devices:
                if host in d and 'device' in d:
                    print('✅ Emulator connected and online.')
                    return True
        time.sleep(3)

    print('❌ ADB failed to connect after restart.')
    return False


def capture_for_matching():
    return take_screenshot(output_path='home_page.png')


def wait_for_settings_icon(template='settings_logo.png', thresh=0.8, timeout=25) -> bool:
    import main
    host = getattr(main, 'host', None)
    tpl_path = os.path.join(TEMPLATE_DIR, template)
    tpl = imread_unicode(tpl_path, cv2.IMREAD_GRAYSCALE)
    if tpl is None:
        print(f'❌ Template {tpl_path} not found')
        return False

    start = time.time()
    while time.time() - start < timeout:
        screenshot_path = capture_for_matching()
        if not screenshot_path:
            time.sleep(1)
            continue

        img = imread_unicode(screenshot_path, cv2.IMREAD_COLOR)
        if img is None:
            print(f"[WARN] Could not load '{screenshot_path}'")
            time.sleep(1)
            continue

        if img.ndim == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        res = cv2.matchTemplate(gray, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)

        if max_val >= thresh:
            print('✅ Homepage detected. Enjoy clashing!')
            return True

        print(f'[WARN] Settings icon not found (score={max_val:.2f}); sending HOME')
        subprocess.run(
            [ADB_BIN, '-s', host, 'shell', 'input', 'keyevent', 'KEYCODE_HOME'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        time.sleep(1)

    print('❌ Timed out waiting for settings icon.')
    return False


def ensure_memu():
    memu_exe, memuc_exe, _ = find_memu_tools()
    if not (memu_exe and memuc_exe):
        print('❌ Could not find a MEmu installation.')
        print('   → Please install MEmu and retry.')
        raise RuntimeError('Could not find MEmu installation')

    print(f'✅ Found MEmu.exe at: {memu_exe}')
    print(f'✅ Found memuc.exe at: {memuc_exe}')

    vm_idx = get_instance_index(memuc_exe)

    cur = run([memuc_exe, 'getconfigex', '-i', vm_idx, 'custom_resolution'])
    parts = cur.strip().split()
    if len(parts) >= 3:
        w_cur, h_cur, dpi_cur = parts[-3:]
    else:
        w_cur = h_cur = dpi_cur = None

    res_ok = (w_cur, h_cur, dpi_cur) == (WIDTH, HEIGHT, DPI)
    if res_ok:
        print(f'✅ MEmu already at {WIDTH}×{HEIGHT}@{DPI}dpi; skipping re-config.')
    else:
        print(f'▶ Resolution mismatch ({w_cur}×{h_cur}@{dpi_cur}); will apply fix.')

    out = run([memuc_exe, 'getconfigex', '-i', vm_idx, 'graphics_render_mode'])
    mode = None
    for token in out.strip().split():
        if token in ('0', '1', '2'):
            mode = int(token)
            break

    rend_ok = (mode == 1)
    if rend_ok:
        print('✅ Render mode is already DirectX; skipping re-config.')
    else:
        print(f'▶ Render mode is {mode}; will switch to DirectX.')

    if not res_ok or not rend_ok:
        if not res_ok:
            apply_resolution(memuc_exe, vm_idx)

        if not rend_ok:
            subprocess.run(
                [memuc_exe, 'setconfigex', '-i', str(vm_idx), 'graphics_render_mode', '1'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW,
            )
            print('   • graphics_render_mode set to DirectX')

        print('↻ Applying settings → restarting MEmu…')
        stop_memu()

        ret = subprocess.run(
            [memuc_exe, 'start', '-i', str(vm_idx)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        ).returncode

        if ret != 0:
            print('❌ memuc failed to start emulator')
            raise RuntimeError('memuc failed to start emulator')

        if not start_and_connect(memu_exe):
            raise RuntimeError('Failed to connect to emulator')
        time.sleep(12)
    else:
        if not start_and_connect(memu_exe):
            raise RuntimeError('Failed to connect to emulator')

    if not wait_for_settings_icon():
        print('❌ Failed to verify home page.')
        boot_recovery()


if __name__ == '__main__':
    ensure_memu()
