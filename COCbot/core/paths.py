# ==== COCbot/core/paths.py ====
"""
Central path resolution and sys.path configuration.
Ensures both SRC_DIR and COCBOT_DIR (and subpackages) are in sys.path
and resolves paths to Templates, profiles, walls, settings.json, adb, etc.
"""
import os
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    SRC_DIR = os.path.dirname(sys.executable)
    COCBOT_DIR = os.path.join(SRC_DIR, 'COCbot') if os.path.isdir(os.path.join(SRC_DIR, 'COCbot')) else SRC_DIR
else:
    _curr = os.path.abspath(os.path.dirname(__file__))
    _p = _curr
    _found_src = None
    for _ in range(5):
        if (os.path.isdir(os.path.join(_p, 'Templates')) or
                os.path.isfile(os.path.join(_p, 'settings.json')) or
                os.path.isdir(os.path.join(_p, 'COCbot'))):
            _found_src = _p
            break
        _parent = os.path.dirname(_p)
        if _parent == _p:
            break
        _p = _parent

    SRC_DIR = _found_src if _found_src else os.path.abspath(os.path.join(_curr, '..', '..'))
    _candidate_cocbot = os.path.join(SRC_DIR, 'COCbot')
    if os.path.isdir(_candidate_cocbot):
        COCBOT_DIR = _candidate_cocbot
    else:
        COCBOT_DIR = os.path.abspath(os.path.join(_curr, '..'))

# Insert SRC_DIR and COCBOT_DIR into sys.path
for d in [SRC_DIR, COCBOT_DIR]:
    if d not in sys.path:
        sys.path.insert(0, d)

# Auto-add subpackages to sys.path
for subdir in ['core', 'gui', 'routines', 'emulator', 'utils', 'vision', 'attacks', 'actions']:
    p = os.path.abspath(os.path.join(COCBOT_DIR, subdir))
    if os.path.isdir(p) and p not in sys.path:
        sys.path.append(p)

BASE_DIR = SRC_DIR
ROOT = SRC_DIR

TEMPLATE_DIR = os.path.join(SRC_DIR, 'Templates')
PROFILES_DIR = os.path.join(SRC_DIR, 'profiles')
WALLS_DIR = os.path.join(SRC_DIR, 'walls')
SETTINGS_JSON = os.path.join(SRC_DIR, 'settings.json')
ARMY_PRESETS_JSON = os.path.join(SRC_DIR, 'army_presets.json')

# ADB path: check COCbot/adb first, then src/adb
ADB_DIR = os.path.join(COCBOT_DIR, 'adb')
if not os.path.isdir(ADB_DIR):
    ADB_DIR = os.path.join(SRC_DIR, 'adb')
ADB_BIN = os.path.join(ADB_DIR, 'adb.exe')

# Attacks dir: check COCbot/attacks first, then src/attacks
ATTACKS_DIR = os.path.join(COCBOT_DIR, 'attacks')
if not os.path.isdir(ATTACKS_DIR):
    ATTACKS_DIR = os.path.join(SRC_DIR, 'attacks')

# AutoHotkey
AHK_DIR = os.path.join(SRC_DIR, 'AutoHotkey', 'v2')
if not os.path.isdir(AHK_DIR):
    AHK_DIR = os.path.join(COCBOT_DIR, 'AutoHotkey', 'v2')
AHK_EXE = os.path.join(AHK_DIR, 'AutoHotkey64.exe')

TEMPLATE_PATH = Path(TEMPLATE_DIR)
PROFILES_PATH = Path(PROFILES_DIR)
WALLS_PATH = Path(WALLS_DIR)
ATTACKS_PATH = Path(ATTACKS_DIR)
